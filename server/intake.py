"""Offline Twitch identity linking and canonical command intake (W5/TASK-008).

Offline adapter boundary only: no network, no Twitch API, no credentials, no
account linking against real services. Until separate live-integration
authorization every identity here is a labeled local fixture.

D-03 fairness note (recorded, not solved): live eligibility means an
authenticated platform subject at account level with a linked chat/button
identity, and unlinked input is rejected before the engine. Account-level quota
is **not** one-human proof and does not prevent Sybils.

Adapter rule: identity, command type, sequence, timing, pause/terminal and
dedup validation all complete here before any engine application. Adapters
never mutate engine state directly; they only submit canonical command
envelopes through `AuthoritativeGame.submit`.

Canonical joins and leaves are both effective at the next engine roster freeze.
Intake eligibility is revoked immediately on an accepted leave, while the
current turn's frozen quorum denominator remains unchanged.
"""
from collections import OrderedDict
import threading
from typing import Any, Dict, List, Optional

from coordination.canonical_commands import make_command

AUDIENCE_KINDS = frozenset({"streamer.steer", "viewer.counter", "hazard.propose"})
PROVENANCE_WEIGHT = {"human": 1, "fixture": 0, "bot": 0}
RATE_LIMIT_TICKS = 10  # 0.5s at 20 Hz, per account subject
MAX_TRACKED = 10000


def _bounded_text(value: Any, label: str, limit: int = 128) -> str:
    if (type(value) is not str or not value.strip() or len(value) > limit
            or any(ord(char) < 32 for char in value)):
        raise ValueError(f"{label} must be bounded nonempty text")
    return value


class IdentityRegistry:
    """Account-level subjects with linked chat/button identities (offline fixture)."""

    def __init__(self) -> None:
        self._subject_by_channel: Dict[str, str] = {}
        self._channels_by_subject: Dict[str, set] = {}
        self._lock = threading.RLock()

    def link(self, platform_subject: str, channel_identity: str) -> str:
        subject = _bounded_text(platform_subject, "platform_subject")
        channel = _bounded_text(channel_identity, "channel_identity")
        with self._lock:
            existing = self._subject_by_channel.get(channel)
            if existing is not None and existing != subject:
                raise ValueError("channel identity already linked to another account")
            if existing is None and len(self._subject_by_channel) >= MAX_TRACKED:
                raise ValueError("identity registry capacity reached")
            if subject not in self._channels_by_subject and len(self._channels_by_subject) >= MAX_TRACKED:
                raise ValueError("identity registry capacity reached")
            self._subject_by_channel[channel] = subject
            self._channels_by_subject.setdefault(subject, set()).add(channel)
        return subject

    def reconnect(self, platform_subject: str, new_channel_identity: str) -> str:
        """Reconnect keeps the same account subject and therefore its influence history."""
        return self.link(platform_subject, new_channel_identity)

    def resolve(self, channel_identity: str) -> Optional[str]:
        with self._lock:
            return self._subject_by_channel.get(channel_identity)

    def is_linked(self, platform_subject: str) -> bool:
        with self._lock:
            return platform_subject in self._channels_by_subject

    def channels(self, platform_subject: str) -> List[str]:
        with self._lock:
            return sorted(self._channels_by_subject.get(platform_subject, set()))


class CommandIntake:
    """Validated intake from linked identities into the authoritative engine."""

    def __init__(self, engine: Any, registry: Optional[IdentityRegistry] = None) -> None:
        self.engine = engine
        self.registry = registry or IdentityRegistry()
        self._seen_receipts: OrderedDict[str, None] = OrderedDict()
        # These maps are keyed by registry subjects, whose count is capped by
        # IdentityRegistry. Never evict them: doing so would reopen stale input.
        self._last_sequence: Dict[str, int] = {}
        self._last_accepted_tick: Dict[str, int] = {}
        self._left: set = set()
        self._roster_sequence = 0
        self._lock = threading.RLock()
        self.decisions: List[Dict[str, Any]] = []

    # ----- roster -----------------------------------------------------------
    def join(self, platform_subject: str) -> str:
        """Register an account subject; the engine applies joins at the next turn freeze."""
        with self._lock, self.engine.synchronized():
            subject = _bounded_text(platform_subject, "platform_subject")
            if not self.registry.is_linked(subject):
                self._record("-", subject, "audience.register", "rejected", "unlinked_identity")
                return "rejected"
            status = self.engine.submit(make_command(
                "audience.register", subject, "human", self.engine.tick,
                self._next_roster_sequence(), {"account_id": subject},
            ))
            if status == "applied":
                self._left.discard(subject)
            return status

    def leave(self, platform_subject: str) -> str:
        """Revoke intake now and queue engine quorum removal for the next turn."""
        with self._lock, self.engine.synchronized():
            subject = _bounded_text(platform_subject, "platform_subject")
            if not self.registry.is_linked(subject):
                return "rejected"
            status = self.engine.submit(make_command(
                "audience.leave", subject, "human", self.engine.tick,
                self._next_roster_sequence(), {"account_id": subject},
            ))
            if status == "applied":
                self._left.add(subject)
            return self._record("-", subject, "audience.leave", status,
                                "engine_" + status)

    def influence_weight(self, provenance: str) -> int:
        return PROVENANCE_WEIGHT.get(provenance, 0)

    # ----- command intake ---------------------------------------------------
    def submit(
        self,
        receipt_id: str,
        channel_identity: str,
        kind: str,
        payload: Dict[str, Any],
        sequence: int,
        provenance: str = "human",
    ) -> str:
        """Validate one receipt, then submit at most one canonical command."""
        receipt = _bounded_text(receipt_id, "receipt_id")
        with self._lock, self.engine.synchronized():
            # One critical section covers receipt admission, rate state and engine submit.
            if receipt in self._seen_receipts:
                return self._record(receipt, None, kind, "duplicate", "transport_duplicate")
            self._remember(self._seen_receipts, receipt, None)

            subject = self.registry.resolve(channel_identity)
            if subject is None:
                return self._record(receipt, None, kind, "rejected", "unlinked_identity")
            if subject in self._left:
                return self._record(receipt, subject, kind, "rejected", "subject_left")
            if kind not in AUDIENCE_KINDS:
                return self._record(receipt, subject, kind, "rejected", "unsupported_kind")
            if provenance != "human" and provenance not in ("bot", "fixture"):
                return self._record(receipt, subject, kind, "rejected", "invalid_provenance")
            if self.engine.status != "racing":
                return self._record(receipt, subject, kind, "rejected", "terminal_state")
            if self.engine.is_paused:
                return self._record(receipt, subject, kind, "rejected", "paused")
            if type(sequence) is not int or sequence <= self._last_sequence.get(subject, -1):
                return self._record(receipt, subject, kind, "rejected", "stale_sequence")
            if self.engine.tick - self._last_accepted_tick.get(subject, -10 ** 9) < RATE_LIMIT_TICKS:
                return self._record(receipt, subject, kind, "rejected", "rate_limited")

            command = make_command(kind, subject, provenance, self.engine.tick, sequence, payload)
            status = self.engine.submit(command)
            if status in ("applied", "duplicate"):
                self._last_sequence[subject] = sequence
                self._last_accepted_tick[subject] = self.engine.tick
            return self._record(receipt, subject, kind, status,
                                "engine_" + status, provenance=provenance)

    # ----- internals --------------------------------------------------------
    def _next_roster_sequence(self) -> int:
        self._roster_sequence += 1
        return self._roster_sequence

    @staticmethod
    def _remember(mapping: OrderedDict, key: str, value: Any) -> None:
        mapping[key] = value
        mapping.move_to_end(key)
        while len(mapping) > MAX_TRACKED:
            mapping.popitem(last=False)

    def _record(self, receipt: str, subject: Optional[str], kind: str, status: str,
                reason: str, provenance: str = "human") -> str:
        self.decisions = (self.decisions + [{
            "receipt_id": receipt,
            "subject": subject,
            "kind": kind,
            "status": status,
            "reason": reason,
            "provenance": provenance,
            "tick": self.engine.tick,
            "weight": self.influence_weight(provenance),
        }])[-MAX_TRACKED:]
        return status
