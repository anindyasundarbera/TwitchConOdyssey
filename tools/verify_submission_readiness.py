"""Mechanical submission-readiness verifier.

Evaluates a JSON readiness record against explicit, offline predicates. It
reads local files, recomputes SHA-256 digests and the sealed-root sorted-tree
digest, and may query local Git metadata. It never uses the network, starts a
service, executes gameplay, contacts Twitch, or trusts publication booleans as
evidence. Missing, stale or fixture-only predicates return
``submission_ready: false`` with exact reasons.

Usage:
    python3 -m tools.verify_submission_readiness [RECORD]
    python3 -m tools.verify_submission_readiness --require-ready
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORD = "docs/submission/SUBMISSION-METADATA.json"
SEALED_ROOT_ALGORITHM = "sha256-sorted-relative-path-colon-file-sha256-lf-v1"
USER_CHAT_SCOPE = "user:read:chat"

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_PLACEHOLDER_MARKERS = ("<", ">", "replace", "todo", "pending", "example.com",
                        "example.org", "localhost", "127.0.0.1")
_FORBIDDEN_KEYS = frozenset({
    "raw_chat",
    "chat_text",
    "chat_message",
    "message",
    "message_text",
    "viewer_message",
    "oauth_token",
    "access_token",
    "refresh_token",
    "user_token",
    "token",
    "client_secret",
    "client_id",
    "password",
    "secret",
    "authorization_header",
    "user_id",
    "broadcaster_user_id",
    "chatter_user_id",
    "channel_login",
})
_FORBIDDEN_VALUE_PREFIXES = ("oauth:", "bearer ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_tree_sha256(root: Path) -> str:
    """Aggregate sorted tree hash over ``<rel_path>:<sha256>\\n`` lines."""
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"directory does not exist: {root}")
    lines: List[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            lines.append(f"{rel}:{sha256_file(path)}\n")
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def png_dimensions(path: Path) -> Tuple[int, int]:
    """Read PNG width/height from the IHDR chunk without third-party imports."""
    with Path(path).open("rb") as handle:
        header = handle.read(33)
    if len(header) < 33 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"not a PNG with an IHDR header: {path}")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    if width <= 0 or height <= 0:
        raise ValueError(f"non-positive PNG dimensions: {path}")
    return width, height


def local_git_state(repo: Path) -> Optional[Dict[str, str]]:
    """Return local HEAD and tracked-diff digest; no network access."""
    repo = Path(repo)
    try:
        head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True, capture_output=True,
        ).stdout.decode("utf-8").strip()
        diff = subprocess.run(
            ["git", "-C", str(repo), "diff", "HEAD", "--binary"],
            check=True, capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return {"head": head, "tracked_diff_sha256": hashlib.sha256(diff).hexdigest()}


def _is_text(value: Any) -> bool:
    return type(value) is str and bool(value.strip())


def _is_sha1(value: Any) -> bool:
    return _is_text(value) and bool(_SHA1_RE.fullmatch(value))


def _is_sha256(value: Any) -> bool:
    return _is_text(value) and bool(_SHA256_RE.fullmatch(value))


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if type(value) is dict else {}


def _parse_iso(value: Any) -> Optional[datetime]:
    if not _is_text(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _repo_path(repo: Path, value: Any) -> Optional[Path]:
    if not _is_text(value):
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        return None
    root = Path(repo).resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def _url_is_placeholder(value: Any) -> bool:
    if not _is_text(value):
        return True
    lowered = value.lower()
    return any(marker in lowered for marker in _PLACEHOLDER_MARKERS)


def _contains_forbidden_material(value: Any, key: Optional[str] = None) -> bool:
    if key is not None and key.lower() in _FORBIDDEN_KEYS:
        return True
    if type(value) is dict:
        return any(_contains_forbidden_material(item, name) for name, item in value.items())
    if type(value) is list:
        return any(_contains_forbidden_material(item) for item in value)
    if type(value) is str:
        lowered = value.strip().lower()
        return any(prefix in lowered for prefix in _FORBIDDEN_VALUE_PREFIXES)
    return False


class _Checks:
    def __init__(self) -> None:
        self.results: Dict[str, bool] = {}
        self.reasons: List[str] = []

    def check(self, name: str, passed: Any, reason: str) -> bool:
        passed = bool(passed)
        self.results[name] = passed
        if not passed:
            self.reasons.append(f"{name}: {reason}")
        return passed


def _verify_file(checks: _Checks, repo: Path, label: str, path_value: Any,
                 digest_value: Any) -> Optional[Path]:
    if not checks.check(f"{label}.path", _is_text(path_value),
                        f"{label}.path must be bounded nonempty text"):
        return None
    path = _repo_path(repo, path_value)
    if path is None:
        checks.check(f"{label}.path_inside_repository", False,
                     f"{label}.path must stay inside the repository")
        return None
    if not path.is_file():
        checks.check(f"{label}.file_exists", False,
                     f"{label}.file is missing: {path_value}")
        return None
    if not checks.check(f"{label}.sha256_format", _is_sha256(digest_value),
                        f"{label}.sha256 must be 64 lowercase hex characters"):
        return path
    actual = sha256_file(path)
    checks.check(f"{label}.sha256_matches", actual == digest_value,
                 f"{label}.sha256 does not match current bytes")
    return path


def _default_package_checker(repo: Path, manifest_path: Any) -> Dict[str, Any]:
    from tools.package_submission import check

    package_dir = repo / str(manifest_path)
    result = check(package_dir)
    manifest = json.loads((package_dir / "MANIFEST.json").read_text())
    artifact_set = _as_dict(manifest.get("artifact_set"))
    return {
        "status": result.get("status"),
        "complete": bool(artifact_set.get("complete")),
        "verified": int(result.get("verified", 0)),
    }


def evaluate_record(record: Any, repo: Path = ROOT,
                    git_state: Optional[Dict[str, str]] = None,
                    package_checker: Optional[Callable[[Path, Any], Dict[str, Any]]] = None,
                    now: Optional[datetime] = None) -> Dict[str, Any]:
    """Evaluate one readiness record and return the derived result."""
    repo = Path(repo)
    now = now or datetime.now(timezone.utc)
    checks = _Checks()

    if type(record) is not dict:
        return {
            "schema_version": 1,
            "submission_ready": False,
            "reasons": ["record must be a JSON object"],
            "checks": {"record.is_object": False},
            "predicate_count": 1,
            "passed_predicate_count": 0,
            "declared_submission_ready": None,
            "publication": {},
            "evaluated_head": None,
        }

    checks.check("schema_version", record.get("schema_version") == 1,
                 "schema_version must be 1")
    checks.check("record_id", _is_text(record.get("record_id")),
                 "record_id must be bounded nonempty text")
    checks.check("evaluated_at", _is_text(record.get("evaluated_at")),
                 "evaluated_at must be bounded nonempty text")
    checks.check("declared_submission_ready.is_boolean",
                 type(record.get("declared_submission_ready")) is bool,
                 "declared_submission_ready must be a boolean (advisory only)")

    candidate = _as_dict(record.get("candidate"))
    checks.check("candidate.starting_head", _is_sha1(candidate.get("starting_head")),
                 "candidate.starting_head must be a 40-character hex SHA-1")
    checks.check("candidate.final_head", _is_sha1(candidate.get("final_head")),
                 "candidate.final_head must be a 40-character hex SHA-1")
    checks.check("candidate.tracked_diff_sha256",
                 _is_sha256(candidate.get("tracked_diff_sha256")),
                 "candidate.tracked_diff_sha256 must be a 64-character hex SHA-256")
    if git_state is None:
        checks.check("candidate.git_state_available", False,
                     "local Git metadata is unavailable; final-head and diff freshness cannot be checked")
    else:
        checks.check("candidate.final_head_matches_head",
                     candidate.get("final_head") == git_state.get("head"),
                     "candidate.final_head is stale: it does not match the local HEAD")
        checks.check("candidate.tracked_diff_matches_worktree",
                     candidate.get("tracked_diff_sha256") == git_state.get("tracked_diff_sha256"),
                     "candidate.tracked_diff_sha256 is stale: it does not match git diff HEAD --binary")

    live = _as_dict(record.get("live"))
    checks.check("live.live_validated", live.get("live_validated") is True,
                 "live.live_validated must be true from an observed live receipt")
    token = _as_dict(live.get("token_validation"))
    checks.check("live.token_validation.validated", token.get("validated") is True,
                 "live.token_validation.validated must be true")
    scopes = token.get("scopes")
    checks.check("live.token_validation.scopes",
                 type(scopes) is list and USER_CHAT_SCOPE in scopes,
                 f"live.token_validation.scopes must include {USER_CHAT_SCOPE}")
    checks.check("live.token_validation.origin",
                 token.get("origin") == "observed_live",
                 "live.token_validation.origin must be 'observed_live', not fixture")
    checks.check("live.token_validation.validated_at", _is_text(token.get("validated_at")),
                 "live.token_validation.validated_at must be recorded")
    checks.check("live.token_validation.client_id_sha256",
                 _is_sha256(token.get("client_id_sha256")),
                 "live.token_validation.client_id_sha256 must be a SHA-256")
    checks.check("live.token_validation.user_id_sha256",
                 _is_sha256(token.get("user_id_sha256")),
                 "live.token_validation.user_id_sha256 must be a SHA-256")
    expires = _parse_iso(token.get("expires_at"))
    checks.check("live.token_validation.expires_at", expires is not None,
                 "live.token_validation.expires_at must be a timezone-aware ISO-8601 timestamp")
    if expires is not None:
        checks.check("live.token_validation.unexpired", expires > now,
                     "live.token_validation.expires_at is stale: the token is expired")

    eventsub = _as_dict(live.get("eventsub"))
    checks.check("live.eventsub.connected", eventsub.get("connected") is True,
                 "live.eventsub.connected must be true")
    checks.check("live.eventsub.subscription_type",
                 eventsub.get("subscription_type") == "channel.chat.message",
                 "live.eventsub.subscription_type must be channel.chat.message")
    checks.check("live.eventsub.subscription_version",
                 eventsub.get("subscription_version") == "1",
                 "live.eventsub.subscription_version must be 1")
    checks.check("live.eventsub.subscription_id", _is_text(eventsub.get("subscription_id")),
                 "live.eventsub.subscription_id must be recorded")
    checks.check("live.eventsub.session_id", _is_text(eventsub.get("session_id")),
                 "live.eventsub.session_id must be recorded")
    checks.check("live.eventsub.receipt_id_sha256",
                 _is_sha256(eventsub.get("receipt_id_sha256")),
                 "live.eventsub.receipt_id_sha256 must be a SHA-256")
    checks.check("live.eventsub.received_at", _is_text(eventsub.get("received_at")),
                 "live.eventsub.received_at must be recorded")

    command = _as_dict(live.get("canonical_command"))
    checks.check("live.canonical_command.command", _is_text(command.get("command")),
                 "live.canonical_command.command must be recorded")
    checks.check("live.canonical_command.result",
                 command.get("result") == "applied",
                 "live.canonical_command.result must be 'applied'")
    checks.check("live.canonical_command.visible_consequence",
                 _is_text(command.get("visible_consequence")),
                 "live.canonical_command.visible_consequence must be recorded")
    checks.check("live.canonical_command.consequence_sha256",
                 _is_sha256(command.get("consequence_sha256")),
                 "live.canonical_command.consequence_sha256 must be a SHA-256")

    captures = _as_dict(record.get("captures"))
    for name, expected in (("desktop", (1440, 1100)), ("mobile", (390, 844))):
        capture = _as_dict(captures.get(name))
        prefix = f"captures.{name}"
        checks.check(f"{prefix}.present", bool(capture),
                     f"{prefix} must be recorded")
        checks.check(f"{prefix}.origin", capture.get("origin") == "live",
                     f"{prefix}.origin must be 'live', not fixture")
        path = _verify_file(checks, repo, prefix, capture.get("path"),
                            capture.get("sha256"))
        checks.check(f"{prefix}.width", capture.get("width") == expected[0],
                     f"{prefix}.width must be {expected[0]}")
        checks.check(f"{prefix}.height", capture.get("height") == expected[1],
                     f"{prefix}.height must be {expected[1]}")
        if path is not None:
            try:
                actual = png_dimensions(path)
            except (OSError, ValueError) as exc:
                checks.check(f"{prefix}.png_dimensions", False, f"{prefix}: {exc}")
            else:
                checks.check(f"{prefix}.png_dimensions", actual == expected,
                             f"{prefix}.png_dimensions must be {expected[0]}x{expected[1]}")

    video = _as_dict(record.get("video"))
    video_path = _verify_file(checks, repo, "video", video.get("path"),
                              video.get("sha256"))
    del video_path  # existence and bytes are already checked above
    duration = video.get("duration_seconds")
    checks.check("video.duration_seconds",
                 type(duration) in (int, float) and not isinstance(duration, bool)
                 and 0 < float(duration) < 180,
                 "video.duration_seconds must be greater than 0 and under 180 seconds")
    url = video.get("url")
    parsed = urlparse(url) if _is_text(url) else None
    host = (parsed.hostname or "").lower() if parsed else ""
    checks.check("video.url",
                 bool(parsed) and parsed.scheme in ("http", "https")
                 and (host == "youtu.be" or host.endswith("youtube.com"))
                 and not _url_is_placeholder(url),
                 "video.url must be an accessible YouTube URL")
    checks.check("video.visibility", video.get("visibility") in ("public", "unlisted"),
                 "video.visibility must be public or unlisted; private is not acceptable")
    checks.check("video.observed_available", video.get("observed_available") is True,
                 "video.observed_available must be true")
    checks.check("video.observed_at", _is_text(video.get("observed_at")),
                 "video.observed_at must be recorded")
    checks.check("video.contains_live_twitch", video.get("contains_live_twitch") is True,
                 "video.contains_live_twitch must be true for observed live operation")
    checks.check("video.contains_codex_evidence",
                 video.get("contains_codex_evidence") is True,
                 "video.contains_codex_evidence must be true")

    repository = _as_dict(record.get("repository"))
    repo_url = repository.get("url")
    parsed_repo = urlparse(repo_url) if _is_text(repo_url) else None
    checks.check("repository.url",
                 bool(parsed_repo) and parsed_repo.scheme in ("http", "https")
                 and bool(parsed_repo.hostname) and not _url_is_placeholder(repo_url),
                 "repository.url must be a judge-accessible repository URL, not a placeholder")
    checks.check("repository.commit", _is_sha1(repository.get("commit")),
                 "repository.commit must be a 40-character hex SHA-1")
    if _is_sha1(candidate.get("final_head")):
        checks.check("repository.commit_matches_candidate",
                     repository.get("commit") == candidate.get("final_head"),
                     "repository.commit must match candidate.final_head")
    checks.check("repository.clean_checkout_verified",
                 repository.get("clean_checkout_verified") is True,
                 "repository.clean_checkout_verified must be true")
    checks.check("repository.setup_verified", repository.get("setup_verified") is True,
                 "repository.setup_verified must be true")
    checks.check("repository.observed_accessible",
                 repository.get("observed_accessible") is True,
                 "repository.observed_accessible must be true")
    checks.check("repository.observed_at", _is_text(repository.get("observed_at")),
                 "repository.observed_at must be recorded")

    project = _as_dict(record.get("project"))
    _verify_file(checks, repo, "project.description",
                 project.get("description_path"), project.get("description_sha256"))
    _verify_file(checks, repo, "project.setup",
                 project.get("setup_path"), project.get("setup_sha256"))
    checks.check("project.codex_session_id",
                 _is_text(project.get("codex_session_id"))
                 and bool(_UUID_RE.fullmatch(project.get("codex_session_id", ""))),
                 "project.codex_session_id must be a recorded UUID, not invented")
    _verify_file(checks, repo, "project.licensing_checklist",
                 project.get("licensing_checklist_path"),
                 project.get("licensing_checklist_sha256"))
    checks.check("project.audio_licensed", project.get("audio_licensed") is True,
                 "project.audio_licensed must be true for all final video audio")

    package = _as_dict(record.get("package"))
    manifest_path = package.get("manifest_path")
    checks.check("package.manifest_path", _is_text(manifest_path),
                 "package.manifest_path must be recorded")
    if _is_text(manifest_path):
        checker = package_checker or _default_package_checker
        try:
            package_result = checker(repo, manifest_path)
        except Exception as exc:  # noqa: BLE001 - fail closed on any checker error
            checks.check("package.check", False, f"package.check failed: {exc}")
        else:
            checks.check("package.check",
                         package_result.get("status") == "ok",
                         "package.check did not verify the manifest")
            checks.check("package.artifact_set_complete",
                         package_result.get("complete") is True,
                         "package.artifact_set is incomplete: pending integration artifacts are not packaged")

    hygiene = _as_dict(record.get("hygiene"))
    checks.check("hygiene.cleanup_performed", hygiene.get("cleanup_performed") is True,
                 "hygiene.cleanup_performed must be true")
    checks.check("hygiene.secret_scan_passed", hygiene.get("secret_scan_passed") is True,
                 "hygiene.secret_scan_passed must be true")
    checks.check("hygiene.raw_chat_absent", hygiene.get("raw_chat_absent") is True,
                 "hygiene.raw_chat_absent must be true")
    sealed_roots = hygiene.get("sealed_roots")
    if type(sealed_roots) is not list or not sealed_roots:
        checks.check("hygiene.sealed_roots", False,
                     "hygiene.sealed_roots must list at least one sealed root")
    else:
        for index, sealed in enumerate(sealed_roots):
            sealed = _as_dict(sealed)
            prefix = f"hygiene.sealed_roots[{index}]"
            checks.check(f"{prefix}.algorithm",
                         sealed.get("algorithm") == SEALED_ROOT_ALGORITHM,
                         f"{prefix}.algorithm must be {SEALED_ROOT_ALGORITHM}")
            checks.check(f"{prefix}.file_count",
                         type(sealed.get("file_count")) is int
                         and sealed.get("file_count") > 0,
                         f"{prefix}.file_count must be a positive integer")
            checks.check(f"{prefix}.tree_sha256",
                         _is_sha256(sealed.get("tree_sha256")),
                         f"{prefix}.tree_sha256 must be a SHA-256")
            sealed_path = _repo_path(repo, sealed.get("path"))
            if sealed_path is None or not sealed_path.is_dir():
                checks.check(f"{prefix}.path", False,
                             f"{prefix}.path must be a sealed directory inside the repository")
                continue
            files = [item for item in sealed_path.rglob("*") if item.is_file()]
            checks.check(f"{prefix}.file_count_matches",
                         len(files) == sealed.get("file_count"),
                         f"{prefix}.file_count does not match the sealed root")
            try:
                actual_tree = compute_tree_sha256(sealed_path)
            except OSError as exc:
                checks.check(f"{prefix}.tree_sha256_matches", False,
                             f"{prefix}.tree_sha256 could not be recomputed: {exc}")
            else:
                checks.check(f"{prefix}.tree_sha256_matches",
                             actual_tree == sealed.get("tree_sha256"),
                             f"{prefix}.tree_sha256 does not match the sealed root")

    review = _as_dict(record.get("review"))
    checks.check("review.review_packet_sha256",
                 _is_sha256(review.get("review_packet_sha256")),
                 "review.review_packet_sha256 must be a SHA-256")
    checks.check("review.reviewed_candidate_diff_sha256",
                 _is_sha256(review.get("reviewed_candidate_diff_sha256"))
                 and review.get("reviewed_candidate_diff_sha256")
                 == candidate.get("tracked_diff_sha256"),
                 "review.reviewed_candidate_diff_sha256 is stale or missing")
    try:
        from coordination.review_route import evaluate_review_route

        route_result = evaluate_review_route(review)
    except Exception as exc:  # noqa: BLE001 - malformed review evidence fails closed
        checks.check("review.route", False, f"review.route is invalid: {exc}")
    else:
        checks.check("review.route", route_result.get("review_ready") is True,
                     "review.route failed: "
                     + ", ".join(route_result.get("failure_reasons", [])))

    checks.check("record_hygiene.no_forbidden_material",
                 not _contains_forbidden_material(record),
                 "record contains raw chat, token or secret-shaped material")

    publication = _as_dict(record.get("publication"))
    submission_ready = not checks.reasons
    return {
        "schema_version": 1,
        "submission_ready": submission_ready,
        "reasons": list(checks.reasons),
        "checks": dict(checks.results),
        "predicate_count": len(checks.results),
        "passed_predicate_count": sum(1 for passed in checks.results.values() if passed),
        "declared_submission_ready": record.get("declared_submission_ready"),
        "publication": publication,
        "evaluated_head": git_state.get("head") if git_state else None,
    }


def evaluate_path(record_path: Any, repo: Path = ROOT,
                  git_state: Optional[Dict[str, str]] = None,
                  package_checker: Optional[Callable[[Path, Any], Dict[str, Any]]] = None,
                  now: Optional[datetime] = None) -> Dict[str, Any]:
    repo = Path(repo)
    path = Path(record_path)
    if not path.is_absolute():
        path = repo / path
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return {
            "schema_version": 1,
            "submission_ready": False,
            "reasons": [f"readiness record could not be loaded: {exc}"],
            "checks": {"record.loaded": False},
            "predicate_count": 1,
            "passed_predicate_count": 0,
            "declared_submission_ready": None,
            "publication": {},
            "evaluated_head": git_state.get("head") if git_state else None,
        }
    return evaluate_record(record, repo=repo, git_state=git_state,
                            package_checker=package_checker, now=now)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline submission-readiness verifier. No network, service "
                    "or gameplay execution.",
    )
    parser.add_argument("record", nargs="?", default=DEFAULT_RECORD,
                        help="readiness record path (default: %(default)s)")
    parser.add_argument("--repo", default=str(ROOT),
                        help="repository root (default: detected project root)")
    parser.add_argument("--require-ready", action="store_true",
                        help="exit 1 unless every predicate passes")
    parser.add_argument("--no-package-check", action="store_true",
                        help="diagnostic only: skip package verification")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    package_checker = None
    if args.no_package_check:
        package_checker = lambda _repo, _path: {
            "status": "skipped", "complete": False, "verified": 0,
        }
    result = evaluate_path(args.record, repo=repo,
                           git_state=local_git_state(repo),
                           package_checker=package_checker)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_ready and not result["submission_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
