"""Prepare and aggregate document reviews. No runtime simulation or inference."""
import argparse
import hashlib
import json
from pathlib import Path

from .model_router import DEFAULT_POLICY, choose_model, require_plan

ROLES = {name: "plan_" + name for name in
         ("streamer", "viewer", "character", "attacker", "stage_operator", "security", "review")}
RESULT_KEYS = {"role", "plan_hash", "model", "findings", "runtime_executed"}
FINDING_KEYS = {"id", "severity", "scenario", "gap", "recommendation"}
SEVERITIES = {"low", "medium", "high", "critical"}
MAX_RESULT_BYTES = 65536


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_bounded(path, limit):
    with Path(path).open("rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"Document exceeds {limit} byte budget: {path}")
    return raw


def prepare(plan_path, context_paths=(), *, roles=None, mode="plan", policy_path=DEFAULT_POLICY):
    require_plan(mode)
    roles = list(ROLES) if roles is None else list(roles)
    if not roles or len(set(roles)) != len(roles) or any(role not in ROLES for role in roles):
        raise ValueError("Roles must be unique known review roles")
    decisions = {role: choose_model(ROLES[role], policy_path=policy_path) for role in roles}
    limit = min(d["max_input_chars"] for d in decisions.values())
    raw = read_bounded(plan_path, limit)
    if not isinstance(json.loads(raw), dict):
        raise ValueError("Plan must be a JSON object")
    contexts, content = [], []
    if len(context_paths) > 8:
        raise ValueError("At most eight explicit context documents")
    for path in context_paths:
        data = read_bounded(path, limit)
        contexts.append({"path": str(path), "sha256": digest(data)})
        content.append({"path": str(path), "text": data.decode("utf-8")})
    plan_hash = digest(raw)
    packets = []
    for role, decision in decisions.items():
        prompt = (f"Review this plan as {role}. This is a document-only rehearsal. "
                  "Do not execute gameplay, runtime, replay, servers, harnesses, or tools that run them. "
                  "Find gaps and scenarios; do not claim behavior was observed. Return only JSON with "
                  "role, plan_hash, model, findings, runtime_executed:false. Each finding requires "
                  "id,severity (low/medium/high/critical),scenario,gap,recommendation. "
                  f"role={role}; plan_hash={plan_hash}; model={decision['model']}\n"
                  + json.dumps({"plan": json.loads(raw), "context": content}, ensure_ascii=False))
        if len(prompt) > decision["max_input_chars"]:
            raise ValueError(f"Combined prompt exceeds budget for {role}")
        packets.append({"role": role, "decision": decision, "prompt": prompt})
    return {"schema_version": 1, "mode": "plan", "runtime_executed": False,
            "plan_path": str(plan_path), "plan_hash": plan_hash,
            "context": contexts, "packets": packets,
            "evidence_origin": "scripted_packet_preparation"}


def aggregate(manifest, results, *, plan_path, mode="plan", policy_path=DEFAULT_POLICY):
    require_plan(mode)
    if (not isinstance(manifest, dict) or manifest.get("mode") != "plan"
            or manifest.get("runtime_executed") is not False
            or manifest.get("schema_version") != 1):
        raise ValueError("Invalid plan-only manifest")
    if digest(read_bounded(plan_path, 40000)) != manifest["plan_hash"]:
        raise ValueError("Stale plan hash")
    for context in manifest["context"]:
        if digest(read_bounded(context["path"], 40000)) != context["sha256"]:
            raise ValueError("Stale context hash")
    expected = {}
    for packet in manifest["packets"]:
        role = packet["role"]
        if role not in ROLES or role in expected:
            raise ValueError("Unknown or duplicate role packet")
        decision = choose_model(ROLES[role], policy_path=policy_path)
        if decision != packet["decision"]:
            raise ValueError("Stale or changed model decision")
        expected[role] = decision
    if not expected or len(results) != len(expected):
        raise ValueError("Require exactly one result per role packet")
    seen = set()
    for result in results:
        if not isinstance(result, dict) or set(result) != RESULT_KEYS:
            raise ValueError("Malformed role result")
        role = result["role"]
        if not isinstance(role, str) or role not in expected or role in seen:
            raise ValueError("Unknown or duplicate result role")
        seen.add(role)
        if (result["runtime_executed"] is not False or result["plan_hash"] != manifest["plan_hash"]
                or result["model"] != expected[role]["model"]):
            raise ValueError("Runtime, hash or model mismatch")
        findings = result["findings"]
        if not isinstance(findings, list) or len(findings) > 30:
            raise ValueError("Findings must be a list of at most 30 entries")
        ids = set()
        for finding in findings:
            if (not isinstance(finding, dict) or set(finding) != FINDING_KEYS
                    or any(not isinstance(v, str) or not v.strip() or len(v) > 2000
                           for v in finding.values())
                    or finding["severity"] not in SEVERITIES or finding["id"] in ids):
                raise ValueError("Malformed finding")
            ids.add(finding["id"])
    return {"mode": "plan", "runtime_executed": False, "plan_hash": manifest["plan_hash"],
            "context": manifest["context"], "scripted_checks": {"evidence_origin": "scripted_validation",
            "checks": ["current plan/context hashes", "role schema", "model policy decisions"]},
            "agent_reviews": {"evidence_origin": "submitted_agent_review_json",
                              "authentication": "caller-supplied; identity not independently verified",
                              "expected_providers": {r: d["provider"] for r, d in expected.items()},
                              "canonical_result_hashes": {r["role"]: digest(json.dumps(r, sort_keys=True).encode())
                                                          for r in results},
                              "results": results},
            "limitation": "Document review only; no gameplay or runtime behavior verified"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "aggregate"))
    parser.add_argument("--mode", default="plan")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--context", type=Path, action="append", default=[])
    parser.add_argument("--role", choices=tuple(ROLES), action="append")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--result", type=Path, action="append", default=[])
    args = parser.parse_args()
    try:
        require_plan(args.mode)  # Reject forbidden mode before opening any files.
        if args.command == "prepare":
            output = prepare(args.plan, args.context, roles=args.role, mode=args.mode, policy_path=args.policy)
        else:
            if args.manifest is None:
                raise ValueError("aggregate requires --manifest")
            manifest = json.loads(read_bounded(args.manifest, 400000))
            results = [json.loads(read_bounded(path, MAX_RESULT_BYTES)) for path in args.result]
            output = aggregate(manifest, results, plan_path=args.plan, mode=args.mode, policy_path=args.policy)
        print(json.dumps(output, indent=2, ensure_ascii=False))
    except (ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
