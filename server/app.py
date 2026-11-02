"""Loopback demo HTTP server over the authoritative S1 engine boundary.

The process is an offline fixture surface until a separately authorized live
identity adapter exists.  Its public state envelope therefore carries a fixed,
server-owned evidence context; request or UI data cannot relabel it as live.
"""
import argparse
import json
import os
import queue
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from coordination.canonical_commands import make_command
from server.engine import AuthoritativeGame
from server.intake import CommandIntake
from server.providers import MockProvider
from server.replay import load_fixture
from server.twitch_live import TwitchEventSubAdapter, TwitchLiveError
from storage.store import Store
from schemas.validate import contract

OFFLINE_EVIDENCE = {
    'origin': 'fixture',
    'origin_label': 'offline fixture / simulation (not live Twitch activity)',
    'live_participation': False,
    'authority': 'authoritative-runtime',
}


class Runtime:
    def __init__(self, fixture=None, db='.runtime/game.sqlite', live_adapter=None):
        self.engine, self.lock = AuthoritativeGame(initial_roster=[]), threading.RLock()
        self.intake = CommandIntake(self.engine)
        self.provider = MockProvider()
        self.fixture = load_fixture(fixture) if fixture else []
        self.match_id = uuid.uuid4().hex
        self.store = Store(db)
        self.jobs, self.results = queue.Queue(64), queue.Queue(64)
        self.stop = threading.Event()
        self.pending = set()
        self.work_generation = 0
        self.last_input = {}
        self.sequence = 0
        self.audit = []
        self.metrics = {'steps':0, 'max_step_ms':0, 'late_ticks':0}
        self.failure = None
        self.live_adapter = live_adapter
        self.live_thread = None
    def submit(self, data):
        contract('request', data)
        with self.lock:
            if self.live_adapter is not None and self.live_adapter.live_active:
                raise ValueError('fixture chat input disabled during live session')
            e = self.engine
            if (data['round'] != e.turn or e.phase != 'planning' or e.status != 'racing'
                    or e.is_paused):
                raise ValueError('closed or stale planning window')
            key = data['viewer']
            pending_key = (self.match_id, key)
            if pending_key in self.pending or time.monotonic()-self.last_input.get(key,0)<.3:
                raise ValueError('viewer rate limit')
            if len(self.last_input) >= 10000 and key not in self.last_input:
                raise ValueError('capacity reached')
            state = e.snapshot()
            diff = {
                'turn': e.turn,
                'phase': e.phase,
                'hazard': state['hazard']['committed'],
                'progress': state['movement']['progress'],
            }
            self.jobs.put_nowait((data,diff,e.tick,self.match_id,self.work_generation))
            self.pending.add(pending_key)
            self.last_input[key] = time.monotonic()

    def submit_control(self, data):
        if (type(data) is not dict or set(data) != {'direction', 'turn'}
                or type(data['direction']) is not str or data['direction'] not in ('left', 'right')
                or type(data['turn']) is not int):
            raise ValueError('control requires a direction and turn')
        with self.lock:
            e = self.engine
            if data['turn'] != e.turn or e.status != 'racing' or e.is_paused:
                return {'status': 'expired', 'reason': 'stale turn or closed match'}
            self.sequence += 1
            command = make_command('streamer.steer', 'offline_fixture_controller', 'fixture',
                                   e.tick, self.sequence, {'direction': data['direction']})
            status = e.submit(command)
            return {'status': status, 'reason': 'engine_' + status}

    def pause(self, data):
        if type(data) is not dict or set(data) != {'paused'} or type(data['paused']) is not bool:
            raise ValueError('pause requires a boolean state')
        with self.lock:
            was_paused = self.engine.is_paused
            status = self.engine.pause(data['paused'])
            if status == 'applied' and was_paused != data['paused']:
                self.work_generation += 1
                self.pending.clear()
            return {'status': status, 'reason': 'engine_' + status}

    def restart(self):
        with self.lock:
            if self.live_adapter is not None:
                return {'status': 'rejected', 'reason': 'live adapter attached'}
            if self.engine.status == 'racing':
                return {'status': 'rejected', 'reason': 'match still active'}
            self.engine = AuthoritativeGame(initial_roster=[])
            self.intake = CommandIntake(self.engine)
            self.match_id = uuid.uuid4().hex
            self.work_generation += 1
            self.sequence = 0
            self.pending.clear()
            self.last_input.clear()
            for work_queue in (self.jobs, self.results):
                while True:
                    try:
                        work_queue.get_nowait()
                    except queue.Empty:
                        break
            return {'status': 'applied', 'reason': 'new offline fixture ready'}

    def attach_live(self, adapter):
        if adapter is None:
            raise ValueError('live adapter required')
        with self.lock:
            if self.live_adapter is not None:
                raise ValueError('live adapter already attached')
            self.live_adapter = adapter

    def start_live(self, token):
        """Start the live adapter; the engine remains the sole game authority."""
        adapter = self.live_adapter
        if adapter is None:
            raise ValueError('live adapter not attached')
        adapter.start(token)
        self.live_thread = threading.Thread(target=adapter.run, daemon=True)
        self.live_thread.start()

    def evidence_envelope(self):
        """Return server-owned evidence; live only while the adapter is active."""
        if self.live_adapter is not None:
            return self.live_adapter.evidence_envelope()
        return dict(OFFLINE_EVIDENCE)

    def public_state(self):
        """Return the canonical snapshot with server-owned evidence provenance."""
        return {'state': self.engine.snapshot(), 'evidence': self.evidence_envelope()}

    def _command_for_choice(self, data, choice):
        """Translate the legacy demo vocabulary into bounded canonical commands."""
        self.sequence += 1
        common = (data['viewer'], 'fixture', self.engine.tick, self.sequence)
        if choice == 'sabotage':
            payload = {'hazard_id': f"fixture-{self.engine.turn}-{data['viewer']}"}
            return make_command('hazard.propose', *common, payload)
        direction = {'shield': 'cancel', 'patch': 'left', 'boost': 'right'}[choice]
        return make_command('streamer.steer', *common, {'direction': direction})

    def _apply_action(self, data, action, error=None):
        statuses = []
        if error is None:
            for choice in action['choices']:
                statuses.append(self.engine.submit(self._command_for_choice(data, choice)))
        accepted = bool(statuses) and any(status == 'applied' for status in statuses)
        row = {
            'tick': self.engine.tick,
            'kind': 'validation',
            'accepted': accepted,
            'reason': error or ','.join(statuses) or 'no canonical command',
        }
        self.audit = (self.audit + [row])[-40:]
        return row
    def worker(self):
        while not self.stop.is_set():
            try:
                data,diff,submitted_tick,match_id,generation = self.jobs.get(timeout=.1)
            except queue.Empty:
                continue
            try:
                action = self.provider.parse(data['text'],diff)
                contract('action', action)
                if not action['choices'] or len(set(action['choices'])) != len(action['choices']):
                    raise ValueError('empty or duplicate action')
                outcome = (data,action,None,submitted_tick,match_id,generation)
            except Exception as exc:
                outcome = (data,None,type(exc).__name__+': '+str(exc)[:160],submitted_tick,match_id,generation)
            self.results.put(outcome)
    def apply_results(self):
        for _ in range(64):
            try:
                data,action,error,submitted_tick,match_id,generation = self.results.get_nowait()
            except queue.Empty:
                break
            # A late result from an invalidated generation must not release a
            # same-viewer request admitted after pause/resume or restart.
            if match_id == self.match_id and generation == self.work_generation:
                self.pending.discard((match_id,data['viewer']))
            if (match_id != self.match_id or generation != self.work_generation
                    or data['round'] != self.engine.turn or self.engine.phase != 'planning'
                    or self.engine.status != 'racing' or self.engine.is_paused
                    or self.engine.tick - submitted_tick >= 40):
                self.audit = (self.audit + [{
                    'tick': self.engine.tick, 'kind': 'validation', 'accepted': False,
                    'reason': 'expired: stale turn, phase, or 2-second deadline',
                }])[-40:]
                continue
            self._apply_action(data, action, error)
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
                            self._apply_action({'viewer': row['viewer'], 'round': e.turn}, action)
                    self.apply_results()
                    e.step()
                    record_match_id = self.match_id
                    events, self.audit = self.audit, []
                    snapshot = e.snapshot() if events or e.tick%100==0 else None
                elapsed = (time.perf_counter()-start)*1000
                self.metrics['steps'] += 1
                self.metrics['max_step_ms'] = max(self.metrics['max_step_ms'],elapsed)
                self.store.append(record_match_id,events,snapshot)
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
        if self.live_adapter is not None:
            self.live_adapter.stop()
        if self.live_thread is not None:
            self.live_thread.join(timeout=4)
        for t in getattr(self, 'threads', []): t.join(timeout=4)
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
                with runtime.lock: state = runtime.public_state()
                return self.send(200,state)
            if path == '/api/health':
                return self.send(503 if runtime.failure else 200, {'ok':not runtime.failure,'provider':runtime.provider.name,'evidence':runtime.evidence_envelope(),'metrics':runtime.metrics,'failure':runtime.failure})
            assets = {'/':('client/index.html','text/html; charset=utf-8'),'/app.js':('client/app.js','text/javascript'),'/hud.js':('client/hud.js','text/javascript'),'/style.css':('client/style.css','text/css')}
            if path not in assets: return self.send(404,{'error':'not found'})
            file,mime = assets[path]
            return self.send(200,Path(file).read_bytes(),mime)
        def do_POST(self):
            if self.path not in ('/api/chat', '/api/command', '/api/pause', '/api/restart'):
                return self.send(404,{'error':'not found'})
            # Loopback demo: deny cross-origin mutations; production auth belongs in ingress adapter.
            origin = self.headers.get('Origin')
            if origin and origin != 'http://'+self.headers.get('Host',''):
                return self.send(403,{'error':'cross-origin request denied'})
            try:
                size = int(self.headers.get('Content-Length','0'))
                if not 0 < size <= 2048: raise ValueError('body must be 1..2048 bytes')
                data = json.loads(self.rfile.read(size))
                if self.path == '/api/command':
                    return self.send(200, runtime.submit_control(data))
                if self.path == '/api/pause':
                    return self.send(200, runtime.pause(data))
                if self.path == '/api/restart':
                    if data != {}: raise ValueError('restart takes an empty object')
                    return self.send(200, runtime.restart())
                runtime.submit(data)
                return self.send(202,{'queued':True})
            except (ValueError,TypeError,queue.Full) as exc:
                return self.send(400,{'error':str(exc) or 'queue full'})
    return Handler

LIVE_ENV_NAMES = (
    'TWITCH_CLIENT_ID',
    'TWITCH_USER_OAUTH_TOKEN',
    'TWITCH_BROADCASTER_USER_ID',
    'TWITCH_CHAT_USER_ID',
)


def _live_adapter_from_env(intake):
    """Build a live adapter from explicitly named environment variables only."""
    missing = [name for name in LIVE_ENV_NAMES if not os.environ.get(name)]
    if missing:
        print('live adapter requires: ' + ', '.join(missing), flush=True)
        return None
    return TwitchEventSubAdapter(
        intake,
        client_id=os.environ['TWITCH_CLIENT_ID'],
        broadcaster_user_id=os.environ['TWITCH_BROADCASTER_USER_ID'],
        user_id=os.environ['TWITCH_CHAT_USER_ID'],
        transport_kind='live',
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--port',type=int,default=8000)
    p.add_argument('--offline-fixture')
    p.add_argument('--db',default='.runtime/game.sqlite')
    p.add_argument('--live-twitch',action='store_true',
                   help='attach the live EventSub adapter from explicit TWITCH_* environment variables')
    args = p.parse_args()
    if args.live_twitch and args.offline_fixture:
        print('live mode cannot use offline fixture replay', flush=True)
        return
    runtime = Runtime(args.offline_fixture, args.db)
    if args.live_twitch:
        try:
            adapter = _live_adapter_from_env(runtime.intake)
        except ValueError:
            print('live adapter unavailable: invalid_configuration', flush=True)
            runtime.close()
            return
        if adapter is None:
            runtime.close()
            return
        runtime.attach_live(adapter)
        token = os.environ.pop('TWITCH_USER_OAUTH_TOKEN')
        try:
            runtime.start_live(token)
        except TwitchLiveError as exc:
            print('live adapter unavailable: ' + exc.code, flush=True)
            runtime.close()
            return
        finally:
            token = None
    http = ThreadingHTTPServer(('127.0.0.1',args.port),handler(runtime))
    runtime.start()
    live = ''
    if runtime.live_adapter is not None and runtime.live_adapter.live_active:
        live = (' | live EventSub verified' if runtime.live_adapter.live_verified
                else ' | live EventSub awaiting first notification')
    print(f'Odyssey ready: http://127.0.0.1:{http.server_port} | {runtime.provider.name}{live}',flush=True)
    try: http.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        http.server_close()
        runtime.close()

if __name__ == '__main__': main()
