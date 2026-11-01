"""Loopback demo HTTP server with bounded asynchronous inference and fixed-step clock."""
import argparse
import json
import queue
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from server.engine import Engine
from server.providers import MockProvider, OpenAIProvider
from server.replay import load_fixture
from storage.store import Store
from schemas.validate import contract

class Runtime:
    def __init__(self, fixture=None, provider=None, db='.runtime/game.sqlite'):
        self.engine, self.lock = Engine(), threading.RLock()
        self.provider = provider or MockProvider()
        self.fixture = load_fixture(fixture) if fixture else []
        self.match_id = uuid.uuid4().hex
        self.store = Store(db)
        self.jobs, self.results = queue.Queue(64), queue.Queue(64)
        self.stop = threading.Event()
        self.pending = set()
        self.last_input = {}
        self.metrics = {'steps':0, 'max_step_ms':0, 'late_ticks':0}
        self.failure = None
    def submit(self, data):
        contract('request', data)
        with self.lock:
            e = self.engine
            if data['round'] != e.round or e.phase != 'planning' or e.status != 'racing':
                raise ValueError('closed or stale planning window')
            key = data['viewer']
            if key in self.pending or time.monotonic()-self.last_input.get(key,0)<.3:
                raise ValueError('viewer rate limit')
            if len(self.last_input) >= 10000 and key not in self.last_input:
                raise ValueError('capacity reached')
            diff = {'round':e.round,'crisis':e.crisis,'integrity':e.integrity,'progress':round(e.progress,2)}
            self.jobs.put_nowait((data,diff))
            self.pending.add(key)
            self.last_input[key] = time.monotonic()
    def worker(self):
        while not self.stop.is_set():
            try:
                data,diff = self.jobs.get(timeout=.1)
            except queue.Empty:
                continue
            try:
                action = self.provider.parse(data['text'],diff)
                contract('action', action)
                if not action['choices'] or len(set(action['choices'])) != len(action['choices']):
                    raise ValueError('empty or duplicate action')
                outcome = (data,action,None)
            except Exception as exc:
                outcome = (data,None,type(exc).__name__+': '+str(exc)[:160])
            self.results.put(outcome)
    def apply_results(self):
        for _ in range(64):
            try:
                data,action,error = self.results.get_nowait()
            except queue.Empty:
                break
            self.pending.discard(data['viewer'])
            self.engine.emit('chat', {'viewer':data['viewer'],'text':data['text'],'provider':self.provider.name})
            if not error:
                self.engine.emit('tool_call', {'name':'submit_game_action','arguments':action,'provider':self.provider.name})
                try:
                    self.engine.submit(data['viewer'],action,data['round'])
                except ValueError as exc:
                    error = str(exc)
            self.engine.emit('validation', {'accepted':error is None,'reason':error or 'schema + phase + cohort budget passed','viewer':data['viewer']})
    def run(self):
        deadline = time.monotonic()
        try:
            while not self.stop.is_set():
                deadline += .05
                start = time.perf_counter()
                with self.lock:
                    e = self.engine
                    for row in self.fixture:
                        if row['tick'] == e.tick and e.status == 'racing':
                            action = MockProvider().parse(row['text'],{})
                            e.emit('chat', {'viewer':row['viewer'],'text':row['text'],'provider':'deterministic mock'})
                            e.emit('tool_call', {'name':'submit_game_action','arguments':action,'provider':'deterministic mock'})
                            e.submit(row['viewer'],action,e.round)
                    self.apply_results()
                    e.step()
                    events, e.events = e.events, []
                    snapshot = e.snapshot() if events or e.tick%100==0 else None
                elapsed = (time.perf_counter()-start)*1000
                self.metrics['steps'] += 1
                self.metrics['max_step_ms'] = max(self.metrics['max_step_ms'],elapsed)
                self.store.append(self.match_id,events,snapshot)
                delay = deadline-time.monotonic()
                if delay < 0:
                    self.metrics['late_ticks'] += 1
                # Bounded catch-up; never accumulate an unbounded spiral after a stall.
                if delay < -.25:
                    deadline = time.monotonic()
                self.stop.wait(max(0,delay))
        except Exception as exc:
            self.failure = repr(exc)
            self.stop.set()
    def start(self):
        self.threads = [threading.Thread(target=f,daemon=True) for f in (self.worker,self.run)]
        for t in self.threads: t.start()
    def close(self):
        self.stop.set()
        for t in self.threads: t.join(timeout=4)
        self.store.close()

def handler(runtime):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self, code, body, mime='application/json'):
            raw = json.dumps(body).encode() if mime=='application/json' else body
            self.send_response(code)
            self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(raw)
        def do_GET(self):
            path = urlparse(self.path).path
            if path == '/api/state':
                with runtime.lock: state = runtime.engine.snapshot()
                return self.send(200,state)
            if path == '/api/health':
                return self.send(503 if runtime.failure else 200, {'ok':not runtime.failure,'provider':runtime.provider.name,'fixture':bool(runtime.fixture),'metrics':runtime.metrics,'failure':runtime.failure})
            assets = {'/':('client/index.html','text/html; charset=utf-8'),'/app.js':('client/app.js','text/javascript'),'/style.css':('client/style.css','text/css')}
            if path not in assets: return self.send(404,{'error':'not found'})
            file,mime = assets[path]
            return self.send(200,Path(file).read_bytes(),mime)
        def do_POST(self):
            if self.path != '/api/chat': return self.send(404,{'error':'not found'})
            # Loopback demo: deny cross-origin mutations; production auth belongs in ingress adapter.
            origin = self.headers.get('Origin')
            if origin and origin != 'http://'+self.headers.get('Host',''):
                return self.send(403,{'error':'cross-origin request denied'})
            try:
                size = int(self.headers.get('Content-Length','0'))
                if not 0 < size <= 2048: raise ValueError('body must be 1..2048 bytes')
                data = json.loads(self.rfile.read(size))
                runtime.submit(data)
                return self.send(202,{'queued':True})
            except (ValueError,TypeError,queue.Full) as exc:
                return self.send(400,{'error':str(exc) or 'queue full'})
    return Handler

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--port',type=int,default=8000)
    p.add_argument('--offline-fixture')
    p.add_argument('--provider',choices=['mock','openai'],default='mock')
    p.add_argument('--db',default='.runtime/game.sqlite')
    args = p.parse_args()
    if args.offline_fixture and args.provider != 'mock': p.error('offline fixture forbids live providers')
    runtime = Runtime(args.offline_fixture,OpenAIProvider() if args.provider=='openai' else MockProvider(),args.db)
    http = ThreadingHTTPServer(('127.0.0.1',args.port),handler(runtime))
    runtime.start()
    print(f'Odyssey ready: http://127.0.0.1:{http.server_port} | {runtime.provider.name}',flush=True)
    try: http.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        http.server_close()
        runtime.close()

if __name__ == '__main__': main()
