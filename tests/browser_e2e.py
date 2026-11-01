"""Real startup and browser gate. Requires loopback sockets + installed Chromium.
No fake server state: advance the same runtime engine to accelerate the 97s fixture.
"""
import json
import sys
import tempfile
import threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from http.server import ThreadingHTTPServer
from server.app import Runtime,handler
from server.providers import MockProvider

def main():
    with tempfile.TemporaryDirectory() as d:
        rt=Runtime('fixtures/stage.jsonl',db=d+'/game.db')
        http=ThreadingHTTPServer(('127.0.0.1',0),handler(rt))
        rt.start()
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True)
                page=browser.new_page(viewport={'width':1440,'height':1100})
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{http.server_port}')
                page.get_by_text('Moderation Shield',exact=True).click()
                page.get_by_text('Vote accepted.',exact=False).wait_for()
                page.get_by_role('button',name='♫ Sound off').click()
                assert page.get_by_role('button',name='♫ Sound on').get_attribute('aria-pressed')=='true'
                page.get_by_role('button',name='◷ Bullet time').click()
                assert page.locator('body').evaluate("e=>e.classList.contains('bullet')")
                page.get_by_role('button',name='▶ Resume inspector').click()
                # Advance authoritative ticks and fixture inputs, keeping schema/rule paths intact.
                with rt.lock:
                    while rt.engine.status=='racing':
                        for row in rt.fixture:
                            if row['tick']==rt.engine.tick:rt.engine.submit(row['viewer'],MockProvider().parse(row['text'],{}),rt.engine.round)
                        rt.engine.step()
                page.get_by_text('Main stage unlocked.',exact=True).wait_for()
                assert page.locator('#progress').inner_text()=='100%'
                page.screenshot(path='evals/desktop.png',full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path='evals/mobile.png',full_page=True)
                assert not errors,errors
                browser.close()
            print(json.dumps({'passed':True,'errors':errors,'tick':rt.engine.tick}))
        finally:http.shutdown();http.server_close();rt.close()

if __name__=='__main__':main()
