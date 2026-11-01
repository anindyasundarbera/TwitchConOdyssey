"""Explicit, bounded model selection and an injected inference boundary."""
import argparse
import hashlib
import json
from pathlib import Path

DEFAULT_POLICY = Path(__file__).resolve().parents[1] / "config/model-policy.json"
FORBIDDEN_TASKS = {"gameplay_actor", "chat_action"}


def require_plan(scope, task=None):
    # Keep this before policy reads and executor calls.
    if scope != "plan" or task in FORBIDDEN_TASKS:
        raise ValueError("Only plan scope is authorized; gameplay execution is disabled")


def choose_model(task, scope="plan", *, policy_path=DEFAULT_POLICY):
    require_plan(scope, task)
    raw = Path(policy_path).read_bytes()
    policy = json.loads(raw)
    if (policy.get("execution_scope") != "plan_only"
            or policy.get("gameplay_simulation_enabled") is not False
            or policy.get("automatic_escalation") is not False):
        raise ValueError("Policy must explicitly enforce plan-only, no escalation")
    if task not in policy["tasks"]:
        raise ValueError(f"Unknown task: {task}")
    profile_name = policy["tasks"][task]
    profile = policy["profiles"][profile_name]
    if profile.get("enabled") is not True:
        raise ValueError(f"Disabled profile: {profile_name}")
    for key in ("max_input_chars", "max_output_tokens"):
        if type(profile.get(key)) is not int or profile[key] <= 0:
            raise ValueError(f"Invalid budget: {key}")
    for key in ("provider", "model", "reasoning_effort"):
        if not isinstance(profile.get(key), str) or not profile[key].strip():
            raise ValueError(f"Missing profile field: {key}")
    return {"task": task, "scope": scope, "profile": profile_name,
            **{key: profile[key] for key in ("provider", "model", "reasoning_effort",
                                           "max_input_chars", "max_output_tokens")},
            "policy_hash": hashlib.sha256(raw).hexdigest()}


def infer(task, prompt, executor, scope="plan", *, policy_path=DEFAULT_POLICY):
    """Call executor(prompt=..., decision=...) exactly once; never retry/fallback."""
    decision = choose_model(task, scope, policy_path=policy_path)
    if not isinstance(prompt, str) or len(prompt) > decision["max_input_chars"]:
        raise ValueError("Prompt exceeds character budget or is not text")
    output = executor(prompt=prompt, decision=dict(decision))
    return {"decision": decision, "output": output, "evidence_origin": "injected_executor",
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(),
            "output_hash": hashlib.sha256(json.dumps(output, sort_keys=True).encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--scope", default="plan")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    args = parser.parse_args()
    try:
        print(json.dumps(choose_model(args.task, args.scope, policy_path=args.policy), indent=2))
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
