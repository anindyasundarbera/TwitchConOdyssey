"""Mechanical submission-readiness tests: every predicate and fail-closed behavior."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from coordination.review_route import REQUESTED_ROUTE
from tools.verify_submission_readiness import (
    SEALED_ROOT_ALGORITHM,
    compute_tree_sha256,
    evaluate_record,
    main,
    png_dimensions,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
HEAD = "b" * 40
DIFF = "c" * 64


def _png(width, height):
    return (
        b"\x89PNG\r\n\x1a\n"
        + (13).to_bytes(4, "big")
        + b"IHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x06\x00\x00\x00"
        + b"\x00" * 4
    )


def _package_ok(_repo, _path):
    return {"status": "ok", "complete": True, "verified": 40}


class SubmissionReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, payload):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    def build_record(self):
        description = self.write(
            "docs/submission/PROJECT-DESCRIPTION.md",
            b"# Project description\n" + b"A truthful feature description.\n" * 20,
        )
        licensing = self.write(
            "docs/submission/LICENSING-CHECKLIST.md",
            b"# Licensing checklist\n" + b"Owner action required.\n" * 10,
        )
        setup = self.write(
            "docs/submission/SETUP.md",
            b"# Clean-checkout setup\n" + b"Run the offline fixture.\n" * 10,
        )
        desktop = self.write("evidence/desktop.png", _png(1440, 1100))
        mobile = self.write("evidence/mobile.png", _png(390, 844))
        video = self.write("evidence/demo.mp4", b"fake but hashed video bytes")
        self.write("sealed/root/rejected.txt", b"preserved rejected root\n")
        self.write("sealed/root/current.txt", b"current sealed root\n")
        sealed_root = self.repo / "sealed/root"
        return {
            "schema_version": 1,
            "record_id": "submission-readiness-synthetic",
            "evaluated_at": "2026-11-02T12:00:00Z",
            "declared_submission_ready": True,
            "candidate": {
                "starting_head": "a" * 40,
                "final_head": HEAD,
                "tracked_diff_sha256": DIFF,
            },
            "live": {
                "live_validated": True,
                "token_validation": {
                    "validated": True,
                    "scopes": ["user:read:chat"],
                    "expires_at": "2099-01-01T00:00:00Z",
                    "validated_at": "2026-11-02T11:00:00Z",
                    "client_id_sha256": "1" * 64,
                    "user_id_sha256": "2" * 64,
                    "origin": "observed_live",
                },
                "eventsub": {
                    "connected": True,
                    "subscription_type": "channel.chat.message",
                    "subscription_version": "1",
                    "subscription_id": "subscription-123",
                    "session_id": "session-123",
                    "receipt_id_sha256": "3" * 64,
                    "received_at": "2026-11-02T11:05:00Z",
                },
                "canonical_command": {
                    "command": "clear lane",
                    "result": "applied",
                    "visible_consequence": "the center obstacle disappeared before collision",
                    "consequence_sha256": "4" * 64,
                },
            },
            "captures": {
                "desktop": {
                    "path": "evidence/desktop.png",
                    "sha256": sha256_file(desktop),
                    "width": 1440,
                    "height": 1100,
                    "origin": "live",
                },
                "mobile": {
                    "path": "evidence/mobile.png",
                    "sha256": sha256_file(mobile),
                    "width": 390,
                    "height": 844,
                    "origin": "live",
                },
            },
            "video": {
                "path": "evidence/demo.mp4",
                "sha256": __import__("tools.verify_submission_readiness", fromlist=["sha256_file"]).sha256_file(video),
                "duration_seconds": 179.5,
                "url": "https://www.youtube.com/watch?v=public-demo",
                "visibility": "unlisted",
                "observed_available": True,
                "observed_at": "2026-11-02T11:30:00Z",
                "contains_live_twitch": True,
                "contains_codex_evidence": True,
            },
            "repository": {
                "url": "https://github.com/twitchcon-odyssey/candidate",
                "commit": HEAD,
                "clean_checkout_verified": True,
                "setup_verified": True,
                "observed_accessible": True,
                "observed_at": "2026-11-02T11:45:00Z",
            },
            "project": {
                "description_path": "docs/submission/PROJECT-DESCRIPTION.md",
                "description_sha256": sha256_file(description),
                "setup_path": "docs/submission/SETUP.md",
                "setup_sha256": sha256_file(setup),
                "codex_session_id": "01a1955f-ecad-7053-a225-82baa06d86bd",
                "licensing_checklist_path": "docs/submission/LICENSING-CHECKLIST.md",
                "licensing_checklist_sha256": sha256_file(licensing),
                "audio_licensed": True,
            },
            "package": {
                "manifest_path": "build/submission-package",
            },
            "hygiene": {
                "cleanup_performed": True,
                "secret_scan_passed": True,
                "raw_chat_absent": True,
                "sealed_roots": [
                    {
                        "path": "sealed/root",
                        "file_count": 2,
                        "tree_sha256": compute_tree_sha256(sealed_root),
                        "algorithm": SEALED_ROOT_ALGORITHM,
                    }
                ],
            },
            "review": {
                "requested_route": dict(REQUESTED_ROUTE),
                "configured_route": dict(REQUESTED_ROUTE),
                "spawn": {
                    "accepted": True,
                    "substitution_reported": False,
                    "reported_route": None,
                },
                "serving_attestation_available": False,
                "candidate_match": True,
                "substantive_verdict": "READY",
                "review_packet_sha256": "5" * 64,
                "reviewed_candidate_diff_sha256": DIFF,
            },
            "publication": {
                "repository_push": False,
                "youtube_upload": False,
                "devpost_final_submit": False,
            },
            "agent_execution": {
                "requested_route": {
                    "provider": "codex_subagent",
                    "model": "gpt-6.1-sol",
                    "reasoning_effort": "high",
                },
                "actual_route": {
                    "provider": "ollama-cloud",
                    "model": "deepseek-v4.1-flash",
                },
                "route_deviation": True,
            },
        }

    def evaluate(self, record, git_state=None, package_checker=_package_ok):
        return evaluate_record(
            record,
            repo=self.repo,
            git_state=git_state if git_state is not None else {
                "head": HEAD, "tracked_diff_sha256": DIFF,
            },
            package_checker=package_checker,
            now=NOW,
        )

    def test_complete_synthetic_record_is_ready_and_ignores_declared_boolean(self):
        record = self.build_record()
        result = self.evaluate(record)
        self.assertEqual(result["reasons"], [])
        self.assertTrue(result["submission_ready"])
        self.assertGreaterEqual(result["predicate_count"], 40)
        self.assertTrue(all(result["checks"].values()))

        record["declared_submission_ready"] = False
        self.assertTrue(self.evaluate(record)["submission_ready"])

    def test_each_required_predicate_can_fail_closed(self):
        def set_token(**values):
            def mutate(record):
                record["live"]["token_validation"].update(values)
            return mutate

        def set_eventsub(**values):
            def mutate(record):
                record["live"]["eventsub"].update(values)
            return mutate

        def set_capture(name, **values):
            def mutate(record):
                record["captures"][name].update(values)
            return mutate

        def set_video(**values):
            def mutate(record):
                record["video"].update(values)
            return mutate

        def set_repo(**values):
            def mutate(record):
                record["repository"].update(values)
            return mutate

        def set_project(**values):
            def mutate(record):
                record["project"].update(values)
            return mutate

        def set_hygiene(**values):
            def mutate(record):
                record["hygiene"].update(values)
            return mutate

        def set_review(**values):
            def mutate(record):
                record["review"].update(values)
            return mutate

        cases = [
            ("schema_version", lambda r: r.update(schema_version=2), "schema_version"),
            ("record_id", lambda r: r.update(record_id=""), "record_id"),
            ("evaluated_at", lambda r: r.update(evaluated_at=None), "evaluated_at"),
            ("declared_boolean", lambda r: r.update(declared_submission_ready="yes"),
             "declared_submission_ready"),
            ("starting_head", lambda r: r["candidate"].update(starting_head="x"),
             "candidate.starting_head"),
            ("final_head", lambda r: r["candidate"].update(final_head="d" * 40),
             "candidate.final_head"),
            ("diff", lambda r: r["candidate"].update(tracked_diff_sha256="e" * 64),
             "candidate.tracked_diff_sha256"),
            ("live_validated", lambda r: r["live"].update(live_validated=False),
             "live.live_validated"),
            ("token_validated", set_token(validated=False),
             "live.token_validation.validated"),
            ("token_scopes", set_token(scopes=["user:read:follows"]),
             "live.token_validation.scopes"),
            ("token_origin", set_token(origin="fixture"),
             "live.token_validation.origin"),
            ("token_expired", set_token(expires_at="2000-01-01T00:00:00Z"),
             "live.token_validation.unexpired"),
            ("token_client_hash", set_token(client_id_sha256=None),
             "live.token_validation.client_id_sha256"),
            ("token_user_hash", set_token(user_id_sha256="short"),
             "live.token_validation.user_id_sha256"),
            ("eventsub_connected", set_eventsub(connected=False),
             "live.eventsub.connected"),
            ("eventsub_type", set_eventsub(subscription_type="channel.follow"),
             "live.eventsub.subscription_type"),
            ("eventsub_version", set_eventsub(subscription_version="2"),
             "live.eventsub.subscription_version"),
            ("eventsub_receipt", set_eventsub(receipt_id_sha256="f" * 63),
             "live.eventsub.receipt_id_sha256"),
            ("command_result", lambda r: r["live"]["canonical_command"].update(result="rejected"),
             "live.canonical_command.result"),
            ("consequence", lambda r: r["live"]["canonical_command"].update(
                visible_consequence=""), "live.canonical_command.visible_consequence"),
            ("desktop_width", set_capture("desktop", width=1280),
             "captures.desktop.width"),
            ("desktop_height", set_capture("desktop", height=720),
             "captures.desktop.height"),
            ("desktop_hash", set_capture("desktop", sha256="0" * 64),
             "captures.desktop.sha256_matches"),
            ("desktop_origin", set_capture("desktop", origin="fixture"),
             "captures.desktop.origin"),
            ("mobile_width", set_capture("mobile", width=375),
             "captures.mobile.width"),
            ("mobile_height", set_capture("mobile", height=667),
             "captures.mobile.height"),
            ("mobile_origin", set_capture("mobile", origin=None),
             "captures.mobile.origin"),
            ("video_duration", set_video(duration_seconds=180),
             "video.duration_seconds"),
            ("video_visibility", set_video(visibility="private"),
             "video.visibility"),
            ("video_observed", set_video(observed_available=False),
             "video.observed_available"),
            ("video_url", set_video(url="https://vimeo.com/123"),
             "video.url"),
            ("video_live", set_video(contains_live_twitch=False),
             "video.contains_live_twitch"),
            ("video_codex", set_video(contains_codex_evidence=False),
             "video.contains_codex_evidence"),
            ("repository_url", set_repo(url="<pending>"), "repository.url"),
            ("repository_commit", set_repo(commit="a" * 40),
             "repository.commit_matches_candidate"),
            ("clean_checkout", set_repo(clean_checkout_verified=False),
             "repository.clean_checkout_verified"),
            ("setup", set_repo(setup_verified=False),
             "repository.setup_verified"),
            ("repository_access", set_repo(observed_accessible=False),
             "repository.observed_accessible"),
            ("description_hash", set_project(description_sha256="0" * 64),
             "project.description.sha256_matches"),
            ("setup_hash", set_project(setup_sha256="0" * 64),
             "project.setup.sha256_matches"),
            ("codex_session", set_project(codex_session_id="invented"),
             "project.codex_session_id"),
            ("licensing_hash", set_project(licensing_checklist_sha256="0" * 64),
             "project.licensing_checklist.sha256_matches"),
            ("audio", set_project(audio_licensed=False),
             "project.audio_licensed"),
            ("cleanup", set_hygiene(cleanup_performed=False),
             "hygiene.cleanup_performed"),
            ("secret_scan", set_hygiene(secret_scan_passed=False),
             "hygiene.secret_scan_passed"),
            ("raw_chat", set_hygiene(raw_chat_absent=False),
             "hygiene.raw_chat_absent"),
            ("sealed_count", lambda r: r["hygiene"]["sealed_roots"][0].update(
                file_count=3), "hygiene.sealed_roots[0].file_count_matches"),
            ("sealed_hash", lambda r: r["hygiene"]["sealed_roots"][0].update(
                tree_sha256="0" * 64), "hygiene.sealed_roots[0].tree_sha256_matches"),
            ("review_packet", set_review(review_packet_sha256="0" * 63),
             "review.review_packet_sha256"),
            ("review_stale_diff", set_review(reviewed_candidate_diff_sha256="0" * 64),
             "review.reviewed_candidate_diff_sha256"),
            ("review_verdict", set_review(substantive_verdict="NOT-READY"),
             "substantive_verdict_ready"),
            ("review_substitution", lambda r: r["review"]["spawn"].update(
                substitution_reported=True), "no_substitution_reported"),
        ]
        base = self.build_record()
        for name, mutate, expected in cases:
            with self.subTest(predicate=name):
                record = deepcopy(base)
                mutate(record)
                result = self.evaluate(record)
                self.assertFalse(result["submission_ready"])
                self.assertTrue(
                    any(expected in reason for reason in result["reasons"]),
                    f"{expected!r} not in {result['reasons']!r}",
                )

    def test_package_must_be_complete_and_verified(self):
        base = self.build_record()
        incomplete = self.evaluate(
            base, package_checker=lambda _repo, _path: {
                "status": "ok", "complete": False, "verified": 20,
            })
        self.assertFalse(incomplete["submission_ready"])
        self.assertTrue(any("package.artifact_set_complete" in reason
                            for reason in incomplete["reasons"]))

        failed = self.evaluate(
            base, package_checker=lambda _repo, _path: {
                "status": "failed", "complete": True, "verified": 0,
            })
        self.assertFalse(failed["submission_ready"])
        self.assertTrue(any("package.check" in reason for reason in failed["reasons"]))

    def test_local_git_staleness_and_absence_fail_closed(self):
        base = self.build_record()
        stale = self.evaluate(base, git_state={
            "head": "d" * 40, "tracked_diff_sha256": "e" * 64,
        })
        self.assertFalse(stale["submission_ready"])
        self.assertTrue(any("candidate.final_head_matches_head" in reason
                            for reason in stale["reasons"]))
        self.assertTrue(any("candidate.tracked_diff_matches_worktree" in reason
                            for reason in stale["reasons"]))

        missing = evaluate_record(
            base, repo=self.repo, git_state=None,
            package_checker=_package_ok, now=NOW,
        )
        self.assertFalse(missing["submission_ready"])
        self.assertTrue(any("candidate.git_state_available" in reason
                            for reason in missing["reasons"]))

    def test_publication_booleans_are_not_evidence(self):
        record = self.build_record()
        record["live"]["live_validated"] = False
        record["live"]["token_validation"]["validated"] = False
        record["publication"] = {
            "repository_push": True,
            "youtube_upload": True,
            "devpost_final_submit": True,
        }
        result = self.evaluate(record)
        self.assertFalse(result["submission_ready"])
        self.assertTrue(any("live.live_validated" in reason for reason in result["reasons"]))
        self.assertEqual(result["publication"], record["publication"])

    def test_declared_true_cannot_override_missing_video(self):
        record = self.build_record()
        record["declared_submission_ready"] = True
        record["video"] = None
        result = self.evaluate(record)
        self.assertFalse(result["submission_ready"])
        self.assertTrue(any("video.path" in reason for reason in result["reasons"]))

    def test_raw_chat_or_token_material_in_record_fails_closed(self):
        for name, mutate in (
            ("raw_chat", lambda r: r.update(raw_chat="viewer said something")),
            ("oauth", lambda r: r.update(note="oauth:pretend-token-value")),
            ("token_field", lambda r: r["live"]["token_validation"].update(
                token="pretend-token-value")),
            ("raw_user_id", lambda r: r["live"]["eventsub"].update(
                user_id="123456789")),
        ):
            with self.subTest(material=name):
                record = deepcopy(self.build_record())
                mutate(record)
                result = self.evaluate(record)
                self.assertFalse(result["submission_ready"])
                self.assertTrue(any("record_hygiene" in reason
                                    for reason in result["reasons"]))

    def test_actual_metadata_record_remains_false_with_exact_missing_reasons(self):
        record = json.loads((ROOT / "docs/submission/SUBMISSION-METADATA.json").read_text())
        self.assertIs(record["declared_submission_ready"], False)
        result = evaluate_record(
            record,
            repo=ROOT,
            git_state=None,
            package_checker=lambda _repo, _path: {
                "status": "ok", "complete": False, "verified": 0,
            },
        )
        self.assertFalse(result["submission_ready"])
        for key in (
            "project.description.sha256_matches",
            "project.setup.sha256_matches",
            "project.licensing_checklist.sha256_matches",
            "hygiene.sealed_roots[0].tree_sha256_matches",
            "hygiene.sealed_roots[1].tree_sha256_matches",
        ):
            self.assertTrue(result["checks"].get(key), key)
        for prefix in (
            "live.", "captures.", "video.", "repository.", "project.",
            "package.", "hygiene.", "review.",
        ):
            self.assertTrue(
                any(reason.startswith(prefix) for reason in result["reasons"]),
                f"missing {prefix} reason in {result['reasons']!r}",
            )

    def test_schema_is_valid_json_and_requires_the_predicate_sections(self):
        schema = json.loads((ROOT / "schemas/submission-readiness.json").read_text())
        self.assertEqual(schema["$schema"],
                         "https://json-schema.org/draft/2020-12/schema")
        required = set(schema["required"])
        self.assertTrue({
            "candidate", "live", "captures", "video", "repository", "project",
            "package", "hygiene", "review", "publication",
        }.issubset(required))
        self.assertIn("sealedRoot", schema["$defs"])
        self.assertIn("reviewRoute", schema["$defs"])

    def test_png_dimensions_rejects_non_png(self):
        path = self.write("not-a.png", b"not a png")
        with self.assertRaises(ValueError):
            png_dimensions(path)

    def test_canonical_sealed_root_hash_algorithm_matches_known_tripwire(self):
        rejected = ROOT / "artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043"
        self.assertEqual(
            compute_tree_sha256(rejected),
            "411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d",
        )

    def test_cli_help_is_available_without_side_effects(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            with self.assertRaises(SystemExit) as raised:
                main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("submission-readiness", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
