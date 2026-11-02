"""Compile deterministic, bounded plan-only directive packets using local files.

This is a preflight contract, not an executor or an authentication mechanism.
Hashes identify exact bytes. Only explicit user authorization changes a gate.
"""
import argparse
import json
from pathlib import Path, PurePosixPath

from .content_cache import bytes_hash, canonical_bytes, canonical_hash, require_hash

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = "config/directive-policy.json"
MODEL_POLICY = "config/model-policy.json"
MUST_HAVE = frozenset({
    "setting_san_diego", "fresh_packets", "context_reuse", "scripted_actors",
    "model_allocation", "manual_escalation", "packet_limits",
    "gate_to_game_interface_authorization_20261102",
    "evidence_independence", "frozen_artifacts", "precedence", "bounded_subagents",
})
MODEL_CAPS = {"gpt-6-luna": 24000, "gpt-6.1-terra": 24000,
              "gpt-6.1-sol": 32000, "gpt-6-sol": 32000, "gpt-6-astra": 40000}
PRECEDENCE = ["latest_explicit_user_instruction_and_phase_authorization",
              "active_directive_ledger_and_current_STATUS",
              "current_proposed_plan_and_context",
              "historical_research_rehearsal_and_agent_opinion"]
MAX_POLICY_BYTES = 128 * 1024
REQUIRED_SOURCES = frozenset({
    "AGENTS.md", MODEL_POLICY, "coordination/context_contract.py",
    "coordination/model_router.py", "coordination/content_cache.py",
    "docs/planning/STATUS.md", "docs/planning/CONTEXT-v2.md",
    "docs/planning/GAMEPLAN-v2.md", "docs/planning/USER-DIRECTIVE-AUDIT.md",
    "docs/planning/CONTEXT-RETENTION-RESEARCH.md",
    "docs/planning/gameplan-v2.json", "docs/planning/S1-SIMULATION-PROFILE.md",
    "docs/planning/research/S1-PLATFORM-EVIDENCE.md",
    "docs/planning/research/S1-SYSTEMS-EVIDENCE.md",
})
SELECTED_DECISIONS = {"D-01": "player_agency", "D-02": "survival_contract",
                      "D-03": "audience_fairness", "D-04": "reward_contract",
                      "D-05": "clock_contract"}
DECISION_IDS = frozenset(SELECTED_DECISIONS)
SELECTED_STATUS = "selected_for_s1_simulation_unverified"
SELECTED_SOURCE = "docs/planning/S1-SIMULATION-PROFILE.md"
MANDATORY_FORBIDDEN_ACTIONS = frozenset({
    "automatic phase advance", "automatic retry/escalation/provider change/silent fallback",
    "runtime migration", "deployment/publication/platform provisioning/provider setup/live calls",
    "frozen v1/context/rehearsal edits",
})
CLOSED_GATE_FORBIDDEN_ACTIONS = frozenset({
    "server.app", "server.replay", "gameplay tests", "browser gameplay", "harness.run",
})
FORBIDDEN_ACTIONS = MANDATORY_FORBIDDEN_ACTIONS


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _relative(value):
    if (type(value) is not str or not value or "\\" in value or "\x00" in value
            or ":" in value):
        raise ValueError("Unsafe repository-relative path")
    path = PurePosixPath(value)
    if (path.is_absolute() or ".." in path.parts or str(path) != value
            or value == "."):
        raise ValueError("Unsafe repository-relative path")
    return value


def _file(root, value):
    value = _relative(value)
    try:
        path = (root / value).resolve(strict=True)
        path.relative_to(root)
        if not path.is_file():
            raise ValueError("Required path is not a file")
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError(f"Missing or out-of-root required path: {value}") from exc
    return path


def _owned_binding(root, value, known_hash=None):
    """Describe an existing file or safe planned path, including new directories."""
    candidate = root / value
    if candidate.is_symlink():
        raise ValueError(f"Owned target must not be a symlink: {value}")
    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(root)
        ancestor = resolved.parent
        while not ancestor.exists():
            ancestor = ancestor.parent
        if not ancestor.is_dir():
            raise ValueError("Owned ancestor is not a directory")
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError(f"Invalid or out-of-root owned path: {value}") from exc
    if candidate.exists():
        digest = known_hash if known_hash is not None else bytes_hash(_file(root, value).read_bytes())
        return {"path": value, "state": "existing", "sha256": digest}
    return {"path": value, "state": "planned", "sha256": None}


def _strings(value, label, *, empty=False):
    if (type(value) is not list or (not value and not empty)
            or any(type(item) is not str or not item.strip() for item in value)
            or len(set(value)) != len(value)):
        raise ValueError(f"Invalid {label}")
    return value


def _text(value, label):
    if type(value) is not str or not value.strip():
        raise ValueError(f"Missing {label}")
    return value


def _validate(policy):
    """Validate the ledger before reading any of its bound source files."""
    if (type(policy) is not dict or type(policy.get("schema_version")) is not int
            or policy["schema_version"] != 1 or type(policy.get("revision")) is not int
            or policy["revision"] < 1):
        raise ValueError("Unsupported directive ledger version")
    if (policy.get("current_phase") != "plan" or policy.get("allowed_phases") != ["plan"]
            or policy.get("precedence") != PRECEDENCE or policy.get("conflicts") != []):
        raise ValueError("Unauthorized phase, precedence or unresolved directive conflict")
    gate = policy.get("gate")
    if type(gate) is not dict or gate.get("automatic_phase_advance") is not False:
        raise ValueError("Invalid gate or automatic phase advance enabled")
    gameplay_enabled = gate.get("gameplay_enabled")
    if gameplay_enabled is not True and gameplay_enabled is not False:
        raise ValueError("Invalid gameplay gate state")
    _text(gate.get("rule"), "gate rule")
    _text(policy.get("instruction_prefix"), "instruction prefix")
    policy_forbidden = _strings(policy.get("forbidden_actions"), "forbidden actions")
    if not MANDATORY_FORBIDDEN_ACTIONS.issubset(policy_forbidden):
        raise ValueError("Missing mandatory forbidden action")
    if not gameplay_enabled:
        if not CLOSED_GATE_FORBIDDEN_ACTIONS.issubset(policy_forbidden):
            raise ValueError("Closed gameplay gate requires forbidden gameplay actions")
    else:
        auth_id = gate.get("authorization_directive")
        if not auth_id or type(auth_id) is not str:
            raise ValueError("Authorized gameplay gate requires a bound active authorization directive")
    forbidden = _strings(policy.get("forbidden_tasks"), "forbidden tasks")
    if not {"gameplay_actor", "chat_action"}.issubset(forbidden):
        raise ValueError("Missing forbidden gameplay task")
    required = policy.get("required_paths")
    if type(required) is not dict or not REQUIRED_SOURCES.issubset(required):
        raise ValueError("Missing required source bindings")
    for path, digest in required.items():
        _relative(path)
        require_hash(digest)
    records = policy.get("directives")
    if type(records) is not list or not records:
        raise ValueError("Missing directives")
    by_id, topics = {}, set()
    for item in records:
        if type(item) is not dict:
            raise ValueError("Invalid directive record")
        ident = _text(item.get("id"), "directive ID")
        if ident in by_id or item.get("status") not in ("active", "superseded"):
            raise ValueError("Duplicate directive or invalid status")
        by_id[ident] = item
        _text(item.get("rule"), "directive rule")
        topic = _text(item.get("topic"), "directive topic")
        if item["status"] == "active":
            if topic in topics:
                raise ValueError("Conflicting active directives for a topic")
            topics.add(topic)
        if item.get("scope") != ["plan"]:
            raise ValueError("Invalid directive scope")
        wording = item.get("wording")
        if wording == "normalized":
            if (item.get("exact_user_wording") is not None
                    or item.get("wording_availability") != "unavailable"):
                raise ValueError("Normalized directive must mark exact wording unavailable")
        elif wording == "exact":
            _text(item.get("exact_user_wording"), "exact user wording")
            if item.get("wording_availability") != "recorded_verbatim":
                raise ValueError("Exact wording requires recorded provenance")
        else:
            raise ValueError("Invalid wording label")
        sources = item.get("provenance")
        if type(sources) is not list or not sources:
            raise ValueError("Missing directive provenance")
        for source in sources:
            if (type(source) is not dict or source.get("path") not in required
                    or source.get("source_kind") != "project_record"):
                raise ValueError("Directive source must have a required hash binding")
            _text(source.get("locator"), "source locator")
    for item in records:
        _strings(item.get("supersedes", []), "supersession links", empty=True)
        if item["status"] == "superseded":
            successor = by_id.get(item.get("superseded_by"))
            if successor is None or successor["status"] != "active":
                raise ValueError("Superseded directive requires an active successor")
            if item["id"] not in successor.get("supersedes", []):
                raise ValueError("Inconsistent supersession links")
        for old in item.get("supersedes", []):
            if old not in by_id or by_id[old].get("superseded_by") != item["id"]:
                raise ValueError("Inconsistent supersession links")
    if gameplay_enabled:
        auth_id = gate.get("authorization_directive")
        if auth_id not in by_id or by_id[auth_id].get("status") != "active":
            raise ValueError("Gameplay gate authorization directive must be active")
        auth_dir = by_id[auth_id]
        if auth_dir.get("topic") != "phase_authorization":
            raise ValueError("Gameplay gate authorization directive must cover phase_authorization")
        if auth_dir.get("wording") != "exact" or auth_dir.get("wording_availability") != "recorded_verbatim":
            raise ValueError("Gameplay gate authorization directive must have verbatim recorded wording")
        _text(auth_dir.get("exact_user_wording"), "gameplay authorization exact user wording")
    common = _strings(policy.get("common_directive_ids"), "common directive IDs")
    if not MUST_HAVE.issubset(common):
        raise ValueError("Missing mandatory directive selection")
    tasks = policy.get("tasks")
    if type(tasks) is not dict or not tasks:
        raise ValueError("Missing task mappings")
    for task, mapping in tasks.items():
        _text(task, "task name")
        if type(mapping) is not dict or task in forbidden:
            raise ValueError("Invalid task mapping")
        _text(mapping.get("routing_task"), "routing task")
        if mapping["routing_task"] in forbidden:
            raise ValueError("Gameplay routing is forbidden")
        ids = common + _strings(mapping.get("directive_ids"), "task directives", empty=True)
        for ident in ids:
            if ident not in by_id or by_id[ident]["status"] != "active":
                raise ValueError("Missing or inactive selected directive")
    selected = policy.get("selected_decisions")
    if type(selected) is not list or len(selected) != len(DECISION_IDS):
        raise ValueError("Missing mandatory selected decisions")
    selected_ids = set()
    for item in selected:
        if type(item) is not dict:
            raise ValueError("Invalid selected decision")
        ident = _text(item.get("id"), "selected decision ID")
        if ident in selected_ids or ident not in DECISION_IDS:
            raise ValueError("Duplicate or unexpected selected decision ID")
        selected_ids.add(ident)
        if (item.get("contract") != SELECTED_DECISIONS[ident]
                or item.get("status") != SELECTED_STATUS
                or item.get("gate") != "before_gameplay"
                or item.get("source_path") != SELECTED_SOURCE
                or item["source_path"] not in required
                or item.get("evidence_origin") != "project_design_inference"):
            raise ValueError("Invalid selected decision contract, status, gate or source binding")
        _text(item.get("rule"), "selected decision rule")
        _text(item.get("source_locator"), "selected decision source locator")
    if selected_ids != DECISION_IDS:
        raise ValueError("Missing mandatory selected decisions")
    decisions = policy.get("unresolved_decisions")
    if type(decisions) is not list or not decisions:
        raise ValueError("Missing unresolved decisions")
    unresolved_ids = set()
    publication_keys = {"repository_push", "youtube_upload", "devpost_final_submit"}
    for item in decisions:
        if (type(item) is not dict
                or item.get("status") not in ("unresolved", "authorized_in_progress")
                or item.get("source_path") not in required):
            raise ValueError("Invalid unresolved decision")
        for key in ("id", "rule", "gate"):
            _text(item.get(key), f"decision {key}")
        if (item["id"] in unresolved_ids or item["id"] in selected_ids
                or item["id"] in SELECTED_DECISIONS.values()):
            raise ValueError("Duplicate or cross-list decision ID")
        unresolved_ids.add(item["id"])
        if item["status"] != "authorized_in_progress":
            continue
        auth = policy.get(item.get("authorization_ref"))
        if type(auth) is not dict or auth.get("decision_id") != item["id"]:
            raise ValueError("Authorized decision requires a bound authorization record")
        _text(auth.get("exact_user_wording"), "authorization exact wording")
        if auth.get("wording_availability") != "recorded_verbatim":
            raise ValueError("Authorization wording must be recorded verbatim")
        _strings(auth.get("authorized_actions"), "authorized actions")
        excluded = _strings(auth.get("excluded_actions"), "excluded actions")
        if not {"publication", "credential_exposure"}.issubset(
                {value for value in excluded if isinstance(value, str)}):
            raise ValueError("Authorization must exclude publication and credential exposure")
        _strings(auth.get("external_inputs_required"), "external inputs")
        publications = auth.get("publication_authorizations")
        if (type(publications) is not dict or set(publications) != publication_keys
                or any(type(value) is not bool or value for value in publications.values())):
            raise ValueError("Publication booleans must remain false until exact targets authorize them")
        if auth.get("submission_ready") is not False or auth.get("compiler_gate_unchanged") is not True:
            raise ValueError("Authorization cannot claim readiness or change the plan compiler gate")
        review = auth.get("review_route")
        if (type(review) is not dict
                or review.get("requested") != {
                    "provider": "codex_subagent", "model": "gpt-6-astra",
                    "reasoning_effort": "high", "fork_turns": "none"}
                or review.get("substitution_fails_closed") is not True
                or review.get("serving_attestation_unavailable_is_not_a_substantive_blocker") is not True):
            raise ValueError("Invalid final review-route policy")
    return by_id


def compile_packet(task, phase="plan", owned_paths=(), *, root=ROOT,
                   policy_path=DEFAULT_POLICY):
    """Return a canonical-data packet; reject stale sources before routing.

    Root/policy overrides support isolated local fixtures. No environment,
    provider, runtime, transcript or historical artifact is implicitly loaded.
    """
    root = Path(root).resolve(strict=True)
    policy_file = _file(root, policy_path)
    if policy_file.stat().st_size > MAX_POLICY_BYTES:
        raise ValueError("Directive ledger exceeds byte budget")
    raw = policy_file.read_bytes()
    if len(raw) > MAX_POLICY_BYTES:
        raise ValueError("Directive ledger exceeds byte budget")
    try:
        policy = json.loads(raw, object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("Invalid directive ledger JSON") from exc
    # Reject task/phase before reading any sources or importing the router.
    if (type(policy) is not dict or phase != "plan"
            or phase != policy.get("current_phase")
            or type(policy.get("allowed_phases")) is not list
            or phase not in policy.get("allowed_phases", [])
            or type(policy.get("forbidden_tasks")) is not list
            or type(policy.get("tasks")) is not dict
            or type(task) is not str or task in {"gameplay_actor", "chat_action"}
            or task in policy.get("forbidden_tasks", [])
            or task not in policy.get("tasks", {})):
        raise ValueError("Unknown or forbidden task/phase; gameplay is disabled")
    try:
        by_id = _validate(policy)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Malformed directive ledger data") from exc
    owned = sorted({_relative(path) for path in owned_paths})
    source_raw, paths = {}, {}
    for path, expected in sorted(policy["required_paths"].items()):
        source_raw[path] = _file(root, path).read_bytes()
        digest = bytes_hash(source_raw[path])
        if digest != expected:
            raise ValueError(f"Changed required source hash: {path}; reconcile ledger first")
        paths[path] = digest
    for item in policy["unresolved_decisions"]:
        auth = policy.get(item.get("authorization_ref"))
        if auth is None:
            continue
        quote = auth["exact_user_wording"].encode("utf-8")
        if not any(quote in raw for raw in source_raw.values()):
            raise ValueError("Authorization exact wording is absent from bound sources")
    if policy["gate"].get("gameplay_enabled"):
        auth_id = policy["gate"].get("authorization_directive")
        auth_dir = by_id[auth_id]
        quote = auth_dir["exact_user_wording"].encode("utf-8")
        if not any(quote in source_raw[source["path"]] for source in auth_dir["provenance"]):
            raise ValueError("Gameplay gate exact authorization wording is absent from bound provenance")
    owned_bindings = [_owned_binding(root, path, paths.get(path)) for path in owned]
    paths.update({item["path"]: item["sha256"] for item in owned_bindings
                  if item["state"] == "existing"})
    try:
        model_policy = json.loads(source_raw[MODEL_POLICY], object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("Invalid model policy JSON") from exc
    if type(model_policy) is not dict:
        raise ValueError("Malformed model policy data")
    strategy = model_policy.get("token_saving_strategy", {})
    if (type(strategy) is not dict or strategy.get("automatic_retry") is not False
            or strategy.get("silent_model_fallback") is not False):
        raise ValueError("Model policy conflicts with no-retry/fallback directives")
    selected = sorted(set(policy["common_directive_ids"]
                          + policy["tasks"][task]["directive_ids"]))
    for ident in selected:
        item = by_id[ident]
        if item["wording"] == "exact":
            quote = item["exact_user_wording"].encode("utf-8")
            if not any(quote in source_raw[source["path"]] for source in item["provenance"]):
                raise ValueError("Exact user wording is absent from bound provenance")
    from .model_router import choose_model
    decision = choose_model(policy["tasks"][task]["routing_task"], scope="plan",
                            policy_path=_file(root, MODEL_POLICY))
    if decision["policy_hash"] != paths[MODEL_POLICY]:
        raise ValueError("Model policy changed during compilation")
    cap = MODEL_CAPS.get(decision["model"])
    if cap is None or decision["max_input_chars"] > cap:
        raise ValueError("Configured model or packet budget violates directive limits")
    packet = {"schema_version": 1, "ledger_revision": policy["revision"],
              "task": task, "phase": phase,
              "instruction_prefix": policy["instruction_prefix"],
              "precedence": policy["precedence"], "gate": policy["gate"],
              "directives": [by_id[ident] for ident in selected],
              "owned_paths": owned, "owned_path_bindings": owned_bindings,
              "required_paths": paths,
              "directive_policy": {"path": policy_path, "sha256": bytes_hash(raw)},
              "routing_decision": decision, "forbidden_actions": policy["forbidden_actions"],
              "selected_decisions": policy["selected_decisions"],
              "unresolved_decisions": policy["unresolved_decisions"],
              "return_limit_words": 250,
              "evidence_origin": "local_directive_compilation",
              "hash_meaning": "Exact byte bindings; not truth, authentication or authorization"}
    packet["packet_hash"] = canonical_hash(packet)
    if len(canonical_bytes(packet).decode("utf-8")) + 1 > decision["max_input_chars"]:
        raise ValueError("Compiled packet exceeds configured character budget")
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--phase", default="plan")
    parser.add_argument("--owned-path", action="append", default=[])
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        packet = compile_packet(args.task, args.phase, args.owned_path)
        if args.validate_only:
            packet = {"validated": True, "packet_hash": packet["packet_hash"]}
        print(canonical_bytes(packet).decode("utf-8"))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
