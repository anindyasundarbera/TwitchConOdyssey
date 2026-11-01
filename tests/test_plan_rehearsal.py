import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from coordination.plan_rehearsal import aggregate, prepare


class PlanRehearsalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.plan = Path(self.tmp.name) / "plan.json"
        self.plan.write_text(json.dumps({"setting": "San Diego", "route": ["A", "B"]}))
        self.manifest = prepare(self.plan, roles=["streamer", "review"])
        self.results = [{"role": p["role"], "plan_hash": self.manifest["plan_hash"],
                         "model": p["decision"]["model"], "findings": [], "runtime_executed": False}
                        for p in self.manifest["packets"]]

    def test_honest_provenance_and_complete_review(self):
        report = aggregate(self.manifest, self.results, plan_path=self.plan)
        self.assertFalse(report["runtime_executed"])
        self.assertEqual(report["scripted_checks"]["evidence_origin"], "scripted_validation")
        self.assertEqual(report["agent_reviews"]["evidence_origin"], "submitted_agent_review_json")
        self.assertEqual(len(report["agent_reviews"]["canonical_result_hashes"]["streamer"]), 64)
        self.assertEqual(report["agent_reviews"]["expected_providers"]["streamer"], "codex_subagent")

    def test_gameplay_fails_before_io(self):
        with patch.object(Path, "open", side_effect=AssertionError("I/O")):
            with self.assertRaises(ValueError):
                prepare(self.plan, mode="gameplay")
            with self.assertRaises(ValueError):
                aggregate({}, [], plan_path=self.plan, mode="gameplay")

    def test_stale_plan_context_and_model(self):
        context = Path(self.tmp.name) / "context.md"
        context.write_text("current")
        manifest = prepare(self.plan, [context], roles=["streamer", "review"])
        context.write_text("changed")
        with self.assertRaisesRegex(ValueError, "context"):
            aggregate(manifest, self.results, plan_path=self.plan)
        self.results[0]["model"] = "wrong"
        with self.assertRaisesRegex(ValueError, "mismatch"):
            aggregate(self.manifest, self.results, plan_path=self.plan)
        self.plan.write_text("{}")
        with self.assertRaisesRegex(ValueError, "Stale plan"):
            aggregate(self.manifest, self.results, plan_path=self.plan)

    def test_invalid_incomplete_duplicate_and_oversize_results(self):
        finding = dict(id="f1", severity="high", scenario="deadline", gap="unclear", recommendation="specify")
        mutations = [lambda r: r.pop(), lambda r: r[0].update(extra=True),
                     lambda r: r[0].update(runtime_executed=True),
                     lambda r: r[1].update(role="streamer"),
                     lambda r: r[0].update(findings=[finding, finding]),
                     lambda r: r[0].update(findings=[dict(finding, gap="x" * 2001)]),
                     lambda r: r[0].update(findings=[finding] * 31)]
        for mutate in mutations:
            results = copy.deepcopy(self.results)
            mutate(results)
            with self.assertRaises(ValueError):
                aggregate(self.manifest, results, plan_path=self.plan)

    def test_packet_budget(self):
        self.plan.write_text(json.dumps({"route": "x" * 24000}))
        with self.assertRaisesRegex(ValueError, "budget"):
            prepare(self.plan)
