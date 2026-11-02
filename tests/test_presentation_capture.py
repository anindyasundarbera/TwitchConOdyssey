"""Worker B presentation/capture tests.

Static checks and an offline Playwright render (fixture-only, no service and no
network). The synthetic live record helpers below exercise structural
predicates only; they are explicitly *not* observed Twitch evidence and no test
claims a live session or final video exists.
"""
import contextlib
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools import capture_submission as cap

ROOT = Path(__file__).resolve().parents[1]
PNG_DIMS = {name: size for name, size in cap.VIEWPORTS.items()}


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _synthetic_live_record() -> dict:
    """A structural test vector, not observed live evidence."""
    return {
        "schema_version": 1,
        "authority": "authoritative-runtime",
        "origin": "live",
        "live_participation": True,
        "live_verified": True,
        "observed": True,
        "observed_at": "2026-11-02T00:00:00Z",
        "token_validation": {
            "valid": True,
            "user_id_sha256": _hash("synthetic-user"),
            "scopes": ["user:read:chat"],
        },
        "eventsub": {
            "subscribed": True,
            "session_id_sha256": _hash("synthetic-session"),
            "notification_received": True,
        },
        "receipt": {"message_id_sha256": _hash("synthetic-message")},
        "subject": {"linked_subject_sha256": _hash("synthetic-subject")},
        "command": {"kind": "streamer.steer", "status": "applied",
                    "sequence": 7, "tick": 301},
        "engine_result": {"tick": 302, "status": "racing", "result": "lane=0"},
        "visible_consequence": {"summary": "avatar moved left", "tick": 302},
    }


def _adapter_live_record() -> dict:
    """Worker A's sanitized EventSub record shape (structural test vector)."""
    return {
        "schema_version": 1,
        "origin": "live",
        "origin_label": "live Twitch EventSub channel.chat.message",
        "live_participation": True,
        "live_verified": True,
        "fixture": False,
        "recorded_at": 1767225600,
        "token_validation": {
            "validated": True,
            "validated_at": 1767225500,
            "expires_at": 1767229100,
            "client_id_sha256": _hash("client"),
            "user_id_sha256": _hash("user"),
            "scopes": ["user:read:chat"],
        },
        "subscription": {
            "subscription_id_sha256": _hash("subscription"),
            "type": "channel.chat.message",
            "version": "1",
            "status": "enabled",
            "subscribed_at": 1767225510,
        },
        "session": {
            "session_id_sha256": _hash("session"),
            "connected_at": 1767225505,
            "reconnect_count": 0,
            "keepalive_timeout_seconds": 10,
        },
        "receipt_sha256": _hash("receipt"),
        "subject_sha256": _hash("subject"),
        "command": {
            "command_id": _hash("command"),
            "kind": "streamer.steer",
            "actor_sha256": _hash("actor"),
            "provenance": "human",
            "logical_tick": 301,
            "sequence": 9,
            "payload": {"direction": "left"},
        },
        "result": {"status": "applied", "reason": "accepted"},
        "consequence": {
            "summary": "lane changed from 1 to 0",
            "before": {"status": "racing", "turn": 1, "phase": "planning", "lane": 1,
                       "progress": 12.5},
            "after": {"status": "racing", "turn": 1, "phase": "planning", "lane": 0,
                      "progress": 12.6},
        },
    }


def _write_artifact(path: Path, payload: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(payload).hexdigest()}


def _synthetic_composed_manifest(base: Path) -> dict:
    """Structural manifest for predicate tests; no observed media is implied."""
    record = _synthetic_live_record()
    desktop = _write_artifact(base / "desktop.png", b"synthetic-desktop")
    mobile = _write_artifact(base / "mobile.png", b"synthetic-mobile")
    desktop.update({"width": 1440, "height": 1100})
    mobile.update({"width": 390, "height": 844})
    segments = []
    for index, role in enumerate(cap.REQUIRED_VIDEO_SEGMENTS):
        item = _write_artifact(base / f"segment-{index}.bin", f"segment-{role}".encode())
        item.update({"role": role, "duration_seconds": 20.0})
        segments.append(item)
    record["capture"] = {"mode": "live", "live_verified": True,
                         "desktop": desktop, "mobile": mobile}
    record["video_segments"] = segments
    record["duration_seconds"] = 120.0
    return record


def _png_dimensions(path: Path) -> tuple:
    payload = path.read_bytes()
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("not a PNG")
    return int.from_bytes(payload[16:20], "big"), int.from_bytes(payload[20:24], "big")


def _playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except Exception:
        return False


class CapturePlanTests(unittest.TestCase):
    def test_fixture_plan_is_ordered_deterministic_and_truthfully_labelled(self):
        first = cap.build_capture_plan("fixture")
        second = cap.build_capture_plan("fixture")
        self.assertEqual(first, second)
        self.assertEqual(first["mode"], "fixture")
        self.assertFalse(first["live_verified"])
        self.assertIn("not live Twitch activity", first["label"])
        self.assertEqual([step["order"] for step in first["steps"]], [1, 2, 3, 4, 5])
        self.assertEqual(first["viewports"]["desktop"], {"width": 1440, "height": 1100})
        self.assertEqual(first["viewports"]["mobile"], {"width": 390, "height": 844})
        self.assertNotIn("generated_at", json.dumps(first))
        self.assertNotIn("timestamp", json.dumps(first))

    def test_disconnected_plan_is_ordered_and_makes_no_live_claim(self):
        plan = cap.build_capture_plan("disconnected")
        self.assertEqual([step["order"] for step in plan["steps"]], [1, 2, 3, 4, 5])
        self.assertFalse(plan["live_verified"])
        self.assertIn("no authoritative state", plan["label"].lower())
        with self.assertRaises(cap.EvidenceError):
            cap.build_capture_plan("query-parameter-live")

    def test_offline_fixture_document_has_no_network_resource(self):
        document = cap._fixture_document("fixture")
        self.assertNotIn('<script src="/', document)
        self.assertNotIn('<link rel="stylesheet" href="/', document)
        self.assertIn("window.__FIXTURE_EVIDENCE__", document)
        self.assertIn("window.Hud", document)


class EvidenceGuardTests(unittest.TestCase):
    def test_live_url_guard_accepts_only_explicit_loopback(self):
        self.assertEqual(cap.validate_local_url("http://127.0.0.1:8000"),
                         "http://127.0.0.1:8000")
        self.assertEqual(cap.validate_local_url("http://localhost:9000/demo"),
                         "http://localhost:9000/demo")
        for rejected in ("https://twitch.tv", "https://127.0.0.1.evil.example",
                         "ftp://127.0.0.1", "http://user:pass@127.0.0.1:8000",
                         "http://192.168.1.10:8000", ""):
            with self.assertRaises(cap.EvidenceError, msg=rejected):
                cap.validate_local_url(rejected)

    def test_live_record_rejects_fixture_incomplete_and_secret_values(self):
        record = _synthetic_live_record()
        normalized = cap.validate_observed_live_evidence(record)
        self.assertTrue(normalized["live_verified"])
        self.assertEqual(normalized["origin"], "live")

        with self.assertRaisesRegex(cap.EvidenceError, "JSON object"):
            cap.validate_observed_live_evidence(None)
        with self.assertRaisesRegex(cap.EvidenceError, "origin must be live"):
            cap.validate_observed_live_evidence({**record, "origin": "fixture"})
        with self.assertRaisesRegex(cap.EvidenceError, "live_verified"):
            cap.validate_observed_live_evidence({**record, "live_verified": False})
        with self.assertRaisesRegex(cap.EvidenceError, "notification"):
            cap.validate_observed_live_evidence(
                {**record, "eventsub": {**record["eventsub"], "notification_received": False}})
        with self.assertRaisesRegex(cap.EvidenceError, "forbidden sensitive"):
            cap.validate_observed_live_evidence(
                {**record, "token_validation": {**record["token_validation"],
                                                "access_token": "not-a-real-token"}})
        with self.assertRaisesRegex(cap.EvidenceError, "user:read:chat"):
            cap.validate_observed_live_evidence(
                {**record, "token_validation": {**record["token_validation"], "scopes": []}})

    def test_worker_a_adapter_record_shape_is_accepted_and_sanitized(self):
        normalized = cap.validate_observed_live_evidence(_adapter_live_record())
        self.assertTrue(normalized["live_verified"])
        self.assertEqual(normalized["receipt"]["message_id_sha256"], _hash("receipt"))
        self.assertEqual(normalized["subject"]["linked_subject_sha256"], _hash("subject"))
        self.assertEqual(normalized["command"]["kind"], "streamer.steer")
        self.assertEqual(normalized["command"]["status"], "applied")
        self.assertEqual(normalized["engine_result"]["lane"], 0)
        self.assertIn("lane changed", normalized["visible_consequence"]["summary"])
        with self.assertRaisesRegex(cap.EvidenceError, "fixture record"):
            cap.validate_observed_live_evidence(
                {**_adapter_live_record(), "fixture": True})

    def test_video_boundary_refuses_fixtures_and_missing_evidence(self):
        decision = cap.evaluate_video_evidence(None)
        self.assertFalse(decision["eligible"])
        self.assertTrue(any("observed live evidence" in item for item in decision["failures"]))

        fixture = cap.evaluate_video_evidence({
            "authority": "authoritative-runtime", "origin": "fixture",
            "live_participation": False, "live_verified": False,
            "capture": {"mode": "fixture", "live_verified": False},
        })
        self.assertFalse(fixture["eligible"])
        self.assertTrue(any("origin must be live" in item for item in fixture["failures"]))
        self.assertTrue(any("capture mode must be live" in item for item in fixture["failures"]))

        live_without_capture = cap.evaluate_video_evidence(_synthetic_live_record())
        self.assertFalse(live_without_capture["eligible"])
        self.assertTrue(any("capture manifest is required" in item
                            for item in live_without_capture["failures"]))

    def test_video_boundary_accepts_only_structurally_complete_evidence(self):
        # This is a synthetic structure test vector, not an observed live record.
        base = Path(tempfile.mkdtemp(prefix=".tmp-worker-b-", dir=ROOT))
        try:
            manifest = _synthetic_composed_manifest(base)
            decision = cap.evaluate_video_evidence(manifest)
            self.assertTrue(decision["eligible"], decision["failures"])
            self.assertTrue(decision["live_verified"])

            manifest["video_segments"][-1]["duration_seconds"] = 120.0
            too_long = cap.evaluate_video_evidence(manifest)
            self.assertFalse(too_long["eligible"])
            self.assertTrue(any("under 180 seconds" in item for item in too_long["failures"]))
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_video_boundary_detects_tampered_capture_bytes(self):
        base = Path(tempfile.mkdtemp(prefix=".tmp-worker-b-", dir=ROOT))
        try:
            manifest = _synthetic_composed_manifest(base)
            (ROOT / manifest["capture"]["desktop"]["path"]).write_bytes(b"tampered")
            decision = cap.evaluate_video_evidence(manifest)
            self.assertFalse(decision["eligible"])
            self.assertTrue(any("hash does not match" in item for item in decision["failures"]))
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_cli_refuses_live_capture_without_evidence_and_missing_video_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "live"
            with contextlib.redirect_stderr(io.StringIO()):
                code = cap.main(["capture", "--mode", "live", "--url",
                                 "https://twitch.tv", "--out", str(output)])
            self.assertEqual(code, 3)
            self.assertFalse(output.exists())

            with contextlib.redirect_stderr(io.StringIO()):
                code = cap.main(["capture", "--mode", "live", "--url",
                                 "http://127.0.0.1:8000", "--out", str(output)])
            self.assertEqual(code, 3)
            self.assertFalse(output.exists())

            with contextlib.redirect_stderr(io.StringIO()):
                code = cap.main(["capture", "--mode", "fixture",
                                 "--url", "http://127.0.0.1:8000", "--out", str(output)])
            self.assertEqual(code, 3)
            self.assertFalse(output.exists())

            with contextlib.redirect_stderr(io.StringIO()):
                code = cap.main(["assemble", "--evidence", str(Path(tmp) / "missing.json")])
            self.assertEqual(code, 3)


class StaticClientTests(unittest.TestCase):
    def test_three_modes_and_no_query_or_storage_live_inference(self):
        hud = (ROOT / "client/hud.js").read_text(encoding="utf-8")
        app = (ROOT / "client/app.js").read_text(encoding="utf-8")
        index = (ROOT / "client/index.html").read_text(encoding="utf-8")
        self.assertIn("disconnectedView", hud)
        self.assertIn("live_verified", hud)
        self.assertIn("MODE_BADGES", hud)
        self.assertIn("odyssey:disconnected", app)
        self.assertIn("odyssey:state", app)
        for token in ("URLSearchParams", "location.search", "localStorage",
                      "sessionStorage", "event.detail.mode"):
            self.assertNotIn(token, app)
            self.assertNotIn(token, index)
        self.assertIn('data-hud="badge"', index)
        self.assertIn('data-hud="connection"', index)
        self.assertIn('aria-live="polite"', index)
        self.assertIn('name="viewport" content="width=device-width,initial-scale=1"', index)

    def test_mobile_focus_and_contrast_rules_are_present(self):
        css = (ROOT / "client/style.css").read_text(encoding="utf-8")
        self.assertIn(":focus-visible", css)
        self.assertIn("@media(max-width:600px)", css)
        self.assertIn("@media(max-width:430px)", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn(".hud-mode[data-mode=live]", css)
        self.assertIn(".hud-mode[data-mode=disconnected]", css)


@unittest.skipUnless(_playwright_available(), "Playwright is not installed")
class OfflineRenderTests(unittest.TestCase):
    def test_fixture_and_disconnected_renders_are_labelled_and_hashed(self):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                fixture = cap.capture("fixture", root / "fixture")
                self.assertFalse(fixture["live_verified"])
                fixture_manifest = json.loads(
                    (root / "fixture/CAPTURE-MANIFEST.json").read_text(encoding="utf-8"))
                self.assertEqual(fixture_manifest["mode"], "fixture")
                self.assertFalse(fixture_manifest["live_verified"])
                self.assertIn("not live Twitch activity", fixture_manifest["label"])
                for target in ("desktop", "mobile"):
                    name = f"fixture-{target}.png"
                    path = root / "fixture" / name
                    self.assertEqual(_png_dimensions(path), PNG_DIMS[target])
                    self.assertEqual(cap.sha256_file(path),
                                     fixture_manifest["artifacts"][name]["sha256"])
                fixture_timeline = json.loads(
                    (root / "fixture/timeline.json").read_text(encoding="utf-8"))
                self.assertEqual([capture["target"] for capture in fixture_timeline["captures"]],
                                 ["desktop", "mobile"])
                self.assertTrue(all(capture["overflow"] is False
                                    for capture in fixture_timeline["captures"]))
                self.assertEqual(fixture_timeline["blocked_requests"], [])
                self.assertTrue(all(item["passed"] for item in
                                    json.loads((root / "fixture/accessibility.json")
                                               .read_text(encoding="utf-8")).values()))
                self.assertTrue(cap.verify_capture(root / "fixture")["ok"])

                disconnected = cap.capture("disconnected", root / "disconnected")
                self.assertFalse(disconnected["live_verified"])
                disconnected_manifest = json.loads(
                    (root / "disconnected/CAPTURE-MANIFEST.json").read_text(encoding="utf-8"))
                self.assertIn("no authoritative state", disconnected_manifest["label"].lower())
                disconnected_accessibility = json.loads(
                    (root / "disconnected/accessibility.json").read_text(encoding="utf-8"))
                for report in disconnected_accessibility.values():
                    checks = {item["id"]: item["pass"] for item in report["checks"]}
                    self.assertTrue(checks["controls-disabled"])
                    self.assertTrue(checks["badge-disconnected"])
                    self.assertTrue(checks["no-horizontal-overflow"])
                self.assertTrue(cap.verify_capture(root / "disconnected")["ok"])

                target = root / "fixture/fixture-mobile.png"
                target.write_bytes(target.read_bytes() + b"tamper")
                self.assertFalse(cap.verify_capture(root / "fixture")["ok"])
        except cap.CaptureUnavailable as exc:
            self.skipTest(str(exc))


if __name__ == "__main__":
    unittest.main()
