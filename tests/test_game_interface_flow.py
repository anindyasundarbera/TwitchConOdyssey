"""End-to-end browser gameplay, responsive viewport, and modal flow verification.

Runs against the real local authoritative loopback server without live network calls.
Captures desktop (1440x1100) and mobile (390x844) screenshots and writes verification
evidence to evidence/ui-readiness/20261102T161855Z/.
"""
import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

from server.app import Runtime, handler

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "evidence" / "ui-readiness" / "20261102T161855Z"


class GameInterfaceFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        cls.tmp_dir = tempfile.mkdtemp(prefix="odyssey-test-db-")
        db_path = str(Path(cls.tmp_dir) / "game.sqlite")
        cls.runtime = Runtime(db=db_path)
        cls.runtime.start()

        # Start loopback HTTP server on port 0 (dynamic port)
        cls.http_server = ThreadingHTTPServer(("127.0.0.1", 0), handler(cls.runtime))
        cls.port = cls.http_server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.http_server.serve_forever, daemon=True)
        cls.server_thread.start()

        # Launch Playwright
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        )

    @classmethod
    def tearDownClass(cls):
        try:
            cls.browser.close()
            cls.playwright.stop()
        except Exception:
            pass
        try:
            cls.http_server.shutdown()
            cls.http_server.server_close()
            cls.runtime.close()
            shutil.rmtree(cls.tmp_dir, ignore_errors=True)
        except Exception:
            pass

    def _hash_file(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_01_desktop_fullscreen_flow_and_modals(self):
        page = self.browser.new_page(viewport={"width": 1440, "height": 1100})
        url = f"http://127.0.0.1:{self.port}/"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector("#modal-start", state="visible", timeout=10000)

        # 1. Attract / Start screen is visible on load
        start_modal = page.locator("#modal-start")
        self.assertTrue(start_modal.is_visible())

        # No page scrolling allowed
        measure = page.evaluate("""() => ({
            scrollWidth: document.documentElement.scrollWidth,
            innerWidth: window.innerWidth,
            scrollHeight: document.documentElement.scrollHeight,
            innerHeight: window.innerHeight,
        })""")
        self.assertLessEqual(measure["scrollWidth"], 1441)
        self.assertLessEqual(measure["scrollHeight"], 1101)

        # 2. Click Start Odyssey to launch
        btn_start = page.locator("#btn-start")
        btn_start.click()
        time.sleep(0.3)
        self.assertFalse(start_modal.is_visible())

        # 3. Verify HUD and Canvas exist and are sized properly
        canvas = page.locator("#game")
        self.assertTrue(canvas.is_visible())
        district = page.locator("#district")
        text = district.text_content() or ""
        self.assertTrue(any(d in text for d in ("Little Italy", "Embarcadero Waterfront", "Gaslamp", "Convention Center", "Main Stage")), f"Unexpected district text: {text}")

        # 4. Steer Left via in-game controls
        btn_left = page.locator('[data-control="left"]')
        self.assertTrue(btn_left.is_enabled())
        btn_left.click()
        time.sleep(0.2)
        feedback = page.locator("#feedback").text_content() or ""
        self.assertIn("Control applied", feedback)

        # 5. Open In-Game Help Modal
        btn_help = page.locator("#btn-help")
        btn_help.click()
        time.sleep(0.2)
        help_modal = page.locator("#modal-help")
        self.assertTrue(help_modal.is_visible())

        help_shot = EVIDENCE_DIR / "help-modal-desktop.png"
        page.screenshot(path=str(help_shot))
        self.assertTrue(help_shot.exists())

        # Dismiss Help Modal
        btn_close_help = page.locator("#btn-close-help")
        btn_close_help.click()
        time.sleep(0.2)
        self.assertFalse(help_modal.is_visible())

        # 6. In-Game Pause Modal
        btn_pause = page.locator("#pause")
        btn_pause.click()
        time.sleep(0.3)
        pause_modal = page.locator("#modal-pause")
        self.assertTrue(pause_modal.is_visible())

        pause_shot = EVIDENCE_DIR / "pause-modal-desktop.png"
        page.screenshot(path=str(pause_shot))
        self.assertTrue(pause_shot.exists())

        # Resume via In-Game Modal button
        btn_resume = page.locator("#btn-modal-resume")
        btn_resume.click()
        time.sleep(0.3)
        self.assertFalse(pause_modal.is_visible())

        # 7. Active Gameplay Snapshot
        gameplay_shot = EVIDENCE_DIR / "active-gameplay-desktop.png"
        page.screenshot(path=str(gameplay_shot))
        self.assertTrue(gameplay_shot.exists())

        page.close()

    def test_02_mobile_responsive_flow(self):
        page = self.browser.new_page(viewport={"width": 390, "height": 844})
        url = f"http://127.0.0.1:{self.port}/"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector("#modal-start", state="visible", timeout=10000)

        # Start game windowed
        btn_windowed = page.locator("#btn-start-windowed")
        btn_windowed.click()
        time.sleep(0.3)

        # Measure horizontal overflow on mobile
        measure = page.evaluate("""() => ({
            scrollWidth: document.documentElement.scrollWidth,
            innerWidth: window.innerWidth,
        })""")
        self.assertLessEqual(measure["scrollWidth"], 391)

        # Touch buttons have minimum 44px height for accessibility
        btn_left = page.locator('[data-control="left"]')
        box = btn_left.bounding_box()
        self.assertIsNotNone(box)
        self.assertGreaterEqual(box["height"], 44)

        # Steer Right using touch button
        btn_right = page.locator('[data-control="right"]')
        btn_right.click()
        time.sleep(0.2)
        feedback = page.locator("#feedback").text_content() or ""
        self.assertIn("Control applied", feedback)

        mobile_shot = EVIDENCE_DIR / "active-gameplay-mobile.png"
        page.screenshot(path=str(mobile_shot))
        self.assertTrue(mobile_shot.exists())

        page.close()

    def test_03_generate_manifest_and_evidence_record(self):
        manifest = {
            "evidence_root": str(EVIDENCE_DIR.relative_to(ROOT)),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "artifacts": {},
            "viewports": {
                "desktop": {"width": 1440, "height": 1100},
                "mobile": {"width": 390, "height": 844},
            },
            "status": "locally_game_ready",
        }
        for path in EVIDENCE_DIR.glob("**/*.png"):
            rel = str(path.relative_to(ROOT))
            manifest["artifacts"][path.name] = {
                "path": rel,
                "sha256": self._hash_file(path),
                "size_bytes": path.stat().st_size,
            }
        manifest_path = EVIDENCE_DIR / "UI-VERIFICATION-MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        self.assertTrue(manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
