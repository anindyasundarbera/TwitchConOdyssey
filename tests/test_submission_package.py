"""W7/TASK-010 evidence packager tests: structure, reproducibility, integrity, honesty."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.package_submission import ROOT, build, build_manifest, check, sha256_file


class SubmissionPackageTests(unittest.TestCase):
    def test_manifest_tracks_five_work_packages_in_sealed_order_and_honest_readiness(self):
        manifest = build_manifest()
        self.assertEqual([wp["id"] for wp in manifest["work_packages"]],
                         manifest["readiness"]["work_package_order"])
        self.assertEqual(len(manifest["work_packages"]), 5)
        self.assertFalse(manifest["readiness"]["submission_ready"])
        self.assertTrue(manifest["readiness"]["simulation_and_plan_ready"])
        self.assertEqual(manifest["readiness"]["open_before_live_submission"],
                         ["live_submission_external_capture"])
        self.assertTrue(manifest["labels"]["fixture_backed"])
        self.assertFalse(manifest["labels"]["live_validated"])

    def test_every_artifact_hash_matches_the_repository_bytes(self):
        manifest = build_manifest()
        self.assertGreaterEqual(len(manifest["artifacts"]), 15)
        for rel, digest in manifest["artifacts"].items():
            self.assertEqual(sha256_file(ROOT / rel), digest, rel)

    def test_build_is_byte_reproducible_and_check_verifies(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            build(Path(first))
            build(Path(second))
            one = (Path(first) / "MANIFEST.json").read_bytes()
            two = (Path(second) / "MANIFEST.json").read_bytes()
            self.assertEqual(one, two)
            self.assertEqual(check(Path(first)), {"verified": len(build_manifest()["artifacts"]),
                                                  "status": "ok"})

    def test_tampered_package_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp))
            target = Path(tmp) / "files" / "server/engine.py"
            target.write_bytes(target.read_bytes() + b"\n# tamper\n")
            with self.assertRaises(ValueError):
                check(Path(tmp))

    def test_manifest_carries_no_credentials_or_chat_content(self):
        blob = json.dumps(build_manifest()).lower()
        for forbidden in ("password", "secret", "token", "credential", "bearer"):
            self.assertNotIn(forbidden, blob)

    def test_runbook_documents_offline_reproduction_and_open_live_gate(self):
        text = (ROOT / "docs/submission/CLOSURE-DEMO-RUNBOOK.md").read_text()
        for phrase in ("Clean checkout", "python3 -m tools.package_submission build",
                       "Failure modes", "Cleanup", "submission_ready: false",
                       "live_submission_external_capture"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
