"""External review recorder. Simulation/finalization must never call this writer.

The caller supplies an actually observed independent invocation. Local hashes
bind its bytes and declared identity; they are not provider authentication.
This module invokes no model, service, network or gameplay.
"""
import json
from pathlib import Path
from typing import Any, Dict

from .content_cache import bytes_hash, require_hash
from .evidence_pipeline import (
    _PROTECTED_REVIEW_FILENAMES, _extract_verdict_from_markdown,
    file_sha256, verify_pre_review_inventory, verify_source_bindings,
)


def record_external_review(
    run_dir: Path, *, review_markdown: str, review_json: Dict[str, Any],
    invocation: Dict[str, Any],
) -> Dict[str, Any]:
    """Record a real review once, after verifying the frozen raw evidence."""
    root = Path(run_dir)
    if (root / "RUN-MANIFEST.json").exists():
        raise FileExistsError("Cannot review or reseal a finalized run")
    if any((root / name).exists() for name in _PROTECTED_REVIEW_FILENAMES):
        raise FileExistsError("Independent review provenance already exists")
    inventory = verify_pre_review_inventory(root)
    verify_source_bindings(root)
    packet_sha = file_sha256(root / "REVIEW-PACKET.md")
    verdict = _extract_verdict_from_markdown(review_markdown)
    if review_json.get("verdict") != verdict or invocation.get("verdict") != verdict:
        raise ValueError("Review verdicts disagree")
    if invocation.get("evidence_origin") != "independent_subagent_review":
        raise ValueError("Only observed independent subagent review is accepted")
    for key in ("subagent_conversation_id", "reviewer_model", "reviewer_effort",
                "reviewer_provider", "configured_model", "configured_effort",
                "configured_provider", "gate_binding"):
        if type(invocation.get(key)) is not str or not invocation[key].strip():
            raise ValueError(f"Missing invocation field: {key}")
    for key in ("configured_model_available", "configured_gate_satisfied"):
        if type(invocation.get(key)) is not bool:
            raise ValueError(f"Missing invocation predicate: {key}")
    require_hash(invocation.get("packet_hash"))
    require_hash(invocation.get("prompt_sha256"))
    if invocation.get("review_packet_sha256") != packet_sha:
        raise ValueError("Invocation does not bind the actual review packet")

    md_bytes = review_markdown.encode("utf-8")
    json_bytes = (json.dumps(review_json, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    usage = [{
        "agent_role": "Independent Evidence Reviewer",
        "model": invocation["reviewer_model"],
        "provider": invocation["reviewer_provider"],
        "reasoning_effort": invocation["reviewer_effort"],
        "configured_model": invocation["configured_model"],
        "configured_gate_satisfied": invocation["configured_gate_satisfied"],
        "subagent_conversation_id": invocation["subagent_conversation_id"],
        "evidence_origin": invocation["evidence_origin"],
        "output_sha256": bytes_hash(md_bytes), "verdict": verdict,
    }]
    receipt = {**invocation, "schema_version": 2, "run_id": root.name,
               "authored_by": "coordination.review_boundary",
               "evidence_root_sha256": inventory["root_sha256"],
               "independent_review_sha256": bytes_hash(md_bytes),
               "independent_review_json_sha256": bytes_hash(json_bytes),
               "model_usage": usage}
    payloads = {
        "INDEPENDENT-REVIEW.md": md_bytes,
        "INDEPENDENT-REVIEW.json": json_bytes,
        "MODEL-USAGE.json": (json.dumps(usage, indent=2) + "\n").encode(),
        # Invocation is the last receipt; incomplete recording fails closed.
        "REVIEW-INVOCATION.json": (json.dumps(receipt, indent=2) + "\n").encode(),
    }
    for name, raw in payloads.items():
        target = root / name
        if root.is_symlink() or any(p.is_symlink() for p in root.parents):
            raise ValueError("Symlink review root is forbidden")
        with target.open("xb") as handle:
            handle.write(raw)
    return receipt
