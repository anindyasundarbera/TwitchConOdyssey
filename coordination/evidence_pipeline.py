"""SDC evidence pipeline primitives: exclusive run roots, derived coverage, review verification & readiness."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from .content_cache import bytes_hash, canonical_hash, detached, require_hash, validate_json
from .state_transport import _validate_delta
from .deterministic_kernel import (
    validate_review_authorship,
    validate_run_immutability,
    validate_citation_hashes,
    validate_source_bytes,
    validate_evidence_coverage,
    validate_readiness_separation,
)

PRESERVED_REJECTED_RUN_ID = "full-game-20261101T102226Z-a8e33043"
PRESERVED_REJECTED_TREE_SHA256 = "411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d"
AUTHORIZATION_TOKEN = "AUTHORIZE_COMPLETE_GAME_SIMULATION=true"

_UTC_COMPACT_RE = re.compile(r"\d{8}T\d{6}Z\Z")
_RUN_ID_RE = re.compile(r"full-game-\d{8}T\d{6}Z-[0-9a-zA-Z]{8}\Z")
_BOUND_HASH_LINE_RE = re.compile(r"^\s*-\s*`([^`]+)`:\s*`([0-9a-fA-F]{64})`\s*$")
_VERDICT_PATTERNS = (
    re.compile(r"(?im)^\s*-\s*\*\*Verdict:\*\*\s*`?(READY|REVISE)`?\s*$"),
    re.compile(r"(?im)^\s*\*\*Verdict:\*\*\s*`?(READY|REVISE)`?\s*$"),
    re.compile(r"(?im)^\s*Verdict:\s*`?(READY|REVISE)`?\s*$"),
)

_PROTECTED_REVIEW_FILENAMES = frozenset({
    "INDEPENDENT-REVIEW.md",
    "INDEPENDENT-REVIEW.json",
    "REVIEW-INVOCATION.json",
    "MODEL-USAGE.json",
})

_POST_REVIEW_FILENAMES = _PROTECTED_REVIEW_FILENAMES | {
    "DEVELOPMENT-READINESS.json", "README.md", "RUN-MANIFEST.json",
}

PIPELINE_INVARIANTS = [
    {"id": "INV-REVIEW-AUTHORSHIP", "name": "review-artifact authorship"},
    {"id": "INV-RUN-IMMUTABILITY", "name": "run-root non-reuse/re-seal"},
    {"id": "INV-CITATION-HASHES", "name": "cited-artifact hash existence"},
    {"id": "INV-SOURCE-BYTES", "name": "seal-time source-byte match"},
    {"id": "INV-EVIDENCE-COVERAGE", "name": "coverage as a function of evidence"},
    {"id": "INV-READINESS-SEPARATION", "name": "ready/submission-ready separation"},
]

# Pipeline/provenance checks are validators, never invented gameplay scenarios.
AUDIT_VALIDATORS = {
    "AUDIT-01": ["independent_review_verified", "independent_review_uses_configured_gate"],
    "AUDIT-02": ["frozen_requirements_valid"],
    "AUDIT-03": ["SCEN-E2E-05", "SCEN-AUD-06"],
    "AUDIT-04": ["feature_coverage_honestly_derived"],
    "AUDIT-05": ["all_traces_substantive"],
    "AUDIT-06": ["candidate_plan_hash_bound_and_matches"],
    "AUDIT-07": ["all_pipeline_invariants_passed"],
    "AUDIT-08": ["corpus_hash_valid"],
    "AUDIT-09": ["pre_review_evidence_complete"],
    "AUDIT-10": ["independent_review_uses_configured_gate", "review_verdict_is_ready"],
    "AUDIT-11": ["all_scenarios_passed", "frozen_requirements_valid"],
    "AUDIT-12": ["all_s0_s1_blocking_s2_issues_closed"],
    "AUDIT-13": ["frozen_requirements_valid", "all_scenarios_passed"],
    "AUDIT-14": ["all_pipeline_invariants_passed"],
    "AUDIT-15": ["independent_review_verified"],
    "AUDIT-16": ["historical_review_unverified"],
    "AUDIT-17": ["frozen_requirements_valid"],
    "AUDIT-18": ["pre_review_evidence_complete"],
    "AUDIT-19": ["generated_stage_metadata_valid"],
}
AUDIT_SEVERITIES = {
    **{f"AUDIT-{n:02}": "S1" for n in (3, 4, 5, 6, 7, 11, 12, 13)},
    **{f"AUDIT-{n:02}": "S0" for n in (1, 2, 10)},
    **{f"AUDIT-{n:02}": "S2" for n in (8, 9, 14, 15, 18)},
    **{f"AUDIT-{n:02}": "S3" for n in (16, 17, 19)},
}

_DEFAULT_PARTIAL_SUB_CLAIMS: Dict[str, List[Dict[str, str]]] = {
    "FEAT-12-BULLET-TIME-PRESENTATION": [
        {
            "claim_id": "state_machine_and_tick_progression",
            "required_evidence_kind": "deterministic_state_and_commands",
            "description": "Bullet-time state flag and authoritative 20 Hz tick progression without deadline extension",
        },
        {
            "claim_id": "visual_interpolation_overlay_capture",
            "required_evidence_kind": "visual_interpolation_render_capture",
            "description": "Browser Canvas 2D visual slow-motion interpolation and overlay rendering",
        },
    ],
    "FEAT-13-ADAPTIVE-AUDIO": [
        {
            "claim_id": "audio_state_machine_and_telemetry_cues",
            "required_evidence_kind": "deterministic_state_and_commands",
            "description": "Discrete adaptive audio state transitions and telemetry cue priority on engine events",
        },
        {
            "claim_id": "acoustic_output_and_voiceover_intelligibility",
            "required_evidence_kind": "acoustic_output_and_voiceover_capture",
            "description": "Synthesized Web Audio acoustic output, voiceover intelligibility, and mute/accessibility capture",
        },
    ],
    "FEAT-15-PUBLIC-DEMO-TIMELINE": [
        {
            "claim_id": "demo_timeline_state_and_claim_schema",
            "required_evidence_kind": "deterministic_state_and_commands",
            "description": "Timed scenario state execution, fixture labeling, and truthful claim provenance schema",
        },
        {
            "claim_id": "rendered_three_minute_video_and_live_session",
            "required_evidence_kind": "rendered_video_and_live_twitch_session",
            "description": "Rendered under-three-minute public demo video capture and live Twitch session observation",
        },
    ],
}


def file_sha256(path: Path) -> str:
    """Compute lowercase SHA-256 hex digest of a file on disk."""
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest()


def compute_tree_sha256(root_dir: Path) -> str:
    """Compute aggregate sorted tree SHA-256 over `<rel_path>:<sha256>\\n` lines."""
    root = Path(root_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Directory does not exist: {root}")
    lines: List[str] = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            lines.append(f"{rel}:{file_sha256(p)}\n")
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def derive_run_id(profile_sha256: str, utc_timestamp: Optional[str] = None) -> str:
    """Construct `full-game-<YYYYMMDDTHHMMSSZ>-<profile_first8>` and reject preserved run ID."""
    require_hash(profile_sha256)
    if utc_timestamp is None:
        utc_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    elif type(utc_timestamp) is not str or not _UTC_COMPACT_RE.fullmatch(utc_timestamp):
        raise ValueError("utc_timestamp must match YYYYMMDDTHHMMSSZ")
    run_id = f"full-game-{utc_timestamp}-{profile_sha256[:8]}"
    if run_id == PRESERVED_REJECTED_RUN_ID:
        raise ValueError(f"Derived run_id collides with preserved rejected run: {run_id}")
    return run_id


def create_immutable_run_root(base_dir: Path, run_id: str, authorization_token: str) -> Path:
    """Create an exclusive run directory and required subdirectories (`exist_ok=False`)."""
    if authorization_token != AUTHORIZATION_TOKEN:
        raise PermissionError(
            f"Explicit simulation authorization required ({AUTHORIZATION_TOKEN})"
        )
    if type(run_id) is not str or not run_id.strip():
        raise ValueError("run_id must be a non-empty string")
    if run_id == PRESERVED_REJECTED_RUN_ID:
        raise ValueError(f"Cannot reuse or overwrite preserved rejected run_id: {run_id}")
    if "/" in run_id or "\\" in run_id or run_id in (".", ".."):
        raise ValueError(f"Invalid run_id path component: {run_id}")
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError(
            f"run_id must match full-game-<YYYYMMDDTHHMMSSZ>-<8chars>: {run_id}"
        )

    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / run_id
    if run_dir.exists():
        raise FileExistsError(f"Immutable run root already exists: {run_dir}")
    run_dir.mkdir(parents=False, exist_ok=False)
    for subdir in ("commands", "traces", "state-hashes", "results"):
        (run_dir / subdir).mkdir(parents=False, exist_ok=False)
    return run_dir


allocate_immutable_run_root = create_immutable_run_root


def _check_exclusive_write_permission(
    path: Path,
    *,
    allow_external_review: bool = False,
    forbid_synthetic_review: bool = True,
) -> Path:
    target = Path(path)
    # Compatibility flags never confer review authorship. The separate external
    # review boundary is the only supported writer of review provenance.
    if target.name in _PROTECTED_REVIEW_FILENAMES:
        raise PermissionError(f"Simulator may not author {target.name}")
    for parent in target.parents:
        if parent.name == PRESERVED_REJECTED_RUN_ID:
            raise PermissionError(
                f"Refusing to write inside preserved rejected run directory: {target}"
            )
    return target


def write_exclusive_bytes(
    path: Path,
    raw: bytes,
    *,
    allow_external_review: bool = False,
    forbid_synthetic_review: bool = True,
) -> str:
    """Write bytes exclusively with `open(path, 'xb')` and return SHA-256 hex digest."""
    if type(raw) is not bytes:
        raise ValueError("write_exclusive_bytes requires bytes")
    target = _check_exclusive_write_permission(
        path,
        allow_external_review=allow_external_review,
        forbid_synthetic_review=forbid_synthetic_review,
    )
    with open(target, "xb") as handle:
        handle.write(raw)
    return bytes_hash(raw)


def write_exclusive_text(
    path: Path,
    text: str,
    *,
    allow_external_review: bool = False,
    forbid_synthetic_review: bool = True,
) -> str:
    """Write UTF-8 text exclusively with `open(path, 'xb')` and return SHA-256 hex digest."""
    if type(text) is not str:
        raise ValueError("write_exclusive_text requires str")
    return write_exclusive_bytes(
        path,
        text.encode("utf-8"),
        allow_external_review=allow_external_review,
        forbid_synthetic_review=forbid_synthetic_review,
    )


def write_exclusive_json(
    path: Path,
    data: Any,
    *,
    allow_external_review: bool = False,
    forbid_synthetic_review: bool = True,
    indent: int = 2,
) -> str:
    """Validate and write JSON data exclusively with `open(path, 'xb')`."""
    validate_json(data)
    text = json.dumps(data, indent=indent, sort_keys=False, ensure_ascii=False) + "\n"
    return write_exclusive_text(
        path,
        text,
        allow_external_review=allow_external_review,
        forbid_synthetic_review=forbid_synthetic_review,
    )


write_immutable_json = write_exclusive_json


def verify_scenario_trace_integrity(
    scenario_id: str,
    run_dir: Path,
    expected_contract_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify command and trace artifacts exist, are non-placeholder, and carry valid state_diff records."""
    if type(scenario_id) is not str or not scenario_id.strip():
        raise ValueError("scenario_id must be a non-empty string")
    if expected_contract_hash is not None:
        require_hash(expected_contract_hash)

    root = Path(run_dir)
    cmd_path = root / "commands" / f"{scenario_id}.json"
    trace_path = root / "traces" / f"{scenario_id}.jsonl"
    if not cmd_path.is_file():
        raise FileNotFoundError(f"Missing scenario command file: {cmd_path}")
    if not trace_path.is_file():
        raise FileNotFoundError(f"Missing scenario trace file: {trace_path}")

    cmd_raw = cmd_path.read_text(encoding="utf-8").strip()
    trace_raw = trace_path.read_text(encoding="utf-8").strip()
    if not cmd_raw:
        raise ValueError(f"Empty command file for {scenario_id}")
    if not trace_raw:
        raise ValueError(f"Empty trace file for {scenario_id}")

    try:
        cmd_data = json.loads(cmd_raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {cmd_path}") from exc

    # Reject placeholder list/dict formats from defective baseline (`AUDIT-05`)
    if type(cmd_data) is list:
        if (
            len(cmd_data) == 1
            and type(cmd_data[0]) is dict
            and set(cmd_data[0].keys()) <= {"scenario_id", "execution_mode"}
        ):
            raise ValueError(f"Placeholder command stream detected for {scenario_id}")
        raise ValueError(
            f"Command file for {scenario_id} must be a canonical envelope object binding contract_hash"
        )
    if type(cmd_data) is not dict:
        raise ValueError(f"Command file for {scenario_id} must be a JSON object")
    if set(cmd_data.keys()) <= {"scenario_id", "execution_mode"}:
        raise ValueError(f"Placeholder command object detected for {scenario_id}")
    if cmd_data.get("scenario_id") != scenario_id:
        raise ValueError(f"Command file scenario_id mismatch for {scenario_id}")

    contract_hash = require_hash(cmd_data.get("contract_hash"))
    if expected_contract_hash is not None and contract_hash != expected_contract_hash:
        raise ValueError(
            f"Command file contract_hash mismatch for {scenario_id}: "
            f"{contract_hash} != {expected_contract_hash}"
        )
    initial_state_hash = require_hash(cmd_data.get("initial_state_hash"))
    final_state_hash = (
        require_hash(cmd_data["final_state_hash"])
        if "final_state_hash" in cmd_data and cmd_data["final_state_hash"] is not None
        else None
    )
    commands_list = cmd_data.get("commands")
    if type(commands_list) is not list:
        raise ValueError(f"Command file for {scenario_id} missing 'commands' list")
    for entry in commands_list:
        if type(entry) is not dict or "cmd" not in entry or "status" not in entry:
            raise ValueError(f"Malformed command log entry in {scenario_id}")

    trace_lines = [line for line in trace_raw.splitlines() if line.strip()]
    if not trace_lines:
        raise ValueError(f"No trace records in {trace_path}")

    deltas_validated = 0
    previous_result_hash: Optional[str] = None
    last_state_hash: Optional[str] = None
    for idx, line in enumerate(trace_lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at line {idx + 1} in {trace_path}") from exc
        if type(record) is not dict:
            raise ValueError(f"Trace record at line {idx + 1} in {trace_path} must be an object")
        if set(record.keys()) <= {"scenario_id", "final_status", "final_tick", "state_hash"}:
            raise ValueError(f"Summary-only placeholder trace detected for {scenario_id}")
        delta = record.get("delta")
        if type(delta) is not dict:
            raise ValueError(
                f"Trace record at line {idx + 1} for {scenario_id} missing substantive 'delta'"
            )
        validated_delta = _validate_delta(delta)
        state_hash = require_hash(record.get("state_hash"))
        if validated_delta["result_hash"] != state_hash:
            raise ValueError(
                f"Trace record result_hash != state_hash at line {idx + 1} for {scenario_id}"
            )
        if idx == 0 and validated_delta["base_hash"] != initial_state_hash:
            raise ValueError(
                f"First trace delta base_hash does not match initial_state_hash for {scenario_id}"
            )
        if previous_result_hash is not None and validated_delta["base_hash"] != previous_result_hash:
            raise ValueError(
                f"Broken state_diff hash chain at line {idx + 1} for {scenario_id}: "
                f"{validated_delta['base_hash']} != {previous_result_hash}"
            )
        previous_result_hash = validated_delta["result_hash"]
        last_state_hash = state_hash
        deltas_validated += 1

    if final_state_hash is not None and last_state_hash != final_state_hash:
        raise ValueError(
            f"Final trace state_hash {last_state_hash} != command final_state_hash {final_state_hash}"
        )

    return {
        "scenario_id": scenario_id,
        "contract_hash": contract_hash,
        "initial_state_hash": initial_state_hash,
        "final_state_hash": last_state_hash,
        "commands_count": len(commands_list),
        "trace_records_count": deltas_validated,
        "commands_sha256": file_sha256(cmd_path),
        "trace_sha256": file_sha256(trace_path),
        "substantive": True,
    }


verify_scenario_trace_Integrity = verify_scenario_trace_integrity
verify_scenario_artifacts = verify_scenario_trace_integrity


def _capability_observed(
    required_kind: str,
    *,
    render_observed: bool,
    audio_observed: bool,
    live_service_observed: bool,
) -> bool:
    if required_kind == "deterministic_state_and_commands":
        return True
    if required_kind in (
        "render_capture_and_mobile_viewport",
        "visual_interpolation_render_capture",
    ):
        return bool(render_observed)
    if required_kind == "acoustic_output_and_voiceover_capture":
        return bool(audio_observed)
    if required_kind == "rendered_video_and_live_twitch_session":
        return bool(render_observed and live_service_observed)
    return False


def derive_feature_statuses(
    feature_specs: List[Dict[str, Any]],
    scenario_results: List[Dict[str, Any]],
    *,
    render_observed: bool = False,
    audio_observed: bool = False,
    live_service_observed: bool = False,
    total_invariants: int = 18,
    passed_invariants: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Mechanically derive FEATURE-INVENTORY.json and COVERAGE.json from scenario evidence."""
    if type(feature_specs) is not list or not feature_specs:
        raise ValueError("feature_specs must be a non-empty list")
    if type(scenario_results) is not list:
        raise ValueError("scenario_results must be a list")

    derived_inventory: List[Dict[str, Any]] = []
    fully_observed_count = 0
    partially_observed_state_only_count = 0
    state_contract_covered_count = 0
    not_observed_count = 0
    failed_feature_count = 0

    for spec in feature_specs:
        if type(spec) is not dict or "feature_id" not in spec:
            raise ValueError("Each feature spec must be a dict with 'feature_id'")
        entry = detached(spec)
        fid = entry["feature_id"]

        exercising = [
            s for s in scenario_results
            if fid in s.get("features", s.get("features_exercised", []))
        ]
        passed_scens = [s["scenario_id"] for s in exercising if s.get("verdict") == "passed"]
        failed_scens = [s["scenario_id"] for s in exercising if s.get("verdict") != "passed"]
        state_passed = len(exercising) > 0 and len(failed_scens) == 0

        required_kind = entry.get("required_evidence_kind")
        if not required_kind:
            if fid == "FEAT-14-READABILITY-AND-HUD":
                required_kind = "render_capture_and_mobile_viewport"
            else:
                required_kind = "deterministic_state_and_commands"
        entry["required_evidence_kind"] = required_kind

        raw_sub_claims = entry.get("sub_claims")
        if raw_sub_claims is None and fid in _DEFAULT_PARTIAL_SUB_CLAIMS:
            raw_sub_claims = detached(_DEFAULT_PARTIAL_SUB_CLAIMS[fid])

        if required_kind != "deterministic_state_and_commands":
            cap_ok = _capability_observed(
                required_kind,
                render_observed=render_observed,
                audio_observed=audio_observed,
                live_service_observed=live_service_observed,
            )
            if not cap_ok:
                entry["status"] = "not_observed"
                entry["coverage_state"] = "not_observed"
                entry["unobserved_reason"] = (
                    "No browser/mobile render capture or compressed-video readability "
                    "observation in headless deterministic simulation"
                )
                entry["exercised_by_scenarios"] = passed_scens
                not_observed_count += 1
                derived_inventory.append(entry)
                continue

        if raw_sub_claims:
            evaluated_sub_claims = []
            all_sub_observed = True
            any_state_sub_passed = False
            for sub in raw_sub_claims:
                sub_copy = detached(sub)
                sub_kind = sub_copy.get("required_evidence_kind", "deterministic_state_and_commands")
                if sub_kind == "deterministic_state_and_commands":
                    if failed_scens:
                        sub_copy["status"] = "failed"
                        sub_copy["coverage_state"] = "failed"
                    elif state_passed:
                        sub_copy["status"] = "passed"
                        sub_copy["coverage_state"] = "covered"
                        any_state_sub_passed = True
                    else:
                        sub_copy["status"] = "not_observed"
                        sub_copy["coverage_state"] = "not_observed"
                        all_sub_observed = False
                else:
                    sub_cap = _capability_observed(
                        sub_kind,
                        render_observed=render_observed,
                        audio_observed=audio_observed,
                        live_service_observed=live_service_observed,
                    )
                    if sub_cap and state_passed:
                        sub_copy["status"] = "passed"
                        sub_copy["coverage_state"] = "covered"
                    elif failed_scens:
                        sub_copy["status"] = "failed"
                        sub_copy["coverage_state"] = "failed"
                    else:
                        sub_copy["status"] = "not_observed"
                        sub_copy["coverage_state"] = "not_observed"
                        all_sub_observed = False
                evaluated_sub_claims.append(sub_copy)

            entry["sub_claims"] = evaluated_sub_claims
            entry["exercised_by_scenarios"] = passed_scens
            if failed_scens:
                entry["status"] = "failed"
                entry["coverage_state"] = "failed"
                failed_feature_count += 1
            elif any_state_sub_passed and all_sub_observed:
                entry["status"] = "passed"
                entry["coverage_state"] = "covered"
                fully_observed_count += 1
                state_contract_covered_count += 1
            elif any_state_sub_passed:
                entry["status"] = "passed"
                entry["coverage_state"] = "partially_observed_state_only"
                entry["state_contract_status"] = "passed"
                entry["unobserved_sub_claims"] = [
                    sc["claim_id"] for sc in evaluated_sub_claims if sc["status"] == "not_observed"
                ]
                partially_observed_state_only_count += 1
                state_contract_covered_count += 1
            else:
                entry["status"] = "not_observed"
                entry["coverage_state"] = "not_observed"
                not_observed_count += 1
            derived_inventory.append(entry)
            continue

        entry["exercised_by_scenarios"] = passed_scens
        if failed_scens:
            entry["status"] = "failed"
            entry["coverage_state"] = "failed"
            failed_feature_count += 1
        elif state_passed:
            entry["status"] = "passed"
            entry["coverage_state"] = "covered"
            fully_observed_count += 1
            state_contract_covered_count += 1
        else:
            entry["status"] = "not_observed"
            entry["coverage_state"] = "not_observed"
            entry["unobserved_reason"] = "Zero scenarios exercised this feature"
            not_observed_count += 1
        derived_inventory.append(entry)

    passed_scenarios_count = sum(1 for s in scenario_results if s.get("verdict") == "passed")
    failed_scenarios_count = sum(1 for s in scenario_results if s.get("verdict") != "passed")
    if passed_invariants is None:
        inv_set = set()
        for s in scenario_results:
            if s.get("verdict") == "passed":
                for inv_id in s.get("invariants_passed", []):
                    inv_set.add(inv_id)
        passed_invariants = len(inv_set)

    coverage_summary = {
        "total_active_features": len(derived_inventory),
        "covered_features": fully_observed_count,
        "fully_observed_features": fully_observed_count,
        "partially_observed_state_only_features": partially_observed_state_only_count,
        "state_contract_covered_features": state_contract_covered_count,
        "not_observed_features": not_observed_count,
        "failed_features": failed_feature_count,
        "environment_capabilities": {
            "render_observed": bool(render_observed),
            "audio_observed": bool(audio_observed),
            "live_service_observed": bool(live_service_observed),
        },
        "total_scenarios": len(scenario_results),
        "passed_scenarios": passed_scenarios_count,
        "failed_scenarios": failed_scenarios_count,
        "total_invariants": total_invariants,
        "passed_invariants": passed_invariants,
    }
    return detached(derived_inventory), detached(coverage_summary)


def _safe_artifact(root: Path, rel: str) -> Path:
    if type(rel) is not str or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ValueError(f"Unsafe artifact path: {rel!r}")
    target = root / rel
    if any(p.is_symlink() for p in (target, *target.parents)):
        raise ValueError(f"Symlink artifact is forbidden: {rel}")
    if not target.is_file():
        raise ValueError(f"Missing artifact: {rel}")
    return target


def _raw_evidence_hashes(root: Path) -> Dict[str, str]:
    hashes = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlink evidence is forbidden: {path}")
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            if rel not in _POST_REVIEW_FILENAMES | {"REVIEW-PACKET.md", "REVIEW-EVIDENCE.json"}:
                hashes[rel] = file_sha256(path)
    return hashes


def verify_pre_review_inventory(run_dir: Path) -> Dict[str, Any]:
    """Recompute the complete pre-review surface; no path may be added or removed."""
    root = Path(run_dir)
    inventory = json.loads(_safe_artifact(root, "REVIEW-EVIDENCE.json").read_text())
    if inventory.get("schema_version") != 2 or inventory.get("run_id") != root.name:
        raise ValueError("Invalid pre-review inventory identity")
    actual = _raw_evidence_hashes(root)
    if not actual or inventory.get("artifact_hashes") != actual:
        raise ValueError("Missing, unexpected or mutated pre-review evidence")
    if inventory.get("root_sha256") != canonical_hash(actual):
        raise ValueError("Pre-review inventory root mismatch")
    return inventory


def verify_source_bindings(run_dir: Path) -> bool:
    root = Path(__file__).resolve().parents[1]
    bindings = json.loads(_safe_artifact(Path(run_dir), "SOURCE-BINDINGS.json").read_text())
    if type(bindings) is not dict or not bindings:
        raise ValueError("Missing source bindings")
    for rel, record in bindings.items():
        path = _safe_artifact(root, rel)
        if record.get("path") != rel or file_sha256(path) != require_hash(record.get("sha256")):
            raise ValueError(f"Source-byte drift: {rel}")
    return True


def prepare_pending_review_packet(
    run_dir: Path,
    run_id: str,
    artifact_rel_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Write REVIEW-PACKET.md binding pre-review artifacts only (never DEVELOPMENT-READINESS.json)."""
    root = Path(run_dir)
    if artifact_rel_paths is not None and set(artifact_rel_paths) & _POST_REVIEW_FILENAMES:
        raise ValueError("REVIEW-PACKET.md must not pre-hash post-review artifacts")
    if any((root / name).exists() for name in _POST_REVIEW_FILENAMES):
        raise ValueError("Review artifacts must be absent at the simulation boundary")
    evidence_hashes = _raw_evidence_hashes(root)
    if artifact_rel_paths is not None and set(artifact_rel_paths) != set(evidence_hashes):
        raise ValueError("Review packet must cover the complete pre-review inventory")
    inventory = {"schema_version": 2, "run_id": run_id,
                 "artifact_hashes": evidence_hashes,
                 "root_sha256": canonical_hash(evidence_hashes)}
    write_exclusive_json(root / "REVIEW-EVIDENCE.json", inventory)
    artifact_rel_paths = ["REVIEW-EVIDENCE.json"]

    bound_hashes: Dict[str, str] = {}
    lines = [
        f"# Independent Review Packet — Run {run_id}",
        "",
        "### Bound Artifact Hashes:",
    ]
    for rel in artifact_rel_paths:
        target = _safe_artifact(root, rel)
        digest = file_sha256(target)
        bound_hashes[rel] = digest
        lines.append(f"- `{rel}`: `{digest}`")

    lines.extend([
        "",
        "### Request:",
        (
            "Review inventory completeness, scenario/oracle adequacy, "
            "raw-evidence-to-conclusion traceability, plan vs harness classification, "
            "replay determinism, and credibility. Emit verdict exactly READY or REVISE."
        ),
        "",
    ])
    packet_text = "\n".join(lines)
    packet_sha256 = write_exclusive_text(root / "REVIEW-PACKET.md", packet_text)
    return {
        "run_id": run_id,
        "review_packet_path": "REVIEW-PACKET.md",
        "review_packet_sha256": packet_sha256,
        "bound_artifact_hashes": bound_hashes,
        "packet_characters": len(packet_text),
    }


def _extract_verdict_from_markdown(text: str) -> str:
    for pattern in _VERDICT_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            verdict = matches[0].upper()
            if verdict in ("READY", "REVISE"):
                return verdict
    raise ValueError("INDEPENDENT-REVIEW.md does not contain an explicit READY or REVISE verdict")


def verify_independent_review_artifact(run_dir: Path) -> Dict[str, Any]:
    """Verify REVIEW-PACKET.md, INDEPENDENT-REVIEW.md, and REVIEW-INVOCATION.json anti-forgery bindings."""
    root = Path(run_dir)
    packet_path = root / "REVIEW-PACKET.md"
    review_md_path = root / "INDEPENDENT-REVIEW.md"
    invocation_path = root / "REVIEW-INVOCATION.json"
    review_json_path = root / "INDEPENDENT-REVIEW.json"

    if not packet_path.is_file():
        raise ValueError(f"Missing REVIEW-PACKET.md in {root}")
    if not review_md_path.is_file():
        raise ValueError(f"Missing INDEPENDENT-REVIEW.md in {root}")
    if not invocation_path.is_file():
        raise ValueError(
            f"Missing REVIEW-INVOCATION.json in {root}; independent review is unverified or synthetic"
        )

    packet_text = packet_path.read_text(encoding="utf-8")
    bound_artifacts: Dict[str, str] = {}
    for line in packet_text.splitlines():
        match = _BOUND_HASH_LINE_RE.match(line)
        if match:
            rel_path, digest = match.group(1), match.group(2).lower()
            require_hash(digest)
            if rel_path in bound_artifacts:
                raise ValueError("Duplicate packet binding")
            bound_artifacts[rel_path] = digest

    if not bound_artifacts:
        raise ValueError("REVIEW-PACKET.md contains no bound artifact hashes")
    if "DEVELOPMENT-READINESS.json" in bound_artifacts:
        raise ValueError(
            "AUDIT-09 violation: REVIEW-PACKET.md pre-hashed DEVELOPMENT-READINESS.json before review"
        )
    if "RUN-MANIFEST.json" in bound_artifacts:
        raise ValueError("REVIEW-PACKET.md must not pre-hash RUN-MANIFEST.json")
    if (root / "READINESS-CONTRACT.json").exists() and set(bound_artifacts) != {"REVIEW-EVIDENCE.json"}:
        raise ValueError("Current review requires the complete pre-review inventory")

    for rel_path, expected_digest in bound_artifacts.items():
        artifact_file = _safe_artifact(root, rel_path)
        actual_digest = file_sha256(artifact_file)
        if actual_digest != expected_digest:
            raise ValueError(
                f"Bound artifact {rel_path} hash mismatch against REVIEW-PACKET.md: "
                f"{actual_digest} != {expected_digest}"
            )

    try:
        invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON in REVIEW-INVOCATION.json") from exc
    if type(invocation) is not dict:
        raise ValueError("REVIEW-INVOCATION.json must be a JSON object")

    if "REVIEW-EVIDENCE.json" in bound_artifacts:
        inventory = verify_pre_review_inventory(root)
        if (invocation.get("schema_version") != 2
                or invocation.get("authored_by") != "coordination.review_boundary"
                or invocation.get("run_id") != root.name
                or invocation.get("evidence_root_sha256") != inventory["root_sha256"]
                or invocation.get("evidence_origin") != "independent_subagent_review"):
            raise ValueError("Review provenance was not produced by the external review boundary")
        for key in ("reviewer_model", "reviewer_effort", "reviewer_provider", "configured_model",
                    "configured_effort", "configured_provider", "gate_binding"):
            if type(invocation.get(key)) is not str or not invocation[key].strip():
                raise ValueError(f"Missing review provenance: {key}")
        if any(type(invocation.get(k)) is not bool for k in (
                "configured_model_available", "configured_gate_satisfied")):
            raise ValueError("Malformed configured-review predicates")
        usage = json.loads(_safe_artifact(root, "MODEL-USAGE.json").read_text())
        if usage != invocation.get("model_usage"):
            raise ValueError("Review model-usage provenance mismatch")
    elif invocation.get("schema_version") == 2:
        raise ValueError("Schema-2 review requires complete inventory binding")

    evidence_origin = invocation.get("evidence_origin")
    if evidence_origin in (None, "", "synthetic_generator", "simulator", "self_authored"):
        raise ValueError(f"Rejected synthetic or invalid review evidence_origin: {evidence_origin!r}")

    conv_id = invocation.get("subagent_conversation_id") or invocation.get("reviewer_conversation_id")
    if type(conv_id) is not str or not conv_id.strip():
        raise ValueError("REVIEW-INVOCATION.json must bind a non-empty subagent_conversation_id")

    require_hash(invocation.get("packet_hash"))
    prompt_hash = invocation.get("prompt_sha256") or invocation.get("prompt_hash")
    require_hash(prompt_hash)

    packet_sha256 = file_sha256(packet_path)
    recorded_packet_sha256 = invocation.get("review_packet_sha256")
    if invocation.get("schema_version") == 2 and recorded_packet_sha256 is None:
        raise ValueError("External review must bind packet bytes")
    if recorded_packet_sha256 is not None:
        require_hash(recorded_packet_sha256)
        if recorded_packet_sha256 != packet_sha256:
            raise ValueError("REVIEW-INVOCATION.json review_packet_sha256 does not match REVIEW-PACKET.md")

    review_md_sha256 = file_sha256(review_md_path)
    output_hash = invocation.get("independent_review_sha256") or invocation.get("output_hash")
    require_hash(output_hash)
    if output_hash != review_md_sha256:
        raise ValueError(
            "REVIEW-INVOCATION.json output hash does not match INDEPENDENT-REVIEW.md bytes"
        )

    review_md_text = review_md_path.read_text(encoding="utf-8")
    md_verdict = _extract_verdict_from_markdown(review_md_text)

    inv_verdict = invocation.get("verdict")
    if inv_verdict not in ("READY", "REVISE"):
        raise ValueError(f"Invalid verdict in REVIEW-INVOCATION.json: {inv_verdict!r}")
    if inv_verdict != md_verdict:
        raise ValueError(
            f"Verdict mismatch between REVIEW-INVOCATION.json ({inv_verdict}) "
            f"and INDEPENDENT-REVIEW.md ({md_verdict})"
        )

    review_json_sha256: Optional[str] = None
    if invocation.get("schema_version") == 2 and not review_json_path.is_file():
        raise ValueError("External review requires INDEPENDENT-REVIEW.json")
    if review_json_path.is_file():
        try:
            review_json = json.loads(review_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON in INDEPENDENT-REVIEW.json") from exc
        if type(review_json) is not dict:
            raise ValueError("INDEPENDENT-REVIEW.json must be a JSON object")
        json_verdict = review_json.get("verdict")
        if json_verdict != md_verdict:
            raise ValueError(
                f"Verdict mismatch between INDEPENDENT-REVIEW.json ({json_verdict}) "
                f"and INDEPENDENT-REVIEW.md ({md_verdict})"
            )
        review_json_sha256 = file_sha256(review_json_path)
        if invocation.get("schema_version") == 2 and not invocation.get("independent_review_json_sha256"):
            raise ValueError("External review must bind its structured output")
        if "independent_review_json_sha256" in invocation and invocation["independent_review_json_sha256"] is not None:
            require_hash(invocation["independent_review_json_sha256"])
            if invocation["independent_review_json_sha256"] != review_json_sha256:
                raise ValueError("REVIEW-INVOCATION.json independent_review_json_sha256 mismatch")

    if invocation.get("schema_version") == 2:
        expected_usage = [{
            "agent_role": "Independent Evidence Reviewer",
            "model": invocation["reviewer_model"], "provider": invocation["reviewer_provider"],
            "reasoning_effort": invocation["reviewer_effort"],
            "configured_model": invocation["configured_model"],
            "configured_gate_satisfied": invocation["configured_gate_satisfied"],
            "subagent_conversation_id": conv_id, "evidence_origin": evidence_origin,
            "output_sha256": review_md_sha256, "verdict": md_verdict,
        }]
        if usage != expected_usage:
            raise ValueError("Invocation identity/output disagrees with model-usage evidence")

    return {
        "verified": True,
        "verdict": md_verdict,
        "evidence_origin": evidence_origin,
        "subagent_conversation_id": conv_id,
        "packet_hash": invocation["packet_hash"],
        "prompt_sha256": prompt_hash,
        "review_packet_sha256": packet_sha256,
        "independent_review_sha256": review_md_sha256,
        "independent_review_json_sha256": review_json_sha256,
        "bound_artifact_hashes": bound_artifacts,
    }


def compute_development_readiness(
    run_dir: Optional[Path] = None,
    *,
    candidate_plan_revision: Optional[int] = None,
    candidate_plan_hash: Optional[str] = None,
    expected_gameplan_sha256: Optional[str] = None,
    candidate_json_hash: Optional[str] = None,
    expected_gameplan_json_sha256: Optional[str] = None,
    blocking_issues_count: Optional[int] = None,
    unresolved_human_decisions: Optional[List[str]] = None,
    all_invariants_passed: Optional[bool] = None,
    all_scenarios_passed: Optional[bool] = None,
    golden_replay_verified: Optional[bool] = None,
    corpus_hash_valid: Optional[bool] = None,
    all_traces_substantive: Optional[bool] = None,
    feature_coverage_honestly_derived: Optional[bool] = None,
    review_verdict: Optional[str] = None,
    independent_review_verified: Optional[bool] = None,
    independent_review_is_configured_gate: Optional[bool] = None,
    gameplan_md_path: Optional[Path] = None,
    gameplan_json_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Evaluate frozen requirements against bytes; caller claims can only veto."""
    root = Path(run_dir) if run_dir is not None else None
    repo = Path(__file__).resolve().parents[1]
    errors = {}
    gates = {}
    data = {}

    def read(rel):
        if root is None:
            raise ValueError("Readiness requires a frozen run directory")
        return json.loads(_safe_artifact(root, rel).read_text(encoding="utf-8"))

    def check(name, predicate, veto=None):
        try:
            gates[name] = veto is not False and predicate() is True
        except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError) as exc:
            gates[name] = False
            errors[name] = str(exc)
        return gates[name]

    check("pre_review_evidence_complete", lambda: bool(verify_pre_review_inventory(root)))
    check("source_bytes_match", lambda: verify_source_bindings(root))

    def requirements():
        contract = read("READINESS-CONTRACT.json")
        bindings = read("SOURCE-BINDINGS.json")
        plan = json.loads(_safe_artifact(repo, "docs/planning/gameplan-v2.json").read_text())
        policy = json.loads(_safe_artifact(repo, "config/directive-policy.json").read_text())
        catalog = read("INVARIANT-CATALOG.json")
        matrix = read("SCENARIO-MATRIX.json")
        from .full_game_simulator import validate_scenario_contract
        if type(matrix) is not list or not matrix or type(catalog) is not list or not catalog:
            return False
        matrix = [validate_scenario_contract(c) for c in matrix]
        ids = [c["scenario_id"] for c in matrix]
        inv_ids = [c["id"] for c in catalog]
        revision = plan["revision"]["number"]
        if (contract["schema_version"] != 2
                or contract["candidate_plan_revision"] != revision
                or type(revision) is not int
                or contract["scenario_ids"] != ids or len(set(ids)) != len(ids)
                or contract["invariant_ids"] != inv_ids or len(set(inv_ids)) != len(inv_ids)
                or contract["scenario_matrix_sha256"] != file_sha256(root / "SCENARIO-MATRIX.json")
                or contract["invariant_catalog_sha256"] != file_sha256(root / "INVARIANT-CATALOG.json")
                or contract["source_bindings_sha256"] != file_sha256(root / "SOURCE-BINDINGS.json")
                or contract["unresolved_decisions"] != policy["unresolved_decisions"]
                or {c["id"] for c in catalog if c["kind"] == "pipeline"} != {c["id"] for c in PIPELINE_INVARIANTS}
                or any(not set(c["invariants_tested"]) <= set(inv_ids) for c in matrix)):
            return False
        if (any(c["kind"] not in ("scenario", "pipeline") for c in catalog)
                or {c["id"] for c in catalog if c["kind"] == "scenario"}
                != {i for c in matrix for i in c["invariants_tested"]}):
            return False
        freeze = read("MATRIX-FREEZE.json")
        if (freeze["scenario_matrix_sha256"] != contract["scenario_matrix_sha256"]
                or freeze["frozen_before_execution"] is not True
                or not freeze["frozen_at_utc"]):
            return False
        data.update(contract=contract, bindings=bindings, matrix=matrix, catalog=catalog,
                    revision=revision)
        return True

    check("frozen_requirements_valid", requirements)
    contract = data.get("contract", {})
    bindings = data.get("bindings", {})
    plan_hash = bindings.get("docs/planning/GAMEPLAN-v2.md", {}).get("sha256")
    json_hash = bindings.get("docs/planning/gameplan-v2.json", {}).get("sha256")
    check("candidate_plan_revision_matches_contract",
          lambda: bool(data) and (candidate_plan_revision is None or candidate_plan_revision == data["revision"]))
    check("candidate_plan_hash_bound_and_matches", lambda: (
        _is_valid_hash(plan_hash) and _is_valid_hash(json_hash)
        and plan_hash == file_sha256(Path(gameplan_md_path) if gameplan_md_path else repo / "docs/planning/GAMEPLAN-v2.md")
        and json_hash == file_sha256(Path(gameplan_json_path) if gameplan_json_path else repo / "docs/planning/gameplan-v2.json")
        and (candidate_plan_hash is None or candidate_plan_hash == plan_hash)
        and (candidate_json_hash is None or candidate_json_hash == json_hash)
        and (expected_gameplan_sha256 is None or expected_gameplan_sha256 == plan_hash)
        and (expected_gameplan_json_sha256 is None or expected_gameplan_json_sha256 == json_hash)))

    def scenarios():
        matrix = data["matrix"]
        results = [json.loads(line) for line in _safe_artifact(root, "results/SCENARIO-RESULTS.jsonl").read_text().splitlines()]
        if [r["scenario_id"] for r in results] != [c["scenario_id"] for c in matrix]:
            return False
        hashes = read("state-hashes/scenario_hashes.json")
        if set(hashes) != {c["scenario_id"] for c in matrix}:
            return False
        for c, r in zip(matrix, results):
            sid = c["scenario_id"]
            trace = verify_scenario_trace_integrity(sid, root, c["contract_hash"])
            state = read(f"state-hashes/{sid}.json")
            oracle = state["oracle_evaluation"]
            if (r["verdict"] != "passed" or oracle["passed"] is not True or oracle["failures"]
                    or not oracle["checks"] or not all(v is True for v in oracle["checks"].values())
                    or state["scenario_id"] != sid or oracle["scenario_id"] != sid
                    or state["contract_hash"] != c["contract_hash"]
                    or r["contract_hash"] != c["contract_hash"]
                    or r["features"] != c["features_exercised"]
                    or r["features_exercised"] != c["features_exercised"]
                    or set(r["invariants_passed"]) != set(oracle["invariants_verified"])
                    or set(r["invariants_passed"]) != set(c["invariants_tested"])
                    or r["state_hash"] != state["final_state_hash"] or hashes[sid] != r["state_hash"]
                    or r["state_hash"] != trace["final_state_hash"]
                    or state["initial_state_hash"] != trace["initial_state_hash"]
                    or r["initial_state_hash"] != trace["initial_state_hash"]
                    or any(r[k] != trace[k] for k in ("commands_count", "trace_records_count", "commands_sha256", "trace_sha256"))):
                return False
        reg = read("REGRESSION-RESULTS.json")
        if (reg["regression_verdict"] != "passed" or reg["scenarios_executed"] != len(matrix)
                or reg["scenarios_passed"] != len(matrix) or reg["scenarios_failed"] != 0
                or reg["scenario_matrix_sha256"] != file_sha256(root / "SCENARIO-MATRIX.json")):
            return False
        data.update(results=results, reg=reg)
        return True

    check("all_scenarios_passed", scenarios, all_scenarios_passed)
    check("all_traces_substantive", lambda: gates["all_scenarios_passed"], all_traces_substantive)

    def invariants():
        summaries = read("INVARIANT-RESULTS.json")
        catalog = [c for c in data["catalog"] if c["kind"] == "scenario"]
        if [s["invariant_id"] for s in summaries] != [c["id"] for c in catalog]:
            return False
        for inv in summaries:
            count = sum(inv["invariant_id"] in c["invariants_tested"] for c in data["matrix"])
            if inv["invariant_id"] == "INV-REPLAY":
                count += 1
            if inv["passed"] is not True or inv["evaluations_count"] != count or count <= 0:
                return False
        data["invariants"] = summaries
        reg = data["reg"]
        return reg["invariants_passed"] == len(catalog) and reg["invariants_failed"] == 0

    check("all_scenario_invariants_passed", invariants, all_invariants_passed)
    check("golden_replay_verified", lambda: (
        data["reg"]["golden_replay_verified"] is True
        and data["reg"]["golden_replay_final_state_hash"] == read("state-hashes/scenario_hashes.json")["SCEN-E2E-01"]
        and data["reg"]["offline_replay_final_state_hash"] == read("state-hashes/scenario_hashes.json")["SCEN-OFF-01"]), golden_replay_verified)

    def corpus():
        if not gates["pre_review_evidence_complete"] or not gates["frozen_requirements_valid"]:
            return False
        from .scenario_inputs import build_corpus_manifest, generate_viewer_corpus
        manifest = read("CORPUS-MANIFEST.json")
        seeds = read("seeds.json")
        if seeds["scenario_seeds"] != {c["scenario_id"]: c["seed"] for c in data["matrix"]}:
            return False
        regenerated = build_corpus_manifest(generate_viewer_corpus(
            seed=manifest["seed"], count=manifest["count"],
            start_tick=manifest["start_tick"], tick_stride=manifest["tick_stride"]))
        return (manifest == regenerated and manifest["sha256"] == data["reg"]["corpus_sha256"]
                and seeds["corpus_seed"] == manifest["seed"] and seeds["corpus_count"] == manifest["count"])

    check("corpus_hash_valid", corpus, corpus_hash_valid)

    def coverage():
        inventory, summary = derive_feature_statuses(
            contract["feature_specs"], data["results"],
            total_invariants=len(data["invariants"]), passed_invariants=len(data["invariants"]))
        return inventory == read("FEATURE-INVENTORY.json") and summary == read("COVERAGE.json")

    check("feature_coverage_honestly_derived", coverage, feature_coverage_honestly_derived)
    review = {}
    def verified_review():
        review.update(verify_independent_review_artifact(root))
        return review["verified"] is True
    check("independent_review_verified", verified_review, independent_review_verified)

    def configured_review():
        invocation = read("REVIEW-INVOCATION.json")
        policy = json.loads((repo / "config/model-policy.json").read_text())
        profile = policy["profiles"][policy["tasks"]["plan_review"]]
        return (gates["independent_review_verified"]
                and invocation["reviewer_model"] == profile["model"]
                and invocation["reviewer_effort"] == profile["reasoning_effort"]
                and invocation["reviewer_provider"] == profile["provider"]
                and invocation["configured_model"] == profile["model"]
                and invocation["configured_effort"] == profile["reasoning_effort"]
                and invocation["configured_provider"] == profile["provider"]
                and invocation["configured_model_available"] is True
                and invocation["configured_gate_satisfied"] is True
                and invocation["gate_binding"] == "configured_gate")
    check("independent_review_uses_configured_gate", configured_review, independent_review_is_configured_gate)
    verdict = review.get("verdict", "UNVERIFIED")
    check("review_verdict_is_ready", lambda: verdict == "READY" and (review_verdict is None or review_verdict == verdict))

    def issues():
        records = read("ISSUES.json")
        if type(records) is not list or not records:
            return False
        bound_hashes = {e["sha256"] for e in bindings.values()}
        if any(i["status"] != "closed" or require_hash(i["resolution_hash"]) not in bound_hashes for i in records):
            return False
        return blocking_issues_count is None or blocking_issues_count == 0
    check("all_s0_s1_blocking_s2_issues_closed", issues)

    unresolved = [d["id"] for d in contract.get("unresolved_decisions", [])
                  if d.get("status") == "unresolved" and d.get("gate") != "before_live_submission"]
    check("no_unresolved_blocking_decisions", lambda: (
        "unresolved_decisions" in contract and not unresolved
        and (unresolved_human_decisions is None or unresolved_human_decisions == [])))

    def safe_read(rel, default=None):
        try:
            return read(rel)
        except Exception:
            return default

    manifest_obj = safe_read("RUN-MANIFEST.json", {})
    artifacts_map = manifest_obj.get("artifact_hashes", {}) if isinstance(manifest_obj, dict) else {}
    if not artifacts_map:
        rev_ev = safe_read("REVIEW-EVIDENCE.json", {})
        if isinstance(rev_ev, dict) and "artifact_hashes" in rev_ev:
            artifacts_map = rev_ev["artifact_hashes"]
            manifest_obj = {"artifact_hashes": artifacts_map}
    review_inv_obj = safe_read("REVIEW-INVOCATION.json", {})
    review_md_text = ""
    try:
        if (root / "INDEPENDENT-REVIEW.md").is_file():
            review_md_text = _safe_artifact(root, "INDEPENDENT-REVIEW.md").read_text(encoding="utf-8")
    except Exception:
        pass

    bundle_for_pipe = {
        "review_invocation": review_inv_obj if isinstance(review_inv_obj, dict) else {},
        "review_text": review_md_text,
        "new_run_id": root.name,
        "old_run_id": PRESERVED_REJECTED_RUN_ID,
        "old_run_tree_sha256_before": PRESERVED_REJECTED_TREE_SHA256,
        "old_run_tree_sha256_after": compute_tree_sha256(repo / "artifacts/simulations/full-game" / PRESERVED_REJECTED_RUN_ID) if (repo / "artifacts/simulations/full-game" / PRESERVED_REJECTED_RUN_ID).is_dir() else None,
        "manifest": manifest_obj,
        "recomputed_hashes": {f: file_sha256(root / f) for f in artifacts_map if (root / f).is_file()},
        "source_bindings": bindings,
        "recomputed_source_hashes": {p: file_sha256(repo / p) for p in bindings if (repo / p).is_file()},
        "matrix": data.get("matrix", []),
        "per_invariant_results": safe_read("INVARIANT-RESULTS.json", []),
        "readiness": safe_read("DEVELOPMENT-READINESS.json", {}),
        "review_verdict": verdict,
        "evidence_passed": gates.get("pre_review_evidence_complete", False) and gates.get("all_scenarios_passed", False),
    }

    pipe_evals = {
        "INV-REVIEW-AUTHORSHIP": validate_review_authorship(bundle_for_pipe),
        "INV-RUN-IMMUTABILITY": validate_run_immutability(bundle_for_pipe),
        "INV-CITATION-HASHES": validate_citation_hashes(bundle_for_pipe),
        "INV-SOURCE-BYTES": validate_source_bytes(bundle_for_pipe),
        "INV-EVIDENCE-COVERAGE": validate_evidence_coverage(bundle_for_pipe),
        "INV-READINESS-SEPARATION": validate_readiness_separation(bundle_for_pipe),
    }

    pipeline_results = {k: (v.get("status") == "PASS") for k, v in pipe_evals.items()}
    check("all_pipeline_invariants_passed", lambda: all(pipeline_results.values()))
    def stage_metadata():
        metadata = read("STAGE-METADATA.json")
        policy = json.loads((repo / "config/directive-policy.json").read_text())
        return (metadata["stage"] == "pre_review" and metadata["review_observed"] is False
                and metadata["directive_ledger_revision"] == policy["revision"]
                and f"Revision {policy['revision']}" in _safe_artifact(root, "PLAN-CHANGELOG.md").read_text()
                and "no independent review observed at this stage" in _safe_artifact(root, "SIMULATION-REPORT.md").read_text())
    check("generated_stage_metadata_valid", stage_metadata)

    def audit_ledger():
        ledger = read("AUDIT-FINDINGS.json")
        if [i["id"] for i in ledger] != [f"AUDIT-{n:02}" for n in range(1, 20)]:
            return False
        inventory = verify_pre_review_inventory(root)["artifact_hashes"]
        evaluations = []
        all_closed_valid = True
        by_id = {r["scenario_id"]: r for r in data.get("results", [])}
        for item in ledger:
            if (item["validator_ids"] != AUDIT_VALIDATORS[item["id"]]
                    or item["severity"] != AUDIT_SEVERITIES[item["id"]]
                    or not item["evidence_hashes"]):
                return False
            for rel, digest in item["evidence_hashes"].items():
                if inventory.get(rel) != require_hash(digest):
                    return False
            if item["resolution_hash"] != canonical_hash(item["evidence_hashes"]):
                return False
            evaluated = all(gates.get(v) is True or by_id.get(v, {}).get("verdict") == "passed"
                            for v in item["validator_ids"])
            evidence = dict(item["evidence_hashes"])
            if item["status"] == "pending_external_review":
                if item["id"] not in ("AUDIT-01", "AUDIT-10"):
                    return False
                evaluated = evaluated and gates["review_verdict_is_ready"]
                if gates["independent_review_verified"]:
                    evidence.update({name: file_sha256(root / name) for name in (
                        "INDEPENDENT-REVIEW.md", "INDEPENDENT-REVIEW.json", "REVIEW-INVOCATION.json")})
                all_closed_valid = all_closed_valid and evaluated
            elif item["status"] == "open":
                if item["severity"] in ("S0", "S1") or item.get("blocking") is True:
                    all_closed_valid = False
            elif item["status"] != "closed":
                return False
            else:
                all_closed_valid = all_closed_valid and evaluated
            evaluations.append({
                **item, "status": "closed" if evaluated else "open",
                "evaluated": evaluated, "evidence_hashes": evidence,
                "resolution_hash": canonical_hash(evidence),
            })
        data["audit_findings"] = evaluations
        return all_closed_valid
    check("audit_findings_resolved", audit_ledger)
    # A missing or mutated inventory invalidates every assertion based on it.
    ready = all(gates.values())
    return detached({
        "ready": ready, "simulation_and_plan_ready": ready, "submission_ready": False,
        "candidate_plan_revision": data.get("revision"), "candidate_plan_hash": plan_hash,
        "candidate_gameplan_json_hash": json_hash,
        "expected_scenarios": len(data.get("matrix", [])),
        "expected_invariants": len(data.get("catalog", [])),
        "blocking_issues_count": 0 if gates["all_s0_s1_blocking_s2_issues_closed"] else None,
        "unresolved_human_decisions": unresolved if contract else None,
        "review_verdict": verdict, "independent_review_verified": gates["independent_review_verified"],
        "pipeline_invariant_results": pipeline_results,
        "invariant_results": data.get("invariants", []) + [
            {"invariant_id": inv["id"], "name": inv["name"], "kind": "pipeline",
             "evaluations_count": 1, "passed": pipeline_results[inv["id"]]}
            for inv in PIPELINE_INVARIANTS
        ],
        "audit_findings": data.get("audit_findings", []),
        "gates": gates, "failed_gates": [k for k, v in gates.items() if not v],
        "evaluation_errors": errors,
        "required_work_packages_order": contract.get("required_work_packages_order", []),
    })


def _configured_plan_review_route(repo_root: Path) -> Tuple[str, str]:
    """Return the configured `plan_review` model and effort from `config/model-policy.json`."""
    policy = json.loads((Path(repo_root) / "config/model-policy.json").read_text(encoding="utf-8"))
    profile = policy["profiles"][policy["tasks"]["plan_review"]]
    return str(profile["model"]), str(profile["reasoning_effort"])


def _is_valid_hash(value: Any) -> bool:
    try:
        require_hash(value)
        return True
    except ValueError:
        return False


def seal_run_manifest(
    run_dir: Path,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Mechanically enumerate and hash all files in `run_dir`, writing RUN-MANIFEST.json exclusively last."""
    root = Path(run_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Run directory does not exist: {root}")
    manifest_path = root / "RUN-MANIFEST.json"
    if manifest_path.exists():
        raise FileExistsError(f"RUN-MANIFEST.json already exists in {root}")

    verify_source_bindings(root)
    verify_independent_review_artifact(root)
    readiness = json.loads(_safe_artifact(root, "DEVELOPMENT-READINESS.json").read_text())
    recomputed = compute_development_readiness(root)
    if readiness != recomputed:
        raise ValueError("Readiness differs from seal-time evidence evaluation")

    artifact_hashes: Dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "RUN-MANIFEST.json":
            rel = p.relative_to(root).as_posix()
            artifact_hashes[rel] = file_sha256(p)

    if not artifact_hashes:
        raise ValueError(f"Cannot seal empty run directory: {root}")

    meta = dict(metadata) if metadata else {}
    run_manifest = {
        "schema_version": 1,
        "run_id": meta.get("run_id", root.name),
        "utc_timestamp": meta.get(
            "utc_timestamp", datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        ),
        "authorization": meta.get("authorization", AUTHORIZATION_TOKEN),
        "plan_baseline_revision": meta.get("plan_baseline_revision", 4),
        "plan_candidate_revision": readiness["candidate_plan_revision"],
        "authoritative_source_hashes": meta.get("authoritative_source_hashes", {}),
        "artifact_count": len(artifact_hashes),
        "artifact_hashes": artifact_hashes,
        "total_scenarios": readiness["expected_scenarios"],
        "total_passed": meta.get("total_passed"),
        "total_failed": meta.get("total_failed"),
        "status": "completed" if readiness["ready"] else "completed_not_ready",
    }
    write_exclusive_json(manifest_path, run_manifest)
    return detached(run_manifest)
