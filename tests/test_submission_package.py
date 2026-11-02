"""Evidence packager tests: structure, reproducibility, integrity, honesty."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.package_submission import (ARTIFACT_CATALOG, CORE_ARTIFACTS,
                                      EXTENSION_ARTIFACTS, ROOT, WORK_PACKAGES,
                                      build, build_manifest, check, sha256_file)


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
        self.assertEqual(manifest["readiness"]["readiness_record"],
                         "docs/submission/SUBMISSION-METADATA.json")
        self.assertEqual(manifest["labels"]["evidence_scope"], "fixture_offline")
        self.assertTrue(manifest["labels"]["fixture_backed"])
        self.assertFalse(manifest["labels"]["live_validated"])

    def test_core_artifacts_exist_and_hash_to_repository_bytes(self):
        manifest = build_manifest()
        self.assertGreaterEqual(len(CORE_ARTIFACTS), 30)
        for rel in CORE_ARTIFACTS:
            self.assertIn(rel, manifest["artifacts"])
            self.assertEqual(sha256_file(ROOT / rel), manifest["artifacts"][rel], rel)

    def test_extension_artifacts_are_pending_not_silently_dropped(self):
        manifest = build_manifest()
        present = [rel for rel in EXTENSION_ARTIFACTS if (ROOT / rel).is_file()]
        pending = [rel for rel in EXTENSION_ARTIFACTS if rel not in present]
        self.assertEqual(manifest["artifact_set"]["pending"], pending)
        self.assertEqual(manifest["artifact_set"]["complete"], not pending)
        self.assertEqual(set(manifest["artifacts"]),
                         set(CORE_ARTIFACTS) | set(present))
        self.assertEqual(manifest["artifact_set"]["catalog"], ARTIFACT_CATALOG)
        if pending:
            self.assertFalse(manifest["artifact_set"]["complete"])
            self.assertIn("incomplete", manifest["artifact_set"]["pending_reason"])

    def test_every_work_package_evidence_path_is_required_and_hashed(self):
        manifest = build_manifest()
        declared = {path for _, _, _, evidence in WORK_PACKAGES for path in evidence}
        self.assertTrue(declared.issubset(set(CORE_ARTIFACTS)))
        self.assertTrue(declared.issubset(set(manifest["artifacts"])))
        for package in manifest["work_packages"]:
            self.assertTrue(set(package["evidence"]).issubset(set(manifest["artifacts"])))

    def test_build_is_byte_reproducible_and_check_verifies(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            build(Path(first))
            build(Path(second))
            one = (Path(first) / "MANIFEST.json").read_bytes()
            two = (Path(second) / "MANIFEST.json").read_bytes()
            self.assertEqual(one, two)
            manifest = build_manifest()
            result = check(Path(first))
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["verified"], len(manifest["artifacts"]))
            self.assertEqual(result["complete"], manifest["artifact_set"]["complete"])
            self.assertEqual(result["pending"], len(manifest["artifact_set"]["pending"]))

    def test_tampered_package_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp))
            target = Path(tmp) / "files" / "server/engine.py"
            target.write_bytes(target.read_bytes() + b"\n# tamper\n")
            with self.assertRaises(ValueError):
                check(Path(tmp))

    def test_manifest_cannot_omit_required_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp))
            manifest_path = Path(tmp) / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["artifacts"].pop("server/engine.py")
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "artifact set"):
                check(Path(tmp))

    def test_manifest_complete_flag_must_match_pending_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp))
            manifest_path = Path(tmp) / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text())
            if manifest["artifact_set"]["pending"]:
                self.assertFalse(manifest["artifact_set"]["complete"])
                manifest["artifact_set"]["complete"] = True
            else:
                self.assertTrue(manifest["artifact_set"]["complete"])
                manifest["artifact_set"]["complete"] = False
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "complete flag"):
                check(Path(tmp))

    def test_manifest_cannot_claim_live_or_submission_ready(self):
        for field, value, message in (
            (("labels", "live_validated"), True, "live_validated"),
            (("readiness", "submission_ready"), True, "submission_ready"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                build(Path(tmp))
                manifest_path = Path(tmp) / "MANIFEST.json"
                manifest = json.loads(manifest_path.read_text())
                manifest[field[0]][field[1]] = value
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, message):
                    check(Path(tmp))

    def test_manifest_carries_no_credentials_or_chat_content(self):
        blob = json.dumps(build_manifest()).lower()
        for forbidden in ("password", "secret", "token", "credential", "bearer"):
            self.assertNotIn(forbidden, blob)

    def test_package_never_declares_sensitive_or_generated_paths(self):
        manifest = build_manifest()
        for rel in manifest["artifacts"]:
            self.assertFalse(rel == ".env" or rel.startswith(
                (".env", ".runtime/", "build/", "__pycache__/", ".git/")), rel)

    def test_runbook_documents_offline_reproduction_and_open_live_gate(self):
        text = (ROOT / "docs/submission/CLOSURE-DEMO-RUNBOOK.md").read_text()
        for phrase in ("Clean checkout", "python3 -m tools.package_submission build",
                       "python3 -m tools.verify_submission_readiness",
                       "Failure modes", "Cleanup", "submission_ready: false",
                       "live_submission_external_capture", "artifact_set.pending"):
            self.assertIn(phrase, text)
        self.assertNotIn("requirements.txt", text)


if __name__ == "__main__":
    unittest.main()
