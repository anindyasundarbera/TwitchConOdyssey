"""Static/in-process checks for authoritative runtime and HUD state binding."""
import tempfile
import unittest
from pathlib import Path

from server.app import Runtime
from server.engine import AuthoritativeGame

ROOT = Path(__file__).resolve().parents[1]


class RuntimeIntegrationTests(unittest.TestCase):
    def test_runtime_constructs_authoritative_engine_and_fixed_fixture_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(db=str(Path(tmp) / "runtime.sqlite"))
            try:
                self.assertIsInstance(runtime.engine, AuthoritativeGame)
                envelope = runtime.public_state()
                self.assertEqual(envelope["state"], runtime.engine.snapshot())
                self.assertEqual(envelope["evidence"]["origin"], "fixture")
                self.assertFalse(envelope["evidence"]["live_participation"])
                envelope["evidence"]["origin"] = "live"
                self.assertEqual(runtime.public_state()["evidence"]["origin"], "fixture")
            finally:
                runtime.close()

    def test_client_emits_canonical_state_with_server_evidence(self):
        app = (ROOT / "client/app.js").read_text()
        index = (ROOT / "client/index.html").read_text()
        self.assertIn("odyssey:state", app)
        self.assertIn("state: envelope.state, evidence: envelope.evidence", app)
        self.assertIn("deriveView(event.detail.state, event.detail.evidence)", index)
        self.assertNotIn("event.detail.mode", index)

    def test_client_does_not_render_fabricated_gameplay_metrics_or_actions(self):
        app = (ROOT / "client/app.js").read_text()
        index = (ROOT / "client/index.html").read_text()
        self.assertNotIn("integrity:100", app)
        self.assertNotIn("winner:'shield'", app)
        self.assertNotIn("/api/chat", app)
        for mock_label in ("BUILD INTEGRITY", "Rival squads", "DETERMINISTIC MOCK",
                           "STRUCTURED TOOL PROPOSAL"):
            self.assertNotIn(mock_label, index)

    def test_client_controls_submit_canonical_fixture_commands(self):
        app = (ROOT / "client/app.js").read_text()
        index = (ROOT / "client/index.html").read_text()
        runtime = (ROOT / "server/app.py").read_text()
        self.assertIn('data-control="left"', index)
        self.assertIn('data-control="right"', index)
        self.assertIn('fetch("/api/command"', app)
        self.assertIn('id="pause"', index)
        self.assertIn('id="restart"', index)
        self.assertIn('id="feedback" role="status" aria-live="polite"', index)
        self.assertIn('fetch(path, {', app)
        self.assertIn("make_command('streamer.steer'", runtime)
        self.assertIn("'offline_fixture_controller', 'fixture'", runtime)

    def test_async_provider_results_expire_instead_of_rolling_forward(self):
        runtime = (ROOT / "server/app.py").read_text()
        self.assertIn("data['round'] != self.engine.turn", runtime)
        self.assertIn("self.engine.phase != 'planning'", runtime)
        self.assertIn("self.engine.tick - submitted_tick >= 40", runtime)
        self.assertIn("match_id != self.match_id", runtime)
        self.assertIn("generation != self.work_generation", runtime)
        self.assertIn("self.engine.is_paused", runtime)
        self.assertIn("self.store.append(record_match_id", runtime)


if __name__ == "__main__":
    unittest.main()
