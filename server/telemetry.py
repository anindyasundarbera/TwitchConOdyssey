"""Booth telemetry and privacy-bounded evidence (W6/TASK-009).

Observation-only boundary: the recorder reads detached canonical snapshots and
terminal settlement views. It never mutates gameplay state, never submits
commands, and never reads chat content or credentials.

Privacy rules (documented retention/redaction):
- No chat text, message bodies, tokens, credentials or free-text identity
  fields are recorded.
- No per-subject handles are emitted; audience facts are aggregate counts only.
  D-03 accounting that needs a subject reference is satisfied upstream by the
  command log's pseudonymous actor and the commit hazard ID linkage.
- Retention is bounded in memory (MAX_EVENTS); evidence is exported as an
  explicit manifest with per-artifact SHA-256 so W7 can package and W8 verify.

This repository has no authorized live identity/evidence adapter. The recorder
therefore emits fixture provenance only. There is deliberately no constructor
argument that can mint a live label; adding live evidence requires a separate
authorized adapter and review.
"""
from typing import Any, Dict, List, Optional

import hashlib

from coordination.content_cache import canonical_bytes, canonical_hash

SCHEMA_VERSION = 1
MAX_EVENTS = 2000
FIXTURE_ORIGIN = "fixture"
FIXTURE_LABEL = "offline fixture / simulation (not live Twitch activity)"

# Selected geometry (D-05): diegetic booth waypoints at exact route percentages.
BOOTH_WAYPOINTS = {
    35.0: "twitch_booth",
    60.0: "codex_booth",
    80.0: "aws_booth",
    100.0: "fictional_main_stage",
}
TERMINAL_STATUSES = {"delivered", "wiped", "failed"}


class TelemetryRecorder:
    """Privacy-bounded, append-only observer of authoritative engine state."""

    def __init__(self, game: Any, match_id: str) -> None:
        if type(match_id) is not str or not match_id.strip() or len(match_id) > 128:
            raise ValueError("match_id must be bounded nonempty text")
        self.game = game
        self.match_id = match_id
        self.origin = FIXTURE_ORIGIN
        self.events: List[Dict[str, Any]] = []
        self._last: Optional[Dict[str, Any]] = None
        self._warned_hazards: set = set()
        self._seen_booths: set = set()

    # ----- observation ------------------------------------------------------
    def poll(self) -> List[Dict[str, Any]]:
        """Read one detached snapshot and append any newly observed events."""
        state = self.game.snapshot()
        emitted: List[Dict[str, Any]] = []
        if self._last is None:
            emitted.append(self._emit("match_start", state, {
                "phase": state["phase"], "turn": state["turn"],
            }))
        last = self._last
        if last is not None and state["turn"] != last["turn"]:
            emitted.append(self._emit("turn_start", state, {"turn": state["turn"]}))
        hazard = state["hazard"].get("committed")
        if hazard and (last is None or hazard != last["hazard"].get("committed")):
            emitted.append(self._emit("hazard_committed", state, {"hazard_id": hazard}))
        if state["hazard"].get("warning_active") and hazard not in self._warned_hazards:
            self._warned_hazards.add(hazard)
            emitted.append(self._emit("warning", state, {"hazard_id": hazard}))
        if last is not None and state["bounty"]["collisions_total"] > last["bounty"]["collisions_total"]:
            emitted.append(self._emit("collision", state, {
                "collisions_total": state["bounty"]["collisions_total"],
                "hazard_id": hazard,
            }))
        for booth in state.get("booths", []):
            if booth not in self._seen_booths:
                self._seen_booths.add(booth)
                waypoint = next((pct for pct, name in BOOTH_WAYPOINTS.items() if name == booth), None)
                emitted.append(self._emit("booth_waypoint", state, {
                    "booth": booth, "waypoint_percent": waypoint,
                }))
        if state["status"] in TERMINAL_STATUSES and (last is None or last["status"] not in TERMINAL_STATUSES):
            emitted.append(self._emit_outcome(state))
        for event in emitted:
            self.events = (self.events + [event])[-MAX_EVENTS:]
        self._last = state
        return emitted

    def _emit(self, kind: str, state: Dict[str, Any], fields: Dict[str, Any]) -> Dict[str, Any]:
        event = {
            "schema_version": SCHEMA_VERSION,
            "match_id": self.match_id,
            "origin": self.origin,
            "origin_label": FIXTURE_LABEL,
            "live_participation": False,
            "tick": state["tick"],
            "turn": state["turn"],
            "phase": state["phase"],
            "event": kind,
        }
        event.update(fields)
        return event

    def _emit_outcome(self, state: Dict[str, Any]) -> Dict[str, Any]:
        settlement = self.game.settlement or {}
        return self._emit("outcome", state, {
            "status": state["status"],
            "hazard_id": state["hazard"].get("committed"),
            "settlement": {
                "status": settlement.get("status"),
                "tick": settlement.get("tick"),
                "total_hype": settlement.get("total_hype"),
                "streamer_share": settlement.get("streamer_share"),
                "audience_share_total": settlement.get("audience_share_total"),
                "settled_once": settlement.get("settled_once"),
                "reason": settlement.get("reason"),
            },
            "command_refs": self._command_refs(),
        })

    def _command_refs(self) -> List[Dict[str, Any]]:
        """Sequence/status references only — no chat content and no actor handles."""
        refs = []
        for entry in getattr(self.game, "_simulator", None).command_history[-50:] if hasattr(self.game, "_simulator") else []:
            cmd = entry.get("cmd") or {}
            refs.append({
                "kind": cmd.get("kind"),
                "sequence": cmd.get("sequence"),
                "status": entry.get("status"),
                "tick": entry.get("tick"),
            })
        return refs

    # ----- evidence ---------------------------------------------------------
    def evidence_bundle(self) -> Dict[str, bytes]:
        """Repo-convention evidence: artifact bytes plus a hashed manifest."""
        events_bytes = canonical_bytes({"events": self.events})
        artifacts = {"events.json": _sha256(events_bytes)}
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "match_id": self.match_id,
            "origin": self.origin,
            "live_participation": False,
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
        }
        return {"events.json": events_bytes, "MANIFEST.json": canonical_bytes(manifest)}


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
