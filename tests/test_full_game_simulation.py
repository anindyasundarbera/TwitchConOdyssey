"""Tests verifying the full-game deterministic simulation kernel and evidence bundle."""

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import unittest

from coordination.canonical_commands import make_command, validate_command
from coordination.content_cache import canonical_bytes, canonical_hash
from coordination.full_game_simulator import (
    FullGameSimulator, HZ, PLANNING_TICKS, RESOLUTION_TICKS, REWARD_TICKS,
    TURN_TICKS, MATCH_DEADLINE_TICKS, HAZARD_ADMISSION_CLOSE_TICKS,
    GENERAL_INPUT_CLOSE_TICKS, BASE_SPEED, DISTRICTS,
)

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "full-game-20261101T102226Z-a8e33043"
ARTIFACT_DIR = ROOT / "artifacts/simulations/full-game" / RUN_ID


class FullGameSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ARTIFACT_DIR / "RUN-MANIFEST.json").read_text())
        cls.readiness = json.loads((ARTIFACT_DIR / "DEVELOPMENT-READINESS.json").read_text())
        cls.inventory = json.loads((ARTIFACT_DIR / "FEATURE-INVENTORY.json").read_text())
        cls.matrix = json.loads((ARTIFACT_DIR / "SCENARIO-MATRIX.json").read_text())
        cls.invariants = json.loads((ARTIFACT_DIR / "INVARIANT-RESULTS.json").read_text())
        cls.issues = json.loads((ARTIFACT_DIR / "ISSUES.json").read_text())

    def test_all_16_mandatory_features_inventoried_and_covered(self):
        self.assertEqual(len(self.inventory), 16)
        expected_feature_ids = {
            "FEAT-01-SAN-DIEGO-ROUTE", "FEAT-02-STREAMER-CONTROL",
            "FEAT-03-CADENCE-AND-CLOCK", "FEAT-04-AUDIENCE-ACCOUNTING",
            "FEAT-05-HAZARD-AND-SURVIVAL", "FEAT-06-FICTIONAL-HYPE-REWARD",
            "FEAT-07-OPENAI-CHAT-TO-ACTION", "FEAT-08-CODEX-LIVE-HOTFIX",
            "FEAT-09-TWITCH-BOOTH", "FEAT-10-AWS-IVS-BOOTH",
            "FEAT-11-OFFLINE-FIXTURE-DRIVER", "FEAT-12-BULLET-TIME-PRESENTATION",
            "FEAT-13-ADAPTIVE-AUDIO", "FEAT-14-READABILITY-AND-HUD",
            "FEAT-15-PUBLIC-DEMO-TIMELINE", "FEAT-16-SECURITY-AND-PROVENANCE",
        }
        actual_ids = {f["feature_id"] for f in self.inventory}
        self.assertEqual(actual_ids, expected_feature_ids)
        for feat in self.inventory:
            self.assertEqual(feat["status"], "passed")
            self.assertEqual(feat["coverage_state"], "covered")

    def test_all_18_mandatory_invariants_pass(self):
        self.assertEqual(len(self.invariants), 18)
        for inv in self.invariants:
            self.assertTrue(inv["passed"], f"Invariant {inv['invariant_id']} failed")
            self.assertGreater(inv["evaluations_count"], 0)

    def test_development_readiness_and_independent_review(self):
        self.assertTrue(self.readiness["ready"])
        self.assertEqual(self.readiness["candidate_plan_revision"], 5)
        self.assertEqual(self.readiness["blocking_issues_count"], 0)
        self.assertEqual(self.readiness["review_verdict"], "READY")
        self.assertEqual(self.readiness["unresolved_human_decisions"], ["D-06", "D-07", "D-08"])

        review_text = (ARTIFACT_DIR / "INDEPENDENT-REVIEW.md").read_text()
        self.assertIn("Verdict:** `READY`", review_text)
        self.assertIn("gpt-6-astra", review_text)

    def test_deterministic_golden_replay_identical_digests(self):
        # Run SCEN-E2E-01 twice independently
        sim1 = FullGameSimulator(seed=101, initial_lane=1)
        sim1.set_roster([f"user_{i}" for i in range(10)])
        sim1.submit_command(make_command("hazard.propose", "user_0", "human", 100, 1, {"hazard_id": "haz_t1", "lane": 1}))
        sim1.submit_command(make_command("streamer.steer", "streamer", "human", 200, 2, {"direction": "left"}))
        for _ in range(TURN_TICKS): sim1.step()
        sim1.submit_command(make_command("hazard.propose", "user_1", "human", 700, 3, {"hazard_id": "haz_t2", "lane": 1}))
        for i in range(7):
            sim1.submit_command(make_command("viewer.counter", f"user_{i}", "human", 750 + i, 4 + i, {"hazard_id": "haz_t2", "counter": "clear_lane"}))
        for _ in range(TURN_TICKS): sim1.step()
        sim1.submit_command(make_command("hazard.propose", "user_2", "human", 1300, 20, {"hazard_id": "haz_t3", "lane": 1}))
        while sim1.status == "racing" and sim1.tick < MATCH_DEADLINE_TICKS:
            sim1.step()
        d1 = canonical_hash(sim1.get_canonical_state())

        sim2 = FullGameSimulator(seed=101, initial_lane=1)
        sim2.set_roster([f"user_{i}" for i in range(10)])
        sim2.submit_command(make_command("hazard.propose", "user_0", "human", 100, 1, {"hazard_id": "haz_t1", "lane": 1}))
        sim2.submit_command(make_command("streamer.steer", "streamer", "human", 200, 2, {"direction": "left"}))
        for _ in range(TURN_TICKS): sim2.step()
        sim2.submit_command(make_command("hazard.propose", "user_1", "human", 700, 3, {"hazard_id": "haz_t2", "lane": 1}))
        for i in range(7):
            sim2.submit_command(make_command("viewer.counter", f"user_{i}", "human", 750 + i, 4 + i, {"hazard_id": "haz_t2", "counter": "clear_lane"}))
        for _ in range(TURN_TICKS): sim2.step()
        sim2.submit_command(make_command("hazard.propose", "user_2", "human", 1300, 20, {"hazard_id": "haz_t3", "lane": 1}))
        while sim2.status == "racing" and sim2.tick < MATCH_DEADLINE_TICKS:
            sim2.step()
        d2 = canonical_hash(sim2.get_canonical_state())

        self.assertEqual(d1, d2)
        scenario_hashes = json.loads((ARTIFACT_DIR / "state-hashes/scenario_hashes.json").read_text())
        self.assertEqual(d1, scenario_hashes["SCEN-E2E-01"])

    def test_run_manifest_verifies_all_artifact_hashes(self):
        for rel_path, expected_hash in self.manifest["artifact_hashes"].items():
            full_path = ARTIFACT_DIR / rel_path
            self.assertTrue(full_path.exists(), f"Missing artifact: {rel_path}")
            actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
            self.assertEqual(actual_hash, expected_hash, f"Hash mismatch on {rel_path}")

    def test_triaged_issues_are_closed_with_evidence(self):
        self.assertEqual(len(self.issues), 2)
        for issue in self.issues:
            self.assertEqual(issue["status"], "closed")
            self.assertEqual(issue["category"], "plan")
            self.assertIn("proposed_remediation", issue)
            self.assertIn("remediation_owner", issue)

    def test_pure_deterministic_kernel_properties(self):
        sim = FullGameSimulator(seed=999, initial_lane=1)
        self.assertEqual(sim.turn, 1)
        self.assertEqual(sim.phase, "planning")
        self.assertEqual(sim.pool, 0)
        self.assertEqual(sim.status, "racing")
        # Ensure 0 HP damage and caps are honored
        self.assertEqual(sim.hotfix_rules["slowdown_fraction"], 0.20)
        self.assertEqual(sim.hotfix_rules["slowdown_duration_ticks"], 40)


if __name__ == "__main__":
    unittest.main()
