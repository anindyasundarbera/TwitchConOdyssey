"""W6/TASK-009 telemetry matrix: privacy, attribution, origin labels, integrity."""
import hashlib
import json
import unittest

from server.engine import AuthoritativeGame
from server.telemetry import BOOTH_WAYPOINTS, TelemetryRecorder


class TelemetryTests(unittest.TestCase):
    def game(self, **kwargs):
        kwargs.setdefault("initial_roster", ["acct_1"])
        return AuthoritativeGame(seed=42, initial_lane=1, **kwargs)

    def test_observation_never_mutates_gameplay_state(self):
        game = self.game()
        recorder = TelemetryRecorder(game, "match-1", origin="fixture")
        before = game.state_hash()
        before_commands = len(game._simulator.command_history)
        recorder.poll()
        recorder.poll()
        self.assertEqual(game.state_hash(), before)
        self.assertEqual(len(game._simulator.command_history), before_commands)

    def test_match_start_is_emitted_once_and_turn_changes_are_tracked(self):
        game = self.game()
        recorder = TelemetryRecorder(game, "match-2")
        first = recorder.poll()
        self.assertEqual([e["event"] for e in first], ["match_start"])
        self.assertEqual(recorder.poll(), [])
        for _ in range(600):
            game.step()
        events = recorder.poll()
        self.assertIn("turn_start", [e["event"] for e in events])
        self.assertTrue(all(e["match_id"] == "match-2" for e in recorder.events))

    def test_hazard_warning_and_booth_waypoint_linkage(self):
        game = self.game(initial_progress=34.99, base_speed_override=1.25)
        recorder = TelemetryRecorder(game, "match-3", origin="fixture")
        recorder.poll()
        game.step()  # progress crosses 35.0 -> twitch_booth
        booth_events = [e for e in recorder.poll() if e["event"] == "booth_waypoint"]
        self.assertEqual(booth_events[0]["booth"], "twitch_booth")
        self.assertEqual(booth_events[0]["waypoint_percent"], 35.0)
        self.assertFalse(booth_events[0]["live_participation"])

        hazard_game = self.game()
        hazard_recorder = TelemetryRecorder(hazard_game, "match-4")
        hazard_game.submit(__import__("coordination.canonical_commands", fromlist=["make_command"])
                           .make_command("hazard.propose", "acct_1", "human", 0, 0, {"hazard_id": "hz_7"}))
        hazard_recorder.poll()
        for _ in range(300):
            hazard_game.step()
        warning = [e for e in hazard_recorder.poll() if e["event"] == "warning"]
        self.assertEqual(warning[0]["hazard_id"], "hz_7")
        self.assertEqual(warning[0]["tick"], 300)
        self.assertIn("hazard_committed", [e["event"] for e in hazard_recorder.events])

    def test_terminal_outcome_is_attributable_without_chat_or_credentials(self):
        game = self.game(initial_tick=1798, initial_progress=99.9375, base_speed_override=1.25)
        recorder = TelemetryRecorder(game, "match-5")
        recorder.poll()
        game.step()
        outcome = [e for e in recorder.poll() if e["event"] == "outcome"][0]
        self.assertEqual(outcome["status"], "delivered")
        self.assertEqual(outcome["tick"], 1799)
        self.assertEqual(outcome["settlement"]["tick"], 1799)
        self.assertTrue(outcome["settlement"]["settled_once"])
        blob = json.dumps(recorder.events).lower()
        for forbidden in ("chat", "message", "token", "credential", "password"):
            self.assertNotIn(forbidden, blob)
        allowed = {"schema_version", "match_id", "origin", "origin_label",
                   "live_participation", "tick", "turn", "phase", "event",
                   "hazard_id", "status", "settlement", "command_refs",
                   "collisions_total", "booth", "waypoint_percent"}
        for event in recorder.events:
            self.assertTrue(set(event) <= allowed, set(event) - allowed)

    def test_fixture_and_live_labels_are_explicit(self):
        fixture = TelemetryRecorder(self.game(), "match-6", origin="fixture")
        live = TelemetryRecorder(self.game(), "match-7", origin="live")
        fixture.poll()
        live.poll()
        self.assertFalse(fixture.events[0]["live_participation"])
        self.assertIn("not live", fixture.events[0]["origin_label"])
        self.assertTrue(live.events[0]["live_participation"])
        with self.assertRaises(ValueError):
            TelemetryRecorder(self.game(), "match-8", origin="replay")

    def test_evidence_bundle_hashes_match_repo_manifest_convention(self):
        recorder = TelemetryRecorder(self.game(), "match-9", origin="fixture")
        recorder.poll()
        recorder.poll()
        bundle = recorder.evidence_bundle()
        self.assertEqual(set(bundle), {"events.json", "MANIFEST.json"})
        manifest = json.loads(bundle["MANIFEST.json"])["value"]
        self.assertEqual(manifest["artifacts"]["events.json"],
                         hashlib.sha256(bundle["events.json"]).hexdigest())
        self.assertEqual(manifest["match_id"], "match-9")
        self.assertEqual(BOOTH_WAYPOINTS, {35.0: "twitch_booth", 60.0: "codex_booth",
                                           80.0: "aws_booth", 100.0: "fictional_main_stage"})


if __name__ == "__main__":
    unittest.main()
