"""Deterministic review-route evidence without route deadlock.

The final Astra review separates five facts that must never be collapsed into
one boolean:

* the exact route the requester asked for;
* the route the configured model policy selected;
* whether orchestration accepted the spawn;
* whether a substitution was reported (explicitly or by a reported route);
* whether an independent serving attestation is available;
* the substantive verdict for the exact frozen candidate.

Under the requester's 2026-11-02 decision, an unavailable serving attestation
is recorded as a caveat but is not by itself a substantive blocker. A rejected
spawn request, a reported substitution, a candidate mismatch, malformed
evidence or a non-READY verdict still fails closed. This module performs no
I/O, model call, retry or fallback.
"""
from typing import Any, Dict

REQUESTED_ROUTE = {
    "provider": "codex_subagent",
    "model": "gpt-6-astra",
    "reasoning_effort": "high",
    "fork_turns": "none",
}
ROUTE_FIELDS = frozenset(REQUESTED_ROUTE)


def _route(value: Any, label: str) -> Dict[str, str]:
    if type(value) is not dict or set(value) != ROUTE_FIELDS:
        raise ValueError(f"{label} must contain exactly {sorted(ROUTE_FIELDS)}")
    for key in ROUTE_FIELDS:
        if type(value[key]) is not str or not value[key].strip():
            raise ValueError(f"{label}.{key} must be bounded nonempty text")
    return {key: value[key] for key in ROUTE_FIELDS}


def evaluate_review_route(record: Any) -> Dict[str, Any]:
    """Return a detached, hash-friendly review-route evaluation.

    Raises ``ValueError`` for malformed evidence. A well-formed record whose
    spawn was rejected, whose route was substituted, whose candidate does not
    match, or whose verdict is not READY returns ``review_ready: False``.
    """
    if type(record) is not dict:
        raise ValueError("review route record must be an object")
    requested = _route(record.get("requested_route"), "requested_route")
    configured = _route(record.get("configured_route"), "configured_route")
    spawn = record.get("spawn")
    if type(spawn) is not dict:
        raise ValueError("spawn must be an object")
    if type(spawn.get("accepted")) is not bool:
        raise ValueError("spawn.accepted must be a boolean")
    if type(spawn.get("substitution_reported")) is not bool:
        raise ValueError("spawn.substitution_reported must be a boolean")
    reported = spawn.get("reported_route")
    if reported is not None:
        reported = _route(reported, "spawn.reported_route")
    if type(record.get("serving_attestation_available")) is not bool:
        raise ValueError("serving_attestation_available must be a boolean")
    if type(record.get("candidate_match")) is not bool:
        raise ValueError("candidate_match must be a boolean")
    if record.get("substantive_verdict") not in ("READY", "NOT-READY"):
        raise ValueError("substantive_verdict must be READY or NOT-READY")

    substitution = bool(spawn["substitution_reported"])
    if reported is not None and reported != requested:
        substitution = True
    attestation = record["serving_attestation_available"]
    checks = {
        "route_request_matches_configured": requested == configured,
        "route_request_is_exact_astra_high": requested == REQUESTED_ROUTE,
        "spawn_accepted": spawn["accepted"],
        "no_substitution_reported": not substitution,
        "candidate_match": record["candidate_match"],
        "substantive_verdict_ready": record["substantive_verdict"] == "READY",
    }
    reasons = [name for name, passed in checks.items() if not passed]
    ready = not reasons
    return {
        "requested_route": requested,
        "configured_route": configured,
        "reported_route": reported,
        "spawn_accepted": spawn["accepted"],
        "substitution_observed": substitution,
        "serving_attestation_available": attestation,
        # The requester's explicit decision: absence is a caveat, not a veto.
        "serving_attestation_caveat": not attestation,
        "serving_attestation_blocking": False,
        "candidate_match": record["candidate_match"],
        "substantive_verdict": record["substantive_verdict"],
        "checks": checks,
        "failure_reasons": reasons,
        "substantive_review_gate_satisfied": ready,
        "review_ready": ready,
    }
