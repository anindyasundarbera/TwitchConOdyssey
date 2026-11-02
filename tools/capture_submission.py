"""Submission presentation capture and video-assembly boundary (Worker B).

Offline, deterministic rendering of the real client shell at the required
viewports, plus a fail-closed boundary for live captures and the final video.

What this tool may do
---------------------
* Render the client's ``fixture`` and ``disconnected`` modes from local files
  with Playwright ``set_content``. No HTTP service, no gameplay, no network.
* Optionally capture a *live* page only when the caller supplies an explicit
  loopback URL and an observed live-evidence record that passes
  :func:`validate_observed_live_evidence`.
* Emit a deterministic ordered timeline, PNG SHA-256 hashes, a basic
  accessibility checklist, and a capture manifest.
* Evaluate (and optionally assemble with ffmpeg) the final video only from a
  composed observed-evidence manifest. It never uploads anything.

Live record interface assumption
---------------------------------
The live adapter record (Worker A, ``schemas/twitch-live.json``) must carry,
at top level or in the accepted nested aliases below::

    origin == "live"
    fixture is False
    live_participation is True
    live_verified is True        # token validated AND real notification received
    recorded_at                  # or observed_at
    token_validation.validated is True
    token_validation.user_id_sha256 (64 hex chars)
    token_validation.scopes includes "user:read:chat"
    subscription.status == "enabled" (type channel.chat.message)
    session.session_id_sha256 (64 hex chars)
    receipt_sha256 (64 hex chars)
    subject_sha256 (64 hex chars)
    command.kind and result.status == "applied"
    consequence (summary plus before/after state)
    authority == "authoritative-runtime" when present

Legacy aliases (``eventsub.*``, ``receipt.*``, ``subject.*``,
``visible_consequence``, ``engine_result``) are accepted. A record without
``authority`` is accepted only when it explicitly sets ``fixture: false``.
The receipt hash is the notification evidence when the adapter omits a
separate notification flag. The record must not contain tokens, secrets, raw
chat text or raw handles. No fixture, query parameter, local flag or
screenshot can satisfy these predicates. Missing live footage blocks the
final video; this tool never claims otherwise.

Usage
-----
::

    python3 -m tools.capture_submission capture --mode fixture
    python3 -m tools.capture_submission capture --mode disconnected
    python3 -m tools.capture_submission capture --mode live \
        --url http://127.0.0.1:8000 --evidence path/to/observed-live.json
    python3 -m tools.capture_submission verify evidence/submission-capture/fixture
    python3 -m tools.capture_submission assemble --evidence path/to/observed.json
    python3 -m tools.capture_submission assemble --evidence path/to/observed.json \
        --out build/submission-video.mp4
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "client"
DEFAULT_EVIDENCE_ROOT = ROOT / "evidence" / "submission-capture"
VIEWPORTS = {"desktop": (1440, 1100), "mobile": (390, 844)}
MODES = ("fixture", "disconnected", "live")
REQUIRED_VIDEO_SEGMENTS = (
    "twitch_receipt",
    "linked_subject",
    "canonical_command",
    "engine_result",
    "visible_consequence",
    "codex_session",
)
MAX_VIDEO_SECONDS = 180.0
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_KEYS = {
    "access_token", "refresh_token", "client_secret", "authorization",
    "raw_message", "message_text", "chat_text", "user_login", "user_name",
    "handle", "display_name",
}
LABELS = {
    "fixture": "FIXTURE — offline fixture render (not live Twitch activity)",
    "disconnected": "DISCONNECTED — no authoritative state (offline render)",
    "live": "LIVE — observed Twitch evidence record supplied",
}

FIXTURE_STATE: Dict[str, Any] = {
    "schema_version": 1,
    "tick": 300,
    "turn": 1,
    "phase": "planning",
    "status": "racing",
    "is_paused": False,
    "avatar": {"lane": 1, "lateral_pos": 1.0, "transition_remaining_ticks": 0},
    "movement": {
        "progress": 12.5,
        "district": "Little Italy / North Embarcadero",
        "slowdown_ticks_remaining": 0,
        "turn_slowdown_ticks": 0,
        "match_slowdown_ticks": 0,
    },
    "bounty": {
        "pool": 20,
        "synthetic_fixture_pool": 0,
        "collisions_total": 0,
        "collision_halved": False,
    },
    "hazard": {
        "committed": "hz_fixture_1",
        "warning_active": True,
        "obstacle_active": False,
        "hazard_countered": False,
    },
    "audience": {"roster_size": 0, "counter_votes_count": 0, "eligible_voters_count": 0},
    "booths": ["twitch_booth"],
    "audio_state": "music",
}
FIXTURE_EVIDENCE: Dict[str, Any] = {
    "authority": "authoritative-runtime",
    "origin": "fixture",
    "origin_label": "Offline fixture (not live Twitch activity)",
    "live_participation": False,
}


class EvidenceError(ValueError):
    """A supplied record or destination does not meet the evidence boundary."""


class CaptureUnavailable(RuntimeError):
    """Playwright or Chromium is unavailable in this environment."""


# ---------------------------------------------------------------------------
# Hashing and deterministic JSON
# ---------------------------------------------------------------------------
def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def write_json(path: Path, payload: Any) -> bytes:
    data = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    return data


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"missing JSON record: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"invalid JSON record: {path}: {exc}") from exc


def source_bindings() -> Dict[str, str]:
    paths = ("client/app.js", "client/hud.js", "client/index.html", "client/style.css")
    return {rel: sha256_file(ROOT / rel) for rel in paths}


# ---------------------------------------------------------------------------
# Deterministic capture plan and offline page document
# ---------------------------------------------------------------------------
def build_capture_plan(mode: str) -> Dict[str, Any]:
    """Return the ordered, timestamp-free capture plan used by the timeline."""
    if mode not in MODES:
        raise EvidenceError(f"unknown capture mode: {mode}")
    if mode == "fixture":
        expected_mode = "Offline fixture (not live Twitch activity)"
        steps = [
            ("render-fixture-page", "fixture evidence envelope; no live claim"),
            ("assert-mode-label", expected_mode),
            ("capture-desktop", "1440x1100 fixture PNG; controls enabled"),
            ("capture-mobile", "390x844 fixture PNG; no horizontal overflow"),
            ("assert-accessibility", "labelled controls, live regions and contrast pass"),
        ]
    elif mode == "disconnected":
        expected_mode = "Disconnected — no authoritative state"
        steps = [
            ("render-disconnected-page", "fetch unavailable; no live inference"),
            ("assert-mode-label", expected_mode),
            ("capture-desktop", "1440x1100 disconnected PNG; controls disabled"),
            ("capture-mobile", "390x844 disconnected PNG; no horizontal overflow"),
            ("assert-accessibility", "labelled controls, disabled state and contrast pass"),
        ]
    else:
        expected_mode = "Live Twitch participation"
        steps = [
            ("require-observed-live-record", "token, subscription, receipt, subject and command"),
            ("require-explicit-loopback-url", "no non-local destination"),
            ("assert-mode-label", expected_mode),
            ("capture-desktop", "1440x1100 live PNG; no fixture label"),
            ("capture-mobile", "390x844 live PNG; no horizontal overflow"),
            ("assert-accessibility", "labelled controls, live region and contrast pass"),
        ]
    return {
        "schema_version": 1,
        "tool": "tools/capture_submission.py",
        "mode": mode,
        "label": LABELS[mode],
        "live_verified": mode == "live",
        "viewports": {name: {"width": size[0], "height": size[1]}
                      for name, size in VIEWPORTS.items()},
        "source_bindings": source_bindings(),
        "steps": [
            {"order": index, "name": name, "expected": expected}
            for index, (name, expected) in enumerate(steps, start=1)
        ],
    }


def _fixture_document(mode: str) -> str:
    """Inline the real client shell plus a local fixture/disconnected fetch stub."""
    index = (CLIENT / "index.html").read_text(encoding="utf-8")
    css = (CLIENT / "style.css").read_text(encoding="utf-8")
    hud = (CLIENT / "hud.js").read_text(encoding="utf-8")
    app = (CLIENT / "app.js").read_text(encoding="utf-8")

    replacements = [
        ('<link rel="stylesheet" href="/style.css">', "<style>\n" + css + "\n</style>"),
        ('<script src="/hud.js"></script>', "<script>\n" + hud + "\n</script>"),
        ('<script type="module" src="/app.js"></script>',
         _bootstrap_script(mode) + '<script type="module">\n' + app + "\n</script>"),
    ]
    for old, new in replacements:
        if old not in index:
            raise EvidenceError(f"client/index.html is missing expected marker: {old}")
        index = index.replace(old, new)
    for marker in ('<script src="/', '<link rel="stylesheet" href="/'):
        if marker in index:
            raise EvidenceError("offline fixture document still references a network resource")
    return index


def _bootstrap_script(mode: str) -> str:
    state = json.dumps(FIXTURE_STATE, sort_keys=True, ensure_ascii=False)
    evidence = json.dumps(FIXTURE_EVIDENCE, sort_keys=True, ensure_ascii=False)
    if mode == "fixture":
        body = (
            "window.__CAPTURE_MODE__ = 'fixture';\n"
            f"window.__FIXTURE_STATE__ = {state};\n"
            f"window.__FIXTURE_EVIDENCE__ = {evidence};\n"
            "window.fetch = async function (url) {\n"
            "  if (String(url) === '/api/state') {\n"
            "    return {ok: true, status: 200, json: async function () {\n"
            "      return {state: window.__FIXTURE_STATE__, evidence: window.__FIXTURE_EVIDENCE__};\n"
            "    }};\n"
            "  }\n"
            "  return {ok: true, status: 200, json: async function () {\n"
            "    return {status: 'applied', reason: 'offline fixture render (no command submitted)'};\n"
            "  }};\n"
            "};\n"
        )
    elif mode == "disconnected":
        body = (
            "window.__CAPTURE_MODE__ = 'disconnected';\n"
            "window.fetch = async function () {\n"
            "  throw new Error('authoritative state unavailable (offline disconnected render)');\n"
            "};\n"
        )
    else:
        raise EvidenceError("live mode must use an explicitly supplied loopback URL")
    return "<script>\n" + body + "</script>\n"


# ---------------------------------------------------------------------------
# URL and live-evidence guards
# ---------------------------------------------------------------------------
def validate_local_url(url: str) -> str:
    """Accept only an explicit loopback HTTP(S) URL; reject everything else."""
    if not isinstance(url, str) or not url.strip():
        raise EvidenceError("an explicit local --url is required for live capture")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise EvidenceError("live capture URL must use http or https")
    if parsed.username or parsed.password:
        raise EvidenceError("live capture URL must not contain credentials")
    if parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise EvidenceError("live capture URL must be an explicit loopback address")
    if parsed.fragment:
        raise EvidenceError("live capture URL must not contain a fragment")
    return url


def _same_origin(candidate: str, allowed: str) -> bool:
    left, right = urlparse(candidate), urlparse(allowed)
    return (left.scheme, left.hostname, left.port) == (right.scheme, right.hostname, right.port)


def _scan_forbidden_keys(value: Any, trail: str = "") -> List[str]:
    found: List[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in _FORBIDDEN_KEYS:
                found.append((trail + "." + lowered).lstrip("."))
            found.extend(_scan_forbidden_keys(child, trail + "." + str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_scan_forbidden_keys(child, f"{trail}[{index}]"))
    return found


def _lookup(record: Dict[str, Any], *paths: str) -> Any:
    for path in paths:
        current: Any = record
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]
        if current is not None:
            return current
    return None


def _require_hex(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _HEX64.match(value):
        raise EvidenceError(f"observed live record requires a 64-character hex {field}")
    return value


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"observed live record requires nonempty {field}")
    return value


def _sanitize_consequence(value: Any) -> Any:
    if isinstance(value, str):
        return value[:500]
    if isinstance(value, dict):
        clean: Dict[str, Any] = {}
        for key, child in value.items():
            if str(key).lower() in _FORBIDDEN_KEYS:
                continue
            if isinstance(child, (str, int, float, bool)) or child is None:
                clean[str(key)] = child[:500] if isinstance(child, str) else child
        if clean:
            return clean
    raise EvidenceError("observed live record requires a visible consequence")


def validate_observed_live_evidence(record: Any) -> Dict[str, Any]:
    """Validate an observed live record and return a sanitized subset.

    This is a mechanical evidence-shape check, not proof that a human observed
    Twitch. Fixtures, mocks, query flags and configured credentials cannot pass
    without the explicit live/observed/verified booleans and hashed receipt.
    """
    if not isinstance(record, dict):
        raise EvidenceError("observed live evidence record must be a JSON object")
    forbidden = _scan_forbidden_keys(record)
    if forbidden:
        raise EvidenceError("live record contains forbidden sensitive fields: " + ", ".join(forbidden))
    if record.get("fixture") is True:
        raise EvidenceError("fixture record cannot satisfy the observed live boundary")
    authority = record.get("authority")
    if authority is not None and authority != "authoritative-runtime":
        raise EvidenceError("live record authority must be authoritative-runtime")
    if authority is None and record.get("fixture") is not False:
        raise EvidenceError("live record without authority must set fixture false")
    if record.get("origin") != "live":
        raise EvidenceError("live record origin must be live; fixture records cannot satisfy this boundary")
    for flag in ("live_participation", "live_verified"):
        if record.get(flag) is not True:
            raise EvidenceError(f"live record requires {flag} is true")
    if record.get("observed") is not None and record.get("observed") is not True:
        raise EvidenceError("live record requires observed is true when present")

    token_valid = _lookup(record, "token_validation.validated",
                          "token_validation.valid", "token_validated")
    if token_valid is not True:
        raise EvidenceError("live record requires a successful Twitch token validation")
    user_hash = _require_hex(
        _lookup(record, "token_validation.user_id_sha256", "user_id_sha256"),
        "token_validation.user_id_sha256")
    scopes = _lookup(record, "token_validation.scopes", "scopes")
    if not isinstance(scopes, list) or "user:read:chat" not in scopes:
        raise EvidenceError("live record requires the user:read:chat OAuth scope")

    subscription_status = _lookup(record, "subscription.status")
    subscription_type = _lookup(record, "subscription.type")
    subscribed = (subscription_status == "enabled" or
                  _lookup(record, "eventsub.subscribed", "subscription.subscribed",
                          "eventsub_subscribed") is True)
    if not subscribed:
        raise EvidenceError("live record requires an EventSub subscription")
    if subscription_type is not None and subscription_type != "channel.chat.message":
        raise EvidenceError("live record subscription must be channel.chat.message")
    session_hash = _require_hex(
        _lookup(record, "session.session_id_sha256",
                "eventsub.session_id_sha256", "session_id_sha256"),
        "session.session_id_sha256")

    receipt_hash = _require_hex(
        _lookup(record, "receipt.message_id_sha256", "receipt_sha256",
                "receipt_id_sha256", "message_id_sha256", "receipt_hash"),
        "receipt_sha256")
    subject_hash = _require_hex(
        _lookup(record, "subject.linked_subject_sha256", "subject_sha256",
                "linked_subject_sha256", "subject_hash"),
        "subject_sha256")
    notified = _lookup(record, "eventsub.notification_received", "notification_received")
    if notified is None:
        # The adapter writes this record only after consuming a real
        # notification; the receipt hash is that notification's evidence.
        notified = bool(receipt_hash)
    if notified is not True:
        raise EvidenceError("live record requires a real channel.chat.message notification")

    command = _lookup(record, "command", "canonical_command")
    if not isinstance(command, dict):
        raise EvidenceError("live record requires the canonical command")
    kind = _require_text(command.get("kind"), "command.kind")
    command_status = (command.get("status") or _lookup(record, "result.status")
                      or _lookup(record, "command_result.status"))
    if command_status != "applied":
        raise EvidenceError("live record requires an applied canonical command result")
    engine_result = _lookup(record, "engine_result", "consequence.after", "result")
    if not isinstance(engine_result, dict) or not engine_result:
        raise EvidenceError("live record requires a nonempty engine result")
    consequence = _sanitize_consequence(_lookup(record, "visible_consequence", "consequence"))
    observed_at = record.get("observed_at", record.get("recorded_at"))
    if isinstance(observed_at, str) and observed_at.strip():
        observed_at = observed_at[:128]
    elif not (isinstance(observed_at, int) and observed_at >= 0):
        raise EvidenceError("live record requires observed_at or recorded_at")

    public_result = {
        key: engine_result[key] for key in sorted(engine_result)
        if key in {"tick", "turn", "phase", "status", "progress", "progress_percent",
                   "district", "sequence", "result", "lane", "lateral_pos",
                   "collisions_total", "pool", "summary", "reason"}
    }
    if not public_result:
        raise EvidenceError("live record engine result has no public fields")

    return {
        "schema_version": 1,
        "authority": "authoritative-runtime",
        "origin": "live",
        "live_participation": True,
        "live_verified": True,
        "fixture": False,
        "observed": True,
        "observed_at": observed_at,
        "token_validation": {
            "validated": True,
            "user_id_sha256": user_hash,
            "scopes": sorted(str(scope) for scope in scopes),
        },
        "eventsub": {
            "subscribed": True,
            "session_id_sha256": session_hash,
            "notification_received": True,
        },
        "receipt": {"message_id_sha256": receipt_hash},
        "subject": {"linked_subject_sha256": subject_hash},
        "command": {
            "kind": kind[:128],
            "status": "applied",
            "sequence": command.get("sequence"),
            "tick": command.get("logical_tick", command.get("tick")),
        },
        "engine_result": public_result,
        "visible_consequence": consequence,
    }


# ---------------------------------------------------------------------------
# Video evidence boundary
# ---------------------------------------------------------------------------
def _verify_artifact_mapping(item: Any, label: str) -> Tuple[Dict[str, Any], str]:
    if not isinstance(item, dict):
        raise EvidenceError(f"{label} capture metadata is required")
    path = item.get("path")
    digest = item.get("sha256")
    if not isinstance(path, str) or not path:
        raise EvidenceError(f"{label} capture path is required")
    _require_hex(digest, f"{label} capture sha256")
    target = (ROOT / path).resolve()
    if ROOT not in target.parents or not target.is_file():
        raise EvidenceError(f"{label} capture file is missing or outside the repository: {path}")
    if sha256_file(target) != digest:
        raise EvidenceError(f"{label} capture hash does not match: {path}")
    return item, digest


def evaluate_video_evidence(record: Any) -> Dict[str, Any]:
    """Return a fail-closed final-video decision for a composed evidence manifest."""
    failures: List[str] = []
    normalized: Optional[Dict[str, Any]] = None
    if isinstance(record, dict) and record.get("origin") != "live":
        failures.append("manifest origin must be live; fixture captures cannot satisfy the video predicate")
    try:
        normalized = validate_observed_live_evidence(record)
    except EvidenceError as exc:
        failures.append(str(exc))

    if isinstance(record, dict):
        capture = record.get("capture")
        if not isinstance(capture, dict):
            failures.append("observed capture manifest is required")
        else:
            if capture.get("mode") != "live":
                failures.append("capture mode must be live; fixture captures cannot satisfy the video predicate")
            if capture.get("live_verified") is not True:
                failures.append("capture must be live_verified")
            for label, expected_size in (("desktop", VIEWPORTS["desktop"]),
                                         ("mobile", VIEWPORTS["mobile"])):
                item = capture.get(label)
                try:
                    _verify_artifact_mapping(item, label)
                    if item.get("width") != expected_size[0] or item.get("height") != expected_size[1]:
                        failures.append(f"{label} capture must be {expected_size[0]}x{expected_size[1]}")
                except EvidenceError as exc:
                    failures.append(str(exc))

        segments = record.get("video_segments")
        if not isinstance(segments, list) or len(segments) != len(REQUIRED_VIDEO_SEGMENTS):
            failures.append("video_segments must list exactly the required ordered segments")
        else:
            roles = [segment.get("role") for segment in segments if isinstance(segment, dict)]
            if tuple(roles) != REQUIRED_VIDEO_SEGMENTS:
                failures.append("video segment order must be: " + ", ".join(REQUIRED_VIDEO_SEGMENTS))
            total = 0.0
            for index, segment in enumerate(segments):
                label = f"video segment {index + 1}"
                if not isinstance(segment, dict):
                    failures.append(f"{label} must be an object")
                    continue
                duration = segment.get("duration_seconds")
                if not isinstance(duration, (int, float)) or duration <= 0:
                    failures.append(f"{label} requires a positive duration_seconds")
                else:
                    total += float(duration)
                try:
                    _verify_artifact_mapping(segment, label)
                except EvidenceError as exc:
                    failures.append(str(exc))
            if total >= MAX_VIDEO_SECONDS or total <= 0:
                failures.append(f"planned duration must be under {int(MAX_VIDEO_SECONDS)} seconds")
        if "duration_seconds" in record and isinstance(record["duration_seconds"], (int, float)):
            if float(record["duration_seconds"]) >= MAX_VIDEO_SECONDS:
                failures.append(f"declared video duration must be under {int(MAX_VIDEO_SECONDS)} seconds")

    return {
        "schema_version": 1,
        "eligible": not failures,
        "failures": failures,
        "record_sha256": sha256_bytes(canonical_bytes(record)) if record is not None else None,
        "live_verified": bool(normalized and normalized.get("live_verified") is True),
        "rule": "A final video requires observed live evidence, live desktop/mobile captures "
                "and the ordered Twitch-to-Codex segments. Fixtures and rehearsals never qualify.",
    }


# ---------------------------------------------------------------------------
# Browser capture
# ---------------------------------------------------------------------------
_CONTRAST_JS = r"""
() => {
  const parse = (value) => {
    const match = String(value).match(/rgba?\(([^)]+)\)/);
    if (!match) return null;
    const parts = match[1].split(/[ ,\/]+/).filter(Boolean).map(Number);
    if (parts.length < 3 || parts.some((part) => Number.isNaN(part))) return null;
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  };
  const luminance = (color) => {
    const channel = (value) => {
      const scaled = value / 255;
      return scaled <= 0.03928 ? scaled / 12.92 : Math.pow((scaled + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * channel(color.r) + 0.7152 * channel(color.g) + 0.0722 * channel(color.b);
  };
  const background = (element) => {
    let node = element;
    while (node) {
      const color = parse(getComputedStyle(node).backgroundColor);
      if (color && color.a > 0.5) return color;
      node = node.parentElement;
    }
    return { r: 255, g: 255, b: 255, a: 1 };
  };
  const ratio = (one, two) => {
    const first = luminance(one), second = luminance(two);
    const light = Math.max(first, second), dark = Math.min(first, second);
    return (light + 0.05) / (dark + 0.05);
  };
  const selectors = [
    'body', '[data-hud=mode]', '[data-hud=mode-detail]', '.hud-status',
    '[data-hud=preview]', '[data-hud=status]', '[data-hud=pool]', '.note',
  ];
  return selectors.map((selector) => {
    const element = document.querySelector(selector);
    if (!element) return { selector, missing: true, pass: false };
    const style = getComputedStyle(element);
    if (style.display === 'none' || style.visibility === 'hidden') {
      return { selector, hidden: true, pass: true };
    }
    const foreground = parse(style.color);
    const behind = background(element);
    if (!foreground) return { selector, missing: true, pass: false };
    const size = parseFloat(style.fontSize);
    const bold = parseInt(style.fontWeight, 10) >= 700;
    const large = size >= 24 || (size >= 18.66 && bold);
    const value = ratio(foreground, behind);
    return {
      selector,
      foreground: style.color,
      background: `rgb(${behind.r}, ${behind.g}, ${behind.b})`,
      ratio: Number(value.toFixed(2)),
      minimum: large ? 3 : 4.5,
      pass: value >= (large ? 3 : 4.5),
    };
  });
}
"""


def _measure(page: Any) -> Dict[str, Any]:
    return page.evaluate(
        """
        () => {
          const width = window.innerWidth;
          const offenders = Array.from(document.querySelectorAll('body *')).filter((element) => {
            const style = getComputedStyle(element);
            if (style.display === 'none' || style.visibility === 'hidden') return false;
            const rect = element.getBoundingClientRect();
            return rect.width > 0 && (rect.right > width + 1 || rect.left < -1);
          }).slice(0, 8).map((element) => {
            const rect = element.getBoundingClientRect();
            return {
              tag: element.tagName.toLowerCase(),
              id: element.id || null,
              className: typeof element.className === 'string' ? element.className : null,
              left: Number(rect.left.toFixed(1)),
              right: Number(rect.right.toFixed(1)),
            };
          });
          return {
            innerWidth: width,
            innerHeight: window.innerHeight,
            documentScrollWidth: document.documentElement.scrollWidth,
            bodyScrollWidth: document.body.scrollWidth,
            overflow: document.documentElement.scrollWidth > width + 1 ||
                      document.body.scrollWidth > width + 1,
            offenders,
          };
        }
        """,
    )


def _page_accessibility(page: Any, mode: str, css: str, measure: Dict[str, Any]) -> Dict[str, Any]:
    raw = page.evaluate(
        """
        () => {
          const buttons = Array.from(document.querySelectorAll('button')).map((button) => ({
            name: (button.getAttribute('aria-label') || button.textContent || '').trim(),
            disabled: button.disabled,
            control: button.getAttribute('data-control'),
          }));
          const liveRegions = Array.from(document.querySelectorAll('[aria-live]')).map((node) => ({
            tag: node.tagName.toLowerCase(),
            live: node.getAttribute('aria-live'),
            text: (node.textContent || '').trim().slice(0, 120),
          }));
          const viewport = document.querySelector('meta[name=viewport]');
          const canvas = document.querySelector('canvas');
          return {
            lang: document.documentElement.lang || '',
            title: document.title || '',
            viewport: viewport ? viewport.getAttribute('content') : null,
            buttons,
            liveRegions,
            canvasLabel: canvas ? canvas.getAttribute('aria-label') : null,
            badge: (document.querySelector('[data-hud=badge]') || {}).textContent || '',
            mode: (document.querySelector('[data-hud=mode]') || {}).textContent || '',
            modeData: (document.querySelector('[data-hud=mode]') || {}).getAttribute
              ? document.querySelector('[data-hud=mode]').getAttribute('data-mode') : null,
          };
        }
        """,
    )
    contrast = page.evaluate(_CONTRAST_JS)
    checks: List[Dict[str, Any]] = []

    def check(ident: str, passed: bool, detail: str) -> None:
        checks.append({"id": ident, "pass": bool(passed), "detail": detail})

    check("html-lang", raw["lang"] == "en", f"lang={raw['lang'] or 'missing'}")
    check("document-title", bool(raw["title"]), raw["title"] or "missing title")
    check("viewport-meta", bool(raw["viewport"] and "width=device-width" in raw["viewport"]),
          raw["viewport"] or "missing viewport meta")
    names = [button["name"] for button in raw["buttons"]]
    unnamed = [button for button in raw["buttons"] if not button["name"]]
    check("accessible-button-names", not unnamed, f"{len(names)} buttons checked")
    check("steer-labels", all(name in names for name in ("Steer left", "Steer right")),
          ", ".join(name for name in names if name.startswith("Steer")))
    check("canvas-label", bool(raw["canvasLabel"]), raw["canvasLabel"] or "missing canvas label")
    check("live-regions", len(raw["liveRegions"]) >= 2,
          f"{len(raw['liveRegions'])} aria-live regions")
    check("focus-visible", ":focus-visible" in css, "CSS focus-visible outline present")
    check("reduced-motion", "prefers-reduced-motion" in css, "CSS reduced-motion rule present")
    check("no-horizontal-overflow", not measure["overflow"],
          f"scrollWidth={measure['documentScrollWidth']} innerWidth={measure['innerWidth']}")
    control_buttons = [button for button in raw["buttons"] if button["control"]]
    if mode == "disconnected":
        check("controls-disabled", all(button["disabled"] for button in control_buttons),
              f"{len(control_buttons)} control buttons disabled")
        check("badge-disconnected", "DISCONNECTED" in raw["badge"], raw["badge"] or "missing badge")
        check("mode-disconnected", "Disconnected" in raw["mode"], raw["mode"] or "missing mode")
    elif mode == "fixture":
        check("controls-enabled", all(not button["disabled"] for button in control_buttons),
              f"{len(control_buttons)} control buttons enabled")
        check("badge-fixture", "OFFLINE FIXTURE" in raw["badge"], raw["badge"] or "missing badge")
        check("mode-fixture", "Offline fixture" in raw["mode"], raw["mode"] or "missing mode")
    else:
        check("controls-enabled", all(not button["disabled"] for button in control_buttons),
              f"{len(control_buttons)} control buttons enabled")
        check("badge-live", "LIVE" in raw["badge"], raw["badge"] or "missing badge")
        check("mode-live", "live" in raw["mode"].lower(), raw["mode"] or "missing mode")
        check("not-fixture-labelled", "fixture" not in raw["mode"].lower(), raw["mode"])
    check("contrast", all(item.get("pass") for item in contrast),
          "; ".join(f"{item['selector']}={item.get('ratio', 'n/a')}" for item in contrast))
    return {
        "schema_version": 1,
        "mode": mode,
        "checks": checks,
        "contrast": contrast,
        "live_regions": raw["liveRegions"],
        "buttons": raw["buttons"],
        "passed": all(item["pass"] for item in checks),
    }


def _launch_playwright() -> Any:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment dependent
        raise CaptureUnavailable(
            "Playwright is required for rendered capture: pip install playwright && "
            "python -m playwright install chromium") from exc
    return sync_playwright


def _chromium_executable() -> Optional[str]:
    """Use an explicitly configured or already-installed Chromium binary.

    The pinned Playwright package can expect a browser build that is absent
    while a compatible build is present in the local cache. This never
    downloads anything; callers may set PLAYWRIGHT_CHROMIUM_EXECUTABLE.
    """
    configured = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if configured and Path(configured).is_file():
        return configured
    cache = Path.home() / ".cache" / "ms-playwright"
    if not cache.is_dir():
        return None
    candidates = sorted(cache.glob("chromium-*/chrome-linux*/chrome"), reverse=True)
    candidates += sorted(cache.glob("chromium_headless_shell-*/chrome-headless-shell-linux64/"
                                    "chrome-headless-shell"), reverse=True)
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _run_capture(mode: str, output: Path, url: Optional[str],
                 normalized_live: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    sync_playwright = _launch_playwright()
    css = (CLIENT / "style.css").read_text(encoding="utf-8")
    document = _fixture_document(mode) if mode in ("fixture", "disconnected") else None
    blocked: List[str] = []
    page_errors: List[str] = []
    with sync_playwright() as playwright:
            executable = _chromium_executable()
            try:
                browser = playwright.chromium.launch(
                    headless=True,
                    executable_path=executable,
                ) if executable else playwright.chromium.launch(headless=True)
            except Exception as exc:  # pragma: no cover - environment dependent
                raise CaptureUnavailable(
                    "Chromium launch failed; install a Playwright browser or set "
                    "PLAYWRIGHT_CHROMIUM_EXECUTABLE: " + str(exc)) from exc
            try:
                context = browser.new_context(
                    viewport={"width": VIEWPORTS["desktop"][0], "height": VIEWPORTS["desktop"][1]},
                    reduced_motion="reduce",
                )

                def guard(route: Any, request: Any) -> None:
                    request_url = request.url
                    if request_url.startswith(("data:", "blob:", "about:blank")):
                        route.continue_()
                    elif url and _same_origin(request_url, url):
                        route.continue_()
                    else:
                        blocked.append(request_url)
                        route.abort()

                context.route("**/*", guard)
                page = context.new_page()
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                captures: List[Dict[str, Any]] = []
                measures: Dict[str, Any] = {}
                accessibility: Dict[str, Any] = {}
                for target in ("desktop", "mobile"):
                    width, height = VIEWPORTS[target]
                    page.set_viewport_size({"width": width, "height": height})
                    if document is not None:
                        page.set_content(document, wait_until="load")
                    else:
                        if not url:
                            raise EvidenceError("live capture requires an explicit loopback URL")
                        page.goto(url, wait_until="domcontentloaded")
                    try:
                        page.wait_for_function(
                            "(expected) => { const node = document.querySelector('[data-hud=mode]');"
                            " return !!node && node.getAttribute('data-mode') === expected; }",
                            arg=mode, timeout=15000,
                        )
                    except Exception as exc:  # Playwright timeout / navigation failure
                        raise EvidenceError(
                            f"{mode} mode was not presented by the page: {exc}") from exc
                    page.wait_for_timeout(250)
                    if mode == "live":
                        probe = page.evaluate(
                            """
                            async () => {
                              const response = await fetch('/api/state', {cache: 'no-store'});
                              if (!response.ok) return null;
                              const envelope = await response.json();
                              return envelope && envelope.evidence ? envelope.evidence : null;
                            }
                            """
                        )
                        if not isinstance(probe, dict) or probe.get("origin") != "live" \
                                or probe.get("live_participation") is not True \
                                or probe.get("live_verified") is not True:
                            raise EvidenceError(
                                "live page did not expose verified server-owned live evidence")
                        expected_session = (normalized_live or {}).get("eventsub", {}).get(
                            "session_id_sha256")
                        observed_session = (probe.get("adapter") or {}).get(
                            "session_id_sha256")
                        if expected_session and observed_session and expected_session != observed_session:
                            raise EvidenceError(
                                "supplied live record session does not match the running page")
                    if page_errors:
                        raise EvidenceError("page errors during capture: " + "; ".join(page_errors))
                    if blocked:
                        raise EvidenceError("blocked non-local request during capture: " + "; ".join(blocked))
                    measure = _measure(page)
                    measures[target] = measure
                    shot = output / f"{mode}-{target}.png"
                    page.screenshot(path=str(shot), full_page=False)
                    accessibility[target] = _page_accessibility(page, mode, css, measure)
                    if not accessibility[target]["passed"]:
                        failed = [item["id"] for item in accessibility[target]["checks"]
                                  if not item["pass"]]
                        raise EvidenceError(f"{mode} {target} accessibility checks failed: "
                                            + ", ".join(failed))
                    captures.append({
                        "target": target,
                        "file": shot.name,
                        "width": width,
                        "height": height,
                        "sha256": sha256_file(shot),
                        "label": LABELS[mode],
                        "overflow": measure["overflow"],
                        "offenders": measure["offenders"],
                    })
                browser.close()
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
    if page_errors:
        raise EvidenceError("page errors during capture: " + "; ".join(page_errors))
    return {"captures": captures, "measures": measures, "accessibility": accessibility,
            "blocked": blocked, "page_errors": page_errors}


def capture(mode: str, output: Path, *, url: Optional[str] = None,
            evidence_path: Optional[Path] = None, force: bool = False) -> Dict[str, Any]:
    if mode not in MODES:
        raise EvidenceError(f"unknown capture mode: {mode}")
    if mode == "live":
        if not url:
            raise EvidenceError("live capture requires an explicit loopback --url")
        validate_local_url(url)
        if evidence_path is None:
            raise EvidenceError("live capture requires an observed live evidence record")
        source_record = read_json(evidence_path)
        normalized_live = validate_observed_live_evidence(source_record)
        source_record_hash = sha256_file(evidence_path)
    else:
        if url:
            raise EvidenceError("--url is only valid with --mode live")
        if evidence_path:
            raise EvidenceError("--evidence is only valid with --mode live")
        normalized_live = None
        source_record_hash = None

    output = output.resolve()
    parent = output.parent
    parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if not force and any(output.iterdir()):
            raise EvidenceError(f"capture destination is not empty; pass --force to replace: {output}")
        shutil.rmtree(output)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=parent))
    committed = False
    try:
        rendered = _run_capture(mode, temporary, url, normalized_live)
        accessibility_bytes = write_json(temporary / "accessibility.json", rendered["accessibility"])
        plan = build_capture_plan(mode)
        timeline = {
            "schema_version": 1,
            "tool": "tools/capture_submission.py",
            "mode": mode,
            "label": LABELS[mode],
            "live_verified": mode == "live",
            "plan": plan,
            "captures": rendered["captures"],
            "measurements": rendered["measures"],
            "accessibility_sha256": sha256_bytes(accessibility_bytes),
            "blocked_requests": rendered["blocked"],
            "page_errors": rendered["page_errors"],
        }
        if mode == "live":
            timeline["live_evidence_sha256"] = source_record_hash
            timeline["live_evidence"] = normalized_live
            write_json(temporary / "live-evidence.json", normalized_live)
        timeline_bytes = write_json(temporary / "timeline.json", timeline)
        artifacts = {
            item["file"]: {"sha256": item["sha256"], "width": item["width"],
                           "height": item["height"]}
            for item in rendered["captures"]
        }
        artifacts["accessibility.json"] = {"sha256": sha256_bytes(accessibility_bytes)}
        artifacts["timeline.json"] = {"sha256": sha256_bytes(timeline_bytes)}
        if mode == "live":
            artifacts["live-evidence.json"] = {
                "sha256": sha256_file(temporary / "live-evidence.json"),
                "source_record_sha256": source_record_hash,
            }
        manifest = {
            "schema_version": 1,
            "tool": "tools/capture_submission.py",
            "mode": mode,
            "label": LABELS[mode],
            "live_verified": mode == "live",
            "submission_video_eligible": False,
            "source_bindings": plan["source_bindings"],
            "artifacts": artifacts,
            "timeline_sha256": sha256_bytes(timeline_bytes),
            "notes": [
                "Fixture and disconnected captures are offline renders; they are not live Twitch evidence.",
                "Live captures require an observed, adapter-verified evidence record.",
                "The final video additionally requires the ordered Twitch-to-Codex segments "
                "and is never produced from fixtures.",
            ],
        }
        write_json(temporary / "CAPTURE-MANIFEST.json", manifest)
        temporary.replace(output)
        committed = True
        summary = {
            "ok": True,
            "mode": mode,
            "output": str(output),
            "manifest_sha256": sha256_file(output / "CAPTURE-MANIFEST.json"),
            "timeline_sha256": manifest["timeline_sha256"],
            "artifacts": {name: item["sha256"] for name, item in artifacts.items()},
            "live_verified": manifest["live_verified"],
        }
        return summary
    finally:
        if not committed and temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


# ---------------------------------------------------------------------------
# Verification and video assembly
# ---------------------------------------------------------------------------
def verify_capture(directory: Path) -> Dict[str, Any]:
    manifest_path = directory / "CAPTURE-MANIFEST.json"
    manifest = read_json(manifest_path)
    failures: List[str] = []
    mode = manifest.get("mode")
    if mode not in MODES:
        failures.append("manifest mode is invalid")
    if manifest.get("live_verified") is True and mode != "live":
        failures.append("non-live capture claims live verification")
    if mode != "live" and manifest.get("live_verified") is not False:
        failures.append("fixture/disconnected capture must label live_verified false")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        failures.append("manifest artifacts are missing")
    else:
        for name, item in artifacts.items():
            target = directory / name
            if not target.is_file():
                failures.append(f"missing artifact: {name}")
                continue
            if sha256_file(target) != item.get("sha256"):
                failures.append(f"hash mismatch: {name}")
        for name in ("desktop", "mobile"):
            if f"{mode}-{name}.png" not in artifacts:
                failures.append(f"missing {name} PNG artifact")
    timeline_path = directory / "timeline.json"
    if timeline_path.is_file():
        if sha256_file(timeline_path) != manifest.get("timeline_sha256"):
            failures.append("timeline hash mismatch")
    else:
        failures.append("timeline.json is missing")
    if mode == "live":
        live_path = directory / "live-evidence.json"
        if not live_path.is_file():
            failures.append("live capture is missing live-evidence.json")
        else:
            try:
                validate_observed_live_evidence(read_json(live_path))
            except EvidenceError as exc:
                failures.append("live evidence is invalid: " + str(exc))
    return {"schema_version": 1, "ok": not failures, "failures": failures,
            "mode": mode, "live_verified": manifest.get("live_verified") is True}


def assemble_video(evidence_path: Path, output: Optional[Path] = None) -> Dict[str, Any]:
    record = read_json(evidence_path)
    decision = evaluate_video_evidence(record)
    if not decision["eligible"]:
        return decision
    if output is None:
        decision["assembled"] = False
        decision["note"] = "evidence is structurally eligible; pass --out to encode with ffmpeg"
        return decision
    segments = record["video_segments"]
    concat_lines: List[str] = []
    for segment in segments:
        target = (ROOT / segment["path"]).resolve()
        escaped = str(target).replace("'", "'\\''")
        concat_lines.append(f"file '{escaped}'")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
        handle.write("\n".join(concat_lines) + "\n")
        list_path = Path(handle.name)
    try:
        try:
            completed = subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(output)],
                capture_output=True, text=True, check=False,
            )
        except FileNotFoundError:
            decision["eligible"] = False
            decision["failures"].append("ffmpeg is required to encode the final video")
            return decision
        if completed.returncode != 0:
            decision["eligible"] = False
            decision["failures"].append("ffmpeg assembly failed: " + (completed.stderr or "")[-500:])
            return decision
    finally:
        list_path.unlink(missing_ok=True)
    if not output.is_file():
        decision["eligible"] = False
        decision["failures"].append("ffmpeg did not produce the output file")
        return decision
    decision.update({"assembled": True, "output": str(output),
                     "video_sha256": sha256_file(output)})
    return decision


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline presentation capture and fail-closed submission video boundary.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture_parser = subparsers.add_parser("capture", help="capture desktop and mobile PNGs")
    capture_parser.add_argument("--mode", choices=MODES, default="fixture")
    capture_parser.add_argument("--out", type=Path)
    capture_parser.add_argument("--url", help="explicit loopback URL for --mode live only")
    capture_parser.add_argument("--evidence", type=Path,
                                help="observed live evidence JSON for --mode live only")
    capture_parser.add_argument("--force", action="store_true",
                                help="replace a non-empty capture destination")
    verify_parser = subparsers.add_parser("verify", help="recompute capture artifact hashes")
    verify_parser.add_argument("directory", type=Path)
    assemble_parser = subparsers.add_parser(
        "assemble", help="evaluate or encode the final video from observed evidence")
    assemble_parser.add_argument("--evidence", type=Path, required=True)
    assemble_parser.add_argument("--out", type=Path)
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "capture":
            output = args.out or (DEFAULT_EVIDENCE_ROOT / args.mode)
            summary = capture(args.mode, output, url=args.url,
                              evidence_path=args.evidence, force=args.force)
        elif args.command == "verify":
            summary = verify_capture(args.directory)
        else:
            summary = assemble_video(args.evidence, args.out)
    except (EvidenceError, CaptureUnavailable) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True),
              file=sys.stderr)
        return 3
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("ok", summary.get("eligible", False)) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
