"""Authoritative, fixed-step 20 Hz deterministic full-game simulation kernel.

Simulates the complete planned TwitchCon Odyssey game (Revision 4 baseline):
- Stylized San Diego route (5 segments: Little Italy/North Embarcadero, Waterfront/Marina,
  Gaslamp Quarter, San Diego Convention Center, Fictional Main Stage)
- Auto-forward three-lane streamer steering with 0.5s transition and edge clamping
- 20s planning -> 5s resolution -> 5.0s reward cadence, 90s deadline, max 3 turns
- Audience accounting: authenticated account roster, K=2 squads, 60% quorum, ties=abstain
- Human-origin hazard commitment (< t=15s), [15, 20s) warning, clear_lane, bounded slowdown
- Fictional Hype rewards, exact rational shares, delivery settlement, single collision halving
- Diegetic booths: Twitch Moderation Forcefield, Codex Live Hotfix, AWS/IVS Scale Boost
- Bullet-Time Matrix Freeze presentation alignment
- Adaptive audio state machine (crisis, bullet_time, solution, victory, wipe)
- Total ordering: deadline -> phase_close -> pause_request -> sequence_commands -> effects
"""

import copy
from fractions import Fraction
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple, TypedDict

from coordination.canonical_commands import make_command, validate_command
from coordination.content_cache import (
    bytes_hash,
    canonical_bytes,
    canonical_hash,
    detached,
    require_hash,
    validate_json,
)
from coordination.state_transport import apply_diff, state_diff
from .deterministic_kernel import (
    advance_tick as kernel_advance_tick,
    evaluate_scenario_properties,
    get_district_for_progress,
    hazard_warning_active,
    is_delivery_before_deadline,
    BASE_SPEED,
    COLLISION_SLOWDOWN_TICKS,
    DISTRICTS,
    GENERAL_INPUT_CLOSE_TICKS,
    HAZARD_ACTIVE_TICKS,
    HAZARD_ADMISSION_CLOSE_TICKS,
    HZ,
    MATCH_DEADLINE_TICKS,
    MAX_TURNS,
    PERMITTED_HOTFIX_FIELDS,
    PLANNING_TICKS,
    RESOLUTION_TICKS,
    REWARD_TICKS,
    TICK_DURATION_SEC,
    TRANSITION_TICKS,
    TURN_TICKS,
)

TICKS_PER_SECOND = HZ
SAFE_PHASE_BOUNDARY_TURN_TICKS = (0, PLANNING_TICKS, PLANNING_TICKS + RESOLUTION_TICKS)
TRUSTED_HOTFIX_KEYS = ("TRUSTED_CODEX_KEY", "CODEX_BOOTH_TRUSTED_V1")


class ScenarioContract(TypedDict, total=False):
    scenario_id: str
    category: str
    description: str
    seed: int
    initial_lane: int
    base_speed_override: Optional[float]
    initial_progress: float
    initial_tick: int
    initial_roster: List[str]
    scheduled_commands: List[Dict[str, Any]]
    steps_to_run: Any
    features_exercised: List[str]
    invariants_tested: List[str]
    dependencies: List[str]
    expected_oracle: Dict[str, Any]
    contract_hash: str


def get_district_for_progress(progress: float) -> str:
    for d in DISTRICTS:
        if d["min_p"] <= progress < d["max_p"]:
            return d["name"]
    return DISTRICTS[-1]["name"]


class FullGameSimulator:
    def __init__(
        self,
        seed: int = 42,
        initial_lane: int = 1,
        *,
        initial_roster: Optional[List[str]] = None,
        base_speed_override: Optional[float] = None,
        initial_progress: float = 0.0,
        initial_tick: int = 0,
    ):
        self.seed = seed
        self.tick = int(initial_tick)
        if self.tick <= 0:
            self.turn = 1
            self.phase = "planning"
        else:
            self.turn = min(MAX_TURNS, (self.tick // TURN_TICKS) + 1)
            turn_t = self.tick % TURN_TICKS
            if turn_t < PLANNING_TICKS:
                self.phase = "planning"
            elif turn_t < PLANNING_TICKS + RESOLUTION_TICKS:
                self.phase = "resolution"
            else:
                self.phase = "reward"
        self.status = "racing"   # racing, delivered, wiped
        self.is_paused = False
        self.execution_mode = "live_fixture"  # "live_fixture" or "offline_fixture"

        # Avatar state
        self.lane = initial_lane  # discrete lane: 0 (left), 1 (center), 2 (right)
        self.lateral_pos = float(initial_lane)
        self.transition_remaining_ticks = 0
        self.transition_start_lane = initial_lane
        self.transition_target_lane = initial_lane

        # Forward movement
        self.progress = float(initial_progress)
        self.base_speed = float(base_speed_override) if base_speed_override is not None else BASE_SPEED
        self.speed_multiplier = 1.0
        self.slowdown_ticks_remaining = 0
        self.turn_slowdown_ticks = 0
        self.match_slowdown_ticks = 0
        self.speed_boost_ticks_remaining = 0

        # Roster & Audience
        self.frozen_roster: List[str] = []
        self.pending_joins: Set[str] = set(initial_roster or [])
        self.pending_leaves: Set[str] = set()
        self.counter_votes: Dict[str, str] = {}  # account_id -> counter_id
        self.eligible_audience: Set[str] = set()  # accounts with >=1 accepted counter vote in match
        self.squad_assignments: Dict[str, int] = {}  # account_id -> squad index (0 or 1)

        # Hazards & Bounty
        self.committed_hazard: Optional[Dict[str, Any]] = None  # for current turn
        self.hazard_countered = False
        self.warning_active = False
        self.obstacle_active = False
        self.collisions_in_turn = 0
        self.collisions_total = 0
        self.collision_halved_settlement = False
        self.pool = 0  # Human-only Hype pool (cap 60)
        self.synthetic_fixture_pool = 0  # Isolated synthetic fixture Hype counter (cap 60, never paid out)
        self.committed_hazard_ids: Set[str] = set()

        # Booths & Effects
        self.twitch_forcefield_active = False
        self.hotfix_rules: Dict[str, Any] = {
            "slowdown_fraction": 0.20,
            "slowdown_duration_ticks": COLLISION_SLOWDOWN_TICKS,
        }
        self.previous_hotfix_rules: Dict[str, Any] = copy.deepcopy(self.hotfix_rules)
        self.applied_hotfix_version = 0
        self.pending_hotfix: Optional[Dict[str, Any]] = None
        self.ivs_scale_boost_active = False

        # Presentation & Audio
        self.bullet_time = {"active": False, "freeze_tick": None, "factor": 1.0}
        self.audio_state = "solution"  # crisis, bullet_time, solution, victory, wipe
        self.booths_visited: Set[str] = set()

        # Telemetry & History
        self.command_history: List[Dict[str, Any]] = []
        self.boundary_hashes: Dict[str, str] = {}
        self.events: List[Dict[str, Any]] = []
        self.terminal_settlement: Optional[Dict[str, Any]] = None

        self._freeze_roster()
        init_digest = self._record_boundary_hash("init")
        if self.tick != 0:
            self.boundary_hashes["tick_0_init"] = init_digest
        self.initial_state = self.get_canonical_state()
        self._last_traced_state = copy.deepcopy(self.initial_state)
        self._last_traced_hash = init_digest
        init_delta = state_diff(self._last_traced_state, self._last_traced_state)
        self._trace_deltas: List[Dict[str, Any]] = [
            {
                "tick": self.tick,
                "trigger": "init",
                "event_kind": "init",
                "delta": init_delta,
                "state_hash": init_digest,
            }
        ]

    @property
    def turn_tick(self) -> int:
        return self.tick % TURN_TICKS

    @property
    def trace_deltas(self) -> List[Dict[str, Any]]:
        curr_state = self.get_canonical_state()
        curr_hash = canonical_hash(curr_state)
        if curr_hash != self._last_traced_hash:
            self._record_trace_delta("tick_advance", "tick_advance", curr_state=curr_state)
        return self._trace_deltas

    @trace_deltas.setter
    def trace_deltas(self, value: List[Dict[str, Any]]):
        self._trace_deltas = list(value)

    def _record_trace_delta(
        self,
        trigger: str,
        event_kind: Optional[str] = None,
        *,
        curr_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if curr_state is None:
            curr_state = self.get_canonical_state()
        delta = state_diff(self._last_traced_state, curr_state)
        entry = {
            "tick": self.tick,
            "trigger": trigger,
            "event_kind": event_kind or trigger,
            "delta": delta,
            "state_hash": delta["result_hash"],
        }
        self._trace_deltas.append(entry)
        self._last_traced_state = curr_state
        self._last_traced_hash = delta["result_hash"]
        return entry

    def finalize_trace(self) -> Dict[str, Any]:
        """Record final boundary hash and scenario completion delta."""
        digest = self._record_boundary_hash("final")
        curr_state = self.get_canonical_state()
        if (
            not self._trace_deltas
            or self._last_traced_hash != digest
            or self._trace_deltas[-1]["trigger"] != "scenario_complete"
        ):
            return self._record_trace_delta("scenario_complete", "scenario_complete", curr_state=curr_state)
        return self._trace_deltas[-1]

    def _freeze_roster(self):
        # Apply pending joins/leaves
        current_set = set(self.frozen_roster)
        current_set.update(self.pending_joins)
        current_set.difference_update(self.pending_leaves)
        self.pending_joins.clear()
        self.pending_leaves.clear()
        # Stable sort and alternate squad assignment (K=2)
        self.frozen_roster = sorted(current_set)
        self.squad_assignments = {
            acct: idx % 2 for idx, acct in enumerate(self.frozen_roster)
        }
        self.counter_votes = {}

    def set_roster(self, accounts: List[str]):
        """Set initial eligible accounts before turn starts."""
        self.pending_joins.update(accounts)
        self._freeze_roster()
        if hasattr(self, "_trace_deltas"):
            self._record_trace_delta("set_roster", "set_roster")

    def register_account(self, account_id: str):
        if self.phase == "planning":
            # Joins take effect next turn
            self.pending_joins.add(account_id)
        else:
            self.pending_joins.add(account_id)

    def _record_boundary_hash(self, label: str):
        state = self.get_canonical_state()
        digest = canonical_hash(state)
        self.boundary_hashes[f"tick_{self.tick}_{label}"] = digest
        return digest

    def _finish_command(self, cmd: Dict[str, Any], status: str, *, valid_envelope: bool = True) -> str:
        kind = cmd.get("kind", "invalid_command") if isinstance(cmd, dict) else "invalid_command"
        curr_state = self.get_canonical_state()
        trace_entry = self._record_trace_delta(
            f"command:{kind}:{status}",
            kind if valid_envelope else "command_rejected",
            curr_state=curr_state,
        )
        self.command_history.append(
            {
                "cmd": copy.deepcopy(cmd) if isinstance(cmd, dict) else {"raw": str(cmd)},
                "status": status,
                "tick": self.tick,
                "valid_envelope": valid_envelope,
                "state_hash": trace_entry["state_hash"],
            }
        )
        return status

    def submit_command(self, cmd: Dict[str, Any]) -> str:
        """Submit and validate a canonical command. Return status: applied, expired, rejected, duplicate."""
        try:
            cmd = validate_command(cmd)
        except Exception:
            return self._finish_command(cmd, "rejected", valid_envelope=False)

        if self.status != "racing":
            return self._finish_command(cmd, "rejected")

        if self.is_paused and cmd["kind"] != "operator.pause":
            return self._finish_command(cmd, "rejected")

        kind = cmd["kind"]
        payload = cmd["payload"]
        actor_id = cmd["actor_id"]
        turn_t = self.turn_tick

        if kind == "operator.pause":
            pause_val = payload.get("state", True)
            if type(pause_val) is not bool or self.tick >= MATCH_DEADLINE_TICKS:
                # Pause cannot suspend a reached deadline
                return self._finish_command(cmd, "rejected")
            self.is_paused = pause_val
            return self._finish_command(cmd, "applied")

        if kind == "operator.failover":
            # D-06: Stage-operator failover valid only at safe phase boundaries
            if cmd["provenance"] == "bot" or payload.get("automatic") is True:
                return self._finish_command(cmd, "rejected")
            if turn_t not in SAFE_PHASE_BOUNDARY_TURN_TICKS:
                return self._finish_command(cmd, "rejected")
            self.execution_mode = "offline_fixture"
            return self._finish_command(cmd, "applied")

        if kind == "operator.recover":
            # D-06: Recovery valid only at safe phase boundary with matching canonical state hash
            if cmd["provenance"] == "bot":
                return self._finish_command(cmd, "rejected")
            if turn_t not in SAFE_PHASE_BOUNDARY_TURN_TICKS:
                return self._finish_command(cmd, "rejected")
            if payload.get("health_ok", True) is not True:
                return self._finish_command(cmd, "rejected")
            current_hash = canonical_hash(self.get_canonical_state())
            if payload.get("expected_state_hash") != current_hash:
                return self._finish_command(cmd, "rejected")
            if "expected_tick" in payload and payload["expected_tick"] != self.tick:
                return self._finish_command(cmd, "rejected")
            if "expected_turn" in payload and payload["expected_turn"] != self.turn:
                return self._finish_command(cmd, "rejected")
            if "expected_phase" in payload and payload["expected_phase"] != self.phase:
                return self._finish_command(cmd, "rejected")
            self.execution_mode = "live_fixture"
            return self._finish_command(cmd, "applied")

        if kind == "streamer.steer":
            # Steering active in planning, resolution, reward until terminal state
            if self.status != "racing":
                return self._finish_command(cmd, "rejected")
            direction = payload.get("direction")
            if direction not in ("left", "right", "cancel"):
                return self._finish_command(cmd, "rejected")
            if direction == "cancel":
                # Opposite directions canceled
                return self._finish_command(cmd, "applied")

            # Check if transition already in progress
            if self.transition_remaining_ticks > 0:
                # Input during transition ignored/rejected
                return self._finish_command(cmd, "rejected")

            target = self.lane - 1 if direction == "left" else self.lane + 1
            if target < 0 or target > 2:
                # Clamped to edges
                return self._finish_command(cmd, "rejected")

            self.transition_start_lane = self.lane
            self.transition_target_lane = target
            self.transition_remaining_ticks = TRANSITION_TICKS
            return self._finish_command(cmd, "applied")

        elif kind == "hazard.propose":
            # AUDIT-03 / INV-BOT-ISOLATION: bot hazard proposals are always rejected
            if cmd["provenance"] == "bot":
                return self._finish_command(cmd, "rejected")

            # Allowed strictly in half-open interval [0, 15.000s) of planning phase
            if self.phase != "planning" or turn_t >= HAZARD_ADMISSION_CLOSE_TICKS:
                return self._finish_command(cmd, "expired")

            hazard_id = payload.get("hazard_id")
            if not hazard_id or type(hazard_id) is not str or cmd["provenance"] not in ("human", "fixture"):
                return self._finish_command(cmd, "rejected")

            # Max 1 hazard per turn
            if self.committed_hazard is not None:
                if self.committed_hazard["hazard_id"] == hazard_id:
                    return self._finish_command(cmd, "duplicate")
                return self._finish_command(cmd, "rejected")

            if hazard_id in self.committed_hazard_ids:
                return self._finish_command(cmd, "duplicate")

            # Commit hazard
            self.committed_hazard = {
                "hazard_id": hazard_id,
                "kind": payload.get("kind", "blocked_demo_lane"),
                "lane": payload.get("lane", 1),
                "committed_tick": self.tick,
                "actor_id": actor_id,
                "provenance": cmd["provenance"],
            }
            self.committed_hazard_ids.add(hazard_id)
            # AUDIT-03: Only human-origin hazard increments live participant pool; fixture increments synthetic_fixture_pool
            if cmd["provenance"] == "human":
                self.pool = min(60, self.pool + 20)
            elif cmd["provenance"] == "fixture":
                self.synthetic_fixture_pool = min(60, self.synthetic_fixture_pool + 20)

            return self._finish_command(cmd, "applied")

        elif kind == "viewer.counter":
            # Bots and fixtures cannot cast human quorum votes or earn live audience share
            if cmd["provenance"] != "human":
                return self._finish_command(cmd, "rejected")

            # Allowed strictly in half-open interval [0, 20.000s) of planning phase
            if self.phase != "planning" or turn_t >= GENERAL_INPUT_CLOSE_TICKS:
                return self._finish_command(cmd, "expired")

            # Must bind to committed hazard ID
            hazard_id = payload.get("hazard_id")
            if not self.committed_hazard or self.committed_hazard["hazard_id"] != hazard_id:
                return self._finish_command(cmd, "rejected")

            # Check account eligibility
            if actor_id not in self.frozen_roster:
                return self._finish_command(cmd, "rejected")

            # Atomic influence: max 1 influence per subject per turn
            if actor_id in self.counter_votes:
                return self._finish_command(cmd, "duplicate")

            self.counter_votes[actor_id] = payload.get("counter", "clear_lane")
            self.eligible_audience.add(actor_id)
            return self._finish_command(cmd, "applied")

        elif kind == "booth.hotfix":
            # D-07: Data/rules only patch proposal with signature, version, expiry, and 2-key allowlist
            patch_data = payload.get("patch_data")
            signature = payload.get("signature")
            if signature not in TRUSTED_HOTFIX_KEYS:
                return self._finish_command(cmd, "rejected")
            if type(patch_data) is not dict or not patch_data:
                return self._finish_command(cmd, "rejected")
            if not set(patch_data.keys()).issubset(PERMITTED_HOTFIX_FIELDS):
                return self._finish_command(cmd, "rejected")

            patch_version = payload.get("patch_version", 1 if "patch_version" not in payload else -1)
            if type(patch_version) is not int or patch_version <= self.applied_hotfix_version:
                return self._finish_command(cmd, "rejected")

            expiry_tick = payload.get("expiry_tick", MATCH_DEADLINE_TICKS if "expiry_tick" not in payload else -1)
            if type(expiry_tick) is not int or expiry_tick < self.tick:
                return self._finish_command(cmd, "rejected")

            if "slowdown_fraction" in patch_data:
                slowdown_frac = patch_data["slowdown_fraction"]
                if type(slowdown_frac) not in (int, float) or not (0.0 <= float(slowdown_frac) <= 0.20):
                    return self._finish_command(cmd, "rejected")
            if "slowdown_duration_ticks" in patch_data:
                slowdown_dur = patch_data["slowdown_duration_ticks"]
                if type(slowdown_dur) is not int or not (0 <= slowdown_dur <= 40):
                    return self._finish_command(cmd, "rejected")

            self.pending_hotfix = copy.deepcopy(patch_data)
            self.applied_hotfix_version = patch_version
            return self._finish_command(cmd, "applied")

        elif kind == "operator.rollback_hotfix":
            # D-07: Turn-boundary hotfix rollback
            if turn_t != 0:
                return self._finish_command(cmd, "rejected")
            self.hotfix_rules = copy.deepcopy(self.previous_hotfix_rules)
            self.pending_hotfix = None
            return self._finish_command(cmd, "applied")

        elif kind == "booth.boost":
            # AWS/IVS scale boost
            duration_ticks = payload.get("duration_ticks", 40)
            if type(duration_ticks) is not int or not (0 <= duration_ticks <= 40):
                return self._finish_command(cmd, "rejected")
            self.speed_boost_ticks_remaining = int(duration_ticks)
            return self._finish_command(cmd, "applied")

        elif kind == "presentation.bullet_time":
            active = payload.get("active", True)
            if type(active) is not bool:
                return self._finish_command(cmd, "rejected")
            factor = payload.get("factor", 0.25)
            if type(factor) not in (int, float) or not (0.0 < float(factor) <= 1.0):
                return self._finish_command(cmd, "rejected")
            self.bullet_time = {
                "active": active,
                "freeze_tick": payload.get("freeze_tick", self.tick),
                "factor": float(factor),
            }
            if active:
                self.audio_state = "bullet_time"
            return self._finish_command(cmd, "applied")

        elif kind == "audience.register":
            account_id = payload.get("account_id")
            if type(account_id) is not str or not account_id.strip():
                return self._finish_command(cmd, "rejected")
            self.register_account(account_id)
            return self._finish_command(cmd, "applied")

        return self._finish_command(cmd, "rejected")

    def _update_phase_boundaries(self):
        turn_t = self.turn_tick
        if turn_t == 0 and self.tick > 0:
            if self.turn >= MAX_TURNS:
                self._handle_wipe("max_turns_exceeded")
                return
            self.turn = self.tick // TURN_TICKS + 1
            self.phase = "planning"
            self.committed_hazard = None
            self.hazard_countered = False
            self.warning_active = False
            self.obstacle_active = False
            self.collisions_in_turn = 0
            self.turn_slowdown_ticks = 0
            self._freeze_roster()
            if self.pending_hotfix:
                self.previous_hotfix_rules = copy.deepcopy(self.hotfix_rules)
                self.hotfix_rules.update(self.pending_hotfix)
                self.pending_hotfix = None
            self._record_boundary_hash(f"turn_{self.turn}_start")
            self._record_trace_delta(f"turn_{self.turn}_start", "phase_boundary")
        elif turn_t == PLANNING_TICKS:
            self.phase = "resolution"
            self.warning_active = False
            self._record_boundary_hash(f"turn_{self.turn}_resolution_start")
            self._record_trace_delta(f"turn_{self.turn}_resolution_start", "phase_boundary")
            self._adjudicate_counter_quorum()
        elif turn_t == PLANNING_TICKS + RESOLUTION_TICKS:
            self.phase = "reward"
            self.obstacle_active = False
            self.warning_active = False
            self._record_boundary_hash(f"turn_{self.turn}_reward_start")
            self._record_trace_delta(f"turn_{self.turn}_reward_start", "phase_boundary")
        else:
            was_warning = self.warning_active
            self.warning_active = hazard_warning_active(self.committed_hazard, self.tick)
            if self.warning_active:
                self.audio_state = "crisis"
                if not was_warning:
                    self._record_trace_delta("warning_window_open", "warning_active")

    def step(self):
        """Advance simulation by exactly one authoritative 20 Hz tick."""
        if self.status != "racing":
            return

        # 1. Total order: Deadline boundary evaluated FIRST at current tick
        if self.tick >= MATCH_DEADLINE_TICKS:
            self._handle_wipe("deadline_reached")
            return

        # Check pause
        if self.is_paused:
            # Paused simulation produces no ticks, clocks frozen
            return

        current_tick = self.tick
        turn_t = self.turn_tick

        # Warning evaluation during planning [15.0s, 20.0s)
        was_warning = self.warning_active
        self.warning_active = hazard_warning_active(self.committed_hazard, self.tick)
        if self.warning_active:
            self.audio_state = "crisis"
            if not was_warning:
                self._record_trace_delta("warning_window_open", "warning_active")

        # Obstacle active during first 3.0s of resolution (ticks 400..460 of turn)
        if self.phase == "resolution":
            rel_res_tick = turn_t - PLANNING_TICKS
            if rel_res_tick < HAZARD_ACTIVE_TICKS and self.committed_hazard and not self.hazard_countered:
                self.obstacle_active = True
            else:
                self.obstacle_active = False
        else:
            self.obstacle_active = False

        # 3. Steering & Lane transition interpolation
        if self.transition_remaining_ticks > 0:
            self.transition_remaining_ticks -= 1
            fraction_done = (TRANSITION_TICKS - self.transition_remaining_ticks) / TRANSITION_TICKS
            self.lateral_pos = self.transition_start_lane + fraction_done * (self.transition_target_lane - self.transition_start_lane)
            if self.transition_remaining_ticks == 0:
                self.lane = self.transition_target_lane
                self.lateral_pos = float(self.lane)

        # 4. Forward speed & progress
        speed = self.base_speed
        if self.slowdown_ticks_remaining > 0:
            speed *= (1.0 - self.hotfix_rules["slowdown_fraction"])
            self.slowdown_ticks_remaining -= 1
            self.turn_slowdown_ticks += 1
            self.match_slowdown_ticks += 1

        if self.speed_boost_ticks_remaining > 0:
            speed *= 1.10
            self.speed_boost_ticks_remaining -= 1

        delta_progress = speed * float(TICK_DURATION_SEC)
        self.progress = min(100.0, self.progress + delta_progress)

        # 5. Admitted effect order:
        # a. clear_lane removal (already handled at resolution start)
        # b. collision adjudication
        if self.obstacle_active and abs(self.lateral_pos - 1.0) < 0.4:
            # Avatar in center lane overlapping obstacle!
            if self.collisions_in_turn == 0:
                self.collisions_in_turn += 1
                self.collisions_total += 1
                self.collision_halved_settlement = True
                self.slowdown_ticks_remaining = self.hotfix_rules["slowdown_duration_ticks"]
                self.audio_state = "crisis"
                self.events.append({"tick": current_tick, "kind": "collision", "lane": 1, "turn": self.turn})
                self._record_trace_delta("event:collision", "collision")

        # Booth triggers
        self._check_booth_triggers()

        # Advance tick clock
        self.tick += 1

        # Check delivery vs deadline at new tick
        if self.progress >= 100.0:
            if is_delivery_before_deadline(current_tick, self.tick):
                # Delivered strictly before deadline!
                self._handle_delivery()
                return
            else:
                # Delivery reached at or after deadline (e.g. at tick 1800):
                # Deadline wipe wins, settlement is zero!
                self._handle_wipe("deadline_equality_wipe")
                return

        # Check deadline at tick boundary
        if self.tick >= MATCH_DEADLINE_TICKS:
            self._handle_wipe("deadline_reached")
            return

        # Update phase boundaries for new tick
        self._update_phase_boundaries()

    def _adjudicate_counter_quorum(self):
        """Evaluate 60% frozen-roster quorum for clear_lane."""
        if not self.committed_hazard:
            return

        N = len(self.frozen_roster)
        if N == 0:
            # Abstain wins
            self.hazard_countered = False
            self.events.append({"tick": self.tick, "kind": "clear_lane_failed", "votes": 0, "threshold": 1})
            self._record_trace_delta("event:clear_lane_failed", "clear_lane_failed")
            return

        # Integer threshold: (3*N + 4) // 5 = ceil(0.60 * N)
        threshold = (3 * N + 4) // 5
        votes_count = sum(1 for v in self.counter_votes.values() if v == "clear_lane")

        if votes_count >= threshold and votes_count >= 1:
            self.hazard_countered = True
            self.obstacle_active = False
            self.audio_state = "solution"
            self.events.append({"tick": self.tick, "kind": "clear_lane_success", "votes": votes_count, "threshold": threshold})
            self._record_trace_delta("event:clear_lane_success", "clear_lane_success")
        else:
            self.hazard_countered = False
            self.events.append({"tick": self.tick, "kind": "clear_lane_failed", "votes": votes_count, "threshold": threshold})
            self._record_trace_delta("event:clear_lane_failed", "clear_lane_failed")

    def _check_booth_triggers(self):
        # District 2: Waterfront/Marina (Twitch Booth at progress 35.0)
        if self.progress >= 35.0 and "twitch_booth" not in self.booths_visited:
            self.booths_visited.add("twitch_booth")
            self.twitch_forcefield_active = True
            self.events.append({"tick": self.tick, "kind": "booth_visited", "booth": "twitch_booth"})
            self._record_trace_delta("event:booth_visited:twitch_booth", "booth_visited")

        # District 3: Gaslamp Quarter (Codex Live Hotfix Booth at progress 60.0)
        if self.progress >= 60.0 and "codex_booth" not in self.booths_visited:
            self.booths_visited.add("codex_booth")
            self.events.append({"tick": self.tick, "kind": "booth_visited", "booth": "codex_booth"})
            self._record_trace_delta("event:booth_visited:codex_booth", "booth_visited")

        # District 4: Convention Center (AWS/IVS Booth at progress 80.0)
        if self.progress >= 80.0 and "aws_booth" not in self.booths_visited:
            self.booths_visited.add("aws_booth")
            self.ivs_scale_boost_active = True
            self.events.append({"tick": self.tick, "kind": "booth_visited", "booth": "aws_booth"})
            self._record_trace_delta("event:booth_visited:aws_booth", "booth_visited")

    def _handle_delivery(self):
        """Execute one final delivery settlement immediately ending active simulation."""
        self.status = "delivered"
        self.phase = "finished"
        self.audio_state = "victory"

        total_pool = self.pool
        if self.collision_halved_settlement:
            total_pool = total_pool // 2

        streamer_share = total_pool // 2
        audience_share_total = total_pool - streamer_share

        eligible_count = len(self.eligible_audience)
        if eligible_count > 0:
            per_voter = Fraction(audience_share_total, eligible_count)
            audience_allocated = audience_share_total
            audience_withheld = 0
        else:
            per_voter = Fraction(0, 1)
            audience_allocated = 0
            audience_withheld = audience_share_total

        self.terminal_settlement = {
            "status": "delivered",
            "tick": self.tick,
            "total_hype": total_pool,
            "original_pool": self.pool,
            "synthetic_fixture_hype_illustrated": self.synthetic_fixture_pool,
            "live_participant_minted_from_fixture": False,
            "live_participant_minted": False,
            "collision_halved": self.collision_halved_settlement,
            "streamer_share": streamer_share,
            "audience_share_total": audience_allocated,
            "audience_withheld": audience_withheld,
            "eligible_voters_count": eligible_count,
            "per_voter_rational": str(per_voter),
            "settled_once": True,
        }
        self.events.append({"tick": self.tick, "kind": "delivery_settlement", "settlement": self.terminal_settlement})
        self._record_boundary_hash("terminal_delivery")
        self._record_trace_delta("terminal:delivery_settlement", "delivery_settlement")

    def _handle_wipe(self, reason: str):
        """Execute wipe settlement: 0 payout, match reset."""
        self.status = "wiped"
        self.phase = "finished"
        self.audio_state = "wipe"
        self.terminal_settlement = {
            "status": "wiped",
            "reason": reason,
            "tick": self.tick,
            "total_hype": 0,
            "original_pool": self.pool,
            "synthetic_fixture_hype_illustrated": self.synthetic_fixture_pool,
            "live_participant_minted_from_fixture": False,
            "live_participant_minted": False,
            "streamer_share": 0,
            "audience_share_total": 0,
            "audience_withheld": self.pool,
            "settled_once": True,
        }
        self.events.append({"tick": self.tick, "kind": "wipe", "reason": reason})
        self._record_boundary_hash(f"terminal_wipe_{reason}")
        self._record_trace_delta(f"terminal:wipe:{reason}", "wipe")

    def get_canonical_state(self) -> Dict[str, Any]:
        """Return a clean detached JSON dictionary of authoritative state."""
        state = {
            "schema_version": 1,
            "tick": self.tick,
            "turn": self.turn,
            "phase": self.phase,
            "status": self.status,
            "is_paused": self.is_paused,
            "avatar": {
                "lane": self.lane,
                "lateral_pos": round(self.lateral_pos, 4),
                "transition_remaining_ticks": self.transition_remaining_ticks,
            },
            "movement": {
                "progress": round(self.progress, 4),
                "district": get_district_for_progress(self.progress),
                "slowdown_ticks_remaining": self.slowdown_ticks_remaining,
                "turn_slowdown_ticks": self.turn_slowdown_ticks,
                "match_slowdown_ticks": self.match_slowdown_ticks,
            },
            "bounty": {
                "pool": self.pool,
                "synthetic_fixture_pool": self.synthetic_fixture_pool,
                "collisions_total": self.collisions_total,
                "collision_halved": self.collision_halved_settlement,
            },
            "hazard": {
                "committed": self.committed_hazard["hazard_id"] if self.committed_hazard else None,
                "warning_active": self.warning_active,
                "obstacle_active": self.obstacle_active,
                "hazard_countered": self.hazard_countered,
            },
            "audience": {
                "roster_size": len(self.frozen_roster),
                "counter_votes_count": len(self.counter_votes),
                "eligible_voters_count": len(self.eligible_audience),
            },
            "booths": sorted(list(self.booths_visited)),
            "audio_state": self.audio_state,
        }
        validate_json(state)
        return detached(state)


REQUIRED_SCENARIO_CONTRACT_FIELDS = {
    "scenario_id",
    "category",
    "seed",
    "initial_lane",
    "initial_roster",
    "scheduled_commands",
    "steps_to_run",
    "features_exercised",
    "invariants_tested",
    "expected_oracle",
}


def validate_scenario_contract(contract: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a pre-execution frozen ScenarioContract and reject generic/circular oracles."""
    if type(contract) is not dict:
        raise ValueError("ScenarioContract must be a JSON object")
    missing = REQUIRED_SCENARIO_CONTRACT_FIELDS - set(contract.keys())
    if missing:
        raise ValueError(f"ScenarioContract missing required fields: {sorted(missing)}")
    if type(contract["scenario_id"]) is not str or not contract["scenario_id"].strip():
        raise ValueError("scenario_id must be a non-empty string")
    if type(contract["category"]) is not str or not contract["category"].strip():
        raise ValueError("category must be a non-empty string")
    if type(contract["seed"]) is not int:
        raise ValueError("seed must be an integer")
    if type(contract["initial_lane"]) is not int or contract["initial_lane"] not in (0, 1, 2):
        raise ValueError("initial_lane must be 0, 1, or 2")
    if type(contract["initial_roster"]) is not list or any(type(x) is not str for x in contract["initial_roster"]):
        raise ValueError("initial_roster must be a list of strings")
    if type(contract["scheduled_commands"]) is not list:
        raise ValueError("scheduled_commands must be a list")
    if type(contract["features_exercised"]) is not list or any(type(x) is not str for x in contract["features_exercised"]):
        raise ValueError("features_exercised must be a list of strings")
    if type(contract["invariants_tested"]) is not list or any(type(x) is not str for x in contract["invariants_tested"]):
        raise ValueError("invariants_tested must be a list of strings")

    oracle = contract.get("expected_oracle")
    if type(oracle) is not dict or not oracle:
        raise ValueError("expected_oracle must be a concrete non-empty dict, never a generic string or empty")
    if oracle.get("expected_final_status") not in ("racing", "delivered", "wiped"):
        raise ValueError("expected_oracle.expected_final_status must be racing, delivered, or wiped")

    body = {k: v for k, v in contract.items() if k != "contract_hash"}
    validate_json(body)
    computed_hash = canonical_hash(body)
    if "contract_hash" in contract and contract["contract_hash"] is not None:
        require_hash(contract["contract_hash"])
        if contract["contract_hash"] != computed_hash:
            raise ValueError("ScenarioContract contract_hash mismatch")
    return detached({**body, "contract_hash": computed_hash})


def freeze_scenario_matrix(
    contracts: List[Dict[str, Any]],
    matrix_path: Optional[Any] = None,
) -> Dict[str, Any]:
    """Validate and freeze scenario contracts before tick 0."""
    if type(contracts) is not list or not contracts:
        raise ValueError("Scenario matrix requires a non-empty list of ScenarioContracts")
    seen_ids: Set[str] = set()
    frozen_list: List[Dict[str, Any]] = []
    for item in contracts:
        frozen = validate_scenario_contract(item)
        scen_id = frozen["scenario_id"]
        if scen_id in seen_ids:
            raise ValueError(f"Duplicate scenario_id in matrix: {scen_id}")
        seen_ids.add(scen_id)
        frozen_list.append(frozen)

    if matrix_path is not None:
        from pathlib import Path

        p = Path(matrix_path)
        raw = (json.dumps(frozen_list, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with open(p, "xb") as fh:
            fh.write(raw)
        matrix_sha256 = bytes_hash(p.read_bytes())
    else:
        matrix_sha256 = canonical_hash(frozen_list)

    return {
        "contracts": frozen_list,
        "matrix_sha256": matrix_sha256,
        "count": len(frozen_list),
    }


def _normalize_scheduled_command(entry: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    if type(entry) is not dict:
        raise ValueError("Scheduled command entry must be a dict")
    if "raw_command" in entry:
        submit_tick = int(entry.get("tick", entry.get("submit_at_tick", 0)))
        return submit_tick, entry["raw_command"]
    if "cmd" in entry and type(entry["cmd"]) is dict:
        inner = entry["cmd"]
        submit_tick = int(entry.get("tick", entry.get("submit_at_tick", inner.get("logical_tick", 0))))
        if "command_id" in inner:
            return submit_tick, validate_command(inner)
        return (
            submit_tick,
            make_command(
                inner["kind"],
                inner["actor_id"],
                inner["provenance"],
                int(inner.get("logical_tick", submit_tick)),
                int(inner["sequence"]),
                inner.get("payload", {}),
            ),
        )
    if "command_id" in entry:
        cmd = validate_command(entry)
        submit_tick = int(entry.get("submit_at_tick", cmd["logical_tick"]))
        return submit_tick, cmd

    submit_tick = int(entry.get("submit_at_tick", entry.get("tick", entry.get("logical_tick", 0))))
    logical_tick = int(entry.get("logical_tick", submit_tick))
    cmd = make_command(
        entry["kind"],
        entry["actor_id"],
        entry["provenance"],
        logical_tick,
        int(entry["sequence"]),
        entry.get("payload", {}),
    )
    return submit_tick, cmd


def execute_frozen_scenario(
    contract: Dict[str, Any],
    artifact_dir: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute a pre-frozen ScenarioContract deterministically and evaluate independent oracles."""
    frozen = validate_scenario_contract(contract)
    contract_hash = frozen["contract_hash"]

    sim = FullGameSimulator(
        seed=frozen["seed"],
        initial_lane=frozen["initial_lane"],
        initial_roster=frozen["initial_roster"],
        base_speed_override=frozen.get("base_speed_override"),
        initial_progress=float(frozen.get("initial_progress", 0.0)),
        initial_tick=int(frozen.get("initial_tick", 0)),
    )

    initial_state = copy.deepcopy(sim.initial_state)
    initial_state_hash = canonical_hash(initial_state)

    commands_by_tick: Dict[int, List[Dict[str, Any]]] = {}
    for item in frozen["scheduled_commands"]:
        submit_tick, cmd_obj = _normalize_scheduled_command(item)
        commands_by_tick.setdefault(submit_tick, []).append(cmd_obj)

    steps_spec = frozen["steps_to_run"]
    if steps_spec == "until_terminal_or_deadline":
        max_steps = MATCH_DEADLINE_TICKS + 1
        stop_on_terminal = True
    else:
        if type(steps_spec) is not int or steps_spec < 0:
            raise ValueError("steps_to_run must be a non-negative integer or 'until_terminal_or_deadline'")
        max_steps = steps_spec
        stop_on_terminal = False

    # Submit commands scheduled at initial tick before stepping
    for cmd_obj in commands_by_tick.pop(sim.tick, []):
        sim.submit_command(cmd_obj)

    for _ in range(max_steps):
        if stop_on_terminal and sim.status != "racing":
            break
        prev_tick = sim.tick
        sim.step()
        if sim.tick != prev_tick:
            for cmd_obj in commands_by_tick.pop(sim.tick, []):
                sim.submit_command(cmd_obj)
        else:
            # If paused or terminal at same tick, still process any remaining commands for this tick
            for cmd_obj in commands_by_tick.pop(sim.tick, []):
                sim.submit_command(cmd_obj)

    sim.finalize_trace()
    final_state = sim.get_canonical_state()
    final_state_hash = canonical_hash(final_state)
    trace_deltas = copy.deepcopy(sim.trace_deltas)
    command_log = copy.deepcopy(sim.command_history)
    boundary_hashes = copy.deepcopy(sim.boundary_hashes)

    execution_bundle: Dict[str, Any] = {
        "scenario_id": frozen["scenario_id"],
        "category": frozen["category"],
        "contract_hash": contract_hash,
        "seed": sim.seed,
        "initial_lane": frozen["initial_lane"],
        "initial_roster": list(frozen["initial_roster"]),
        "base_speed_override": frozen.get("base_speed_override"),
        "initial_progress": float(frozen.get("initial_progress", 0.0)),
        "initial_tick": int(frozen.get("initial_tick", 0)),
        "steps_to_run": steps_spec,
        "initial_state": initial_state,
        "initial_state_hash": initial_state_hash,
        "final_state": final_state,
        "final_state_hash": final_state_hash,
        "final_tick": sim.tick,
        "final_turn": sim.turn,
        "final_phase": sim.phase,
        "final_status": sim.status,
        "execution_mode": sim.execution_mode,
        "pool": sim.pool,
        "synthetic_fixture_pool": sim.synthetic_fixture_pool,
        "collisions_total": sim.collisions_total,
        "terminal_settlement": copy.deepcopy(sim.terminal_settlement),
        "hotfix_rules": copy.deepcopy(sim.hotfix_rules),
        "applied_hotfix_version": sim.applied_hotfix_version,
        "booths_visited": sorted(list(sim.booths_visited)),
        "events": copy.deepcopy(sim.events),
        "command_log": command_log,
        "trace_deltas": trace_deltas,
        "boundary_hashes": boundary_hashes,
        "features_exercised": list(frozen["features_exercised"]),
        "invariants_tested": list(frozen["invariants_tested"]),
    }

    oracle_evaluation = evaluate_independent_oracles(frozen, execution_bundle)
    execution_bundle["oracle_evaluation"] = oracle_evaluation
    execution_bundle["passed"] = bool(oracle_evaluation["passed"])
    execution_bundle["verdict"] = "passed" if execution_bundle["passed"] else "failed"

    if artifact_dir is not None:
        from pathlib import Path

        out_dir = Path(artifact_dir)
        scen_id = frozen["scenario_id"]
        cmd_payload = {
            "scenario_id": scen_id,
            "contract_hash": contract_hash,
            "seed": sim.seed,
            "initial_lane": frozen["initial_lane"],
            "initial_roster": list(frozen["initial_roster"]),
            "initial_state_hash": initial_state_hash,
            "final_state_hash": final_state_hash,
            "commands": command_log,
        }
        hash_payload = {
            "scenario_id": scen_id,
            "contract_hash": contract_hash,
            "initial_state_hash": initial_state_hash,
            "final_state_hash": final_state_hash,
            "boundary_hashes": boundary_hashes,
            "oracle_evaluation": oracle_evaluation,
        }
        cmd_path = out_dir / "commands" / f"{scen_id}.json"
        trace_path = out_dir / "traces" / f"{scen_id}.jsonl"
        hash_path = out_dir / "state-hashes" / f"{scen_id}.json"
        with open(cmd_path, "xb") as fh:
            fh.write((json.dumps(cmd_payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        with open(trace_path, "xb") as fh:
            lines = [json.dumps(entry, sort_keys=True) for entry in trace_deltas]
            fh.write(("\n".join(lines) + "\n").encode("utf-8"))
        with open(hash_path, "xb") as fh:
            fh.write((json.dumps(hash_payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))

    return execution_bundle


def replay_command_stream(
    seed: int,
    initial_lane: int,
    initial_roster: List[str],
    command_log: List[Dict[str, Any]],
    steps_to_run: Any,
    base_speed_override: Optional[float] = None,
    *,
    expected_final_state_hash: Optional[str] = None,
    initial_progress: float = 0.0,
    initial_tick: int = 0,
) -> Dict[str, Any]:
    """Deterministically replay a command stream and verify command envelopes, statuses, and state hashes."""
    if type(command_log) is not list:
        raise ValueError("command_log must be a list")

    sim = FullGameSimulator(
        seed=seed,
        initial_lane=initial_lane,
        initial_roster=initial_roster,
        base_speed_override=base_speed_override,
        initial_progress=initial_progress,
        initial_tick=initial_tick,
    )
    initial_state = copy.deepcopy(sim.initial_state)
    initial_state_hash = canonical_hash(initial_state)

    scheduled: Dict[int, List[Tuple[Dict[str, Any], Optional[str], Optional[str], bool]]] = {}
    for item in command_log:
        if type(item) is not dict:
            raise ValueError("Malformed command log entry")
        if "cmd" in item:
            raw_cmd = item["cmd"]
            valid_env = bool(item.get("valid_envelope", True))
            expected_status = item.get("status")
            expected_state_hash = item.get("state_hash")
            if valid_env:
                validated_cmd = validate_command(raw_cmd)
                submit_tick = int(item.get("tick", validated_cmd["logical_tick"]))
            else:
                validated_cmd = raw_cmd
                submit_tick = int(item.get("tick", 0))
            scheduled.setdefault(submit_tick, []).append(
                (validated_cmd, expected_status, expected_state_hash, valid_env)
            )
        else:
            validated_cmd = validate_command(item)
            submit_tick = int(validated_cmd["logical_tick"])
            scheduled.setdefault(submit_tick, []).append((validated_cmd, None, None, True))

    if steps_to_run == "until_terminal_or_deadline":
        max_steps = MATCH_DEADLINE_TICKS + 1
        stop_on_terminal = True
    else:
        if type(steps_to_run) is not int or steps_to_run < 0:
            raise ValueError("steps_to_run must be a non-negative integer or 'until_terminal_or_deadline'")
        max_steps = steps_to_run
        stop_on_terminal = False

    def _run_tick_commands(t: int):
        for cmd_obj, exp_status, exp_hash, _ in scheduled.pop(t, []):
            obs_status = sim.submit_command(cmd_obj)
            if exp_status is not None and obs_status != exp_status:
                raise ValueError(
                    f"Replay command status mismatch at tick {t}: expected {exp_status}, got {obs_status}"
                )
            if exp_hash is not None:
                obs_hash = canonical_hash(sim.get_canonical_state())
                if obs_hash != exp_hash:
                    raise ValueError(
                        f"Replay state hash mismatch at tick {t}: expected {exp_hash}, got {obs_hash}"
                    )

    _run_tick_commands(sim.tick)
    for _ in range(max_steps):
        if stop_on_terminal and sim.status != "racing":
            break
        sim.step()
        _run_tick_commands(sim.tick)

    sim.finalize_trace()
    final_state = sim.get_canonical_state()
    final_state_hash = canonical_hash(final_state)
    if expected_final_state_hash is not None:
        require_hash(expected_final_state_hash)
        if final_state_hash != expected_final_state_hash:
            raise ValueError(
                f"Replay final state hash mismatch: expected {expected_final_state_hash}, got {final_state_hash}"
            )

    return {
        "seed": seed,
        "initial_lane": initial_lane,
        "initial_state": initial_state,
        "initial_state_hash": initial_state_hash,
        "final_state": final_state,
        "final_state_hash": final_state_hash,
        "final_tick": sim.tick,
        "final_status": sim.status,
        "pool": sim.pool,
        "synthetic_fixture_pool": sim.synthetic_fixture_pool,
        "command_log": copy.deepcopy(sim.command_history),
        "trace_deltas": copy.deepcopy(sim.trace_deltas),
        "boundary_hashes": copy.deepcopy(sim.boundary_hashes),
        "terminal_settlement": copy.deepcopy(sim.terminal_settlement),
    }


RECOGNIZED_ORACLE_KEYS = {
    "expected_final_status",
    "expected_final_tick",
    "expected_final_tick_range",
    "expected_final_turn",
    "expected_final_phase",
    "expected_lane",
    "expected_pool",
    "expected_synthetic_fixture_pool",
    "expected_collisions_total",
    "expected_collision_halved",
    "expected_hazard_countered",
    "expected_warning_active",
    "expected_obstacle_active",
    "expected_is_paused",
    "expected_execution_mode",
    "expected_roster_size",
    "expected_eligible_voters_count",
    "expected_booths_visited",
    "expected_booths_subset",
    "expected_audio_state",
    "expected_hotfix_rules",
    "expected_applied_hotfix_version",
    "expected_command_statuses",
    "expected_settlement",
    "expected_boundary_labels",
}


def evaluate_independent_oracles(
    contract: Dict[str, Any],
    execution_bundle: Dict[str, Any],
    *extra_args: Any,
) -> Dict[str, Any]:
    """Independently verify contract expectations, state-diff trace continuity, and all invariants."""
    if extra_args:
        # Support 5-argument call: (contract, pre_state, post_state, command_log, trace_log)
        if len(extra_args) != 3:
            raise ValueError("evaluate_independent_oracles accepts (contract, bundle) or (contract, pre, post, cmds, trace)")
        pre_state = execution_bundle
        post_state, cmd_log, trace_log = extra_args
        execution_bundle = {
            "scenario_id": contract.get("scenario_id") if isinstance(contract, dict) else None,
            "initial_state": pre_state,
            "initial_state_hash": canonical_hash(pre_state),
            "final_state": post_state,
            "final_state_hash": canonical_hash(post_state),
            "command_log": cmd_log,
            "trace_deltas": trace_log,
            "boundary_hashes": {},
            "hotfix_rules": {"slowdown_fraction": 0.20, "slowdown_duration_ticks": COLLISION_SLOWDOWN_TICKS},
        }

    failures: List[str] = []
    checks: Dict[str, bool] = {}

    if type(contract) is not dict:
        raise ValueError("contract must be a dict")
    oracle = contract.get("expected_oracle")
    if type(oracle) is not dict or not oracle:
        raise ValueError("expected_oracle must be a concrete non-empty dict")

    final_state = execution_bundle.get("final_state")
    initial_state = execution_bundle.get("initial_state")
    if type(final_state) is not dict or type(initial_state) is not dict:
        raise ValueError("execution_bundle must include initial_state and final_state dicts")

    initial_state_hash = execution_bundle.get("initial_state_hash") or canonical_hash(initial_state)
    final_state_hash = execution_bundle.get("final_state_hash") or canonical_hash(final_state)
    if canonical_hash(initial_state) != initial_state_hash:
        failures.append("initial_state_hash does not match canonical_hash(initial_state)")
    if canonical_hash(final_state) != final_state_hash:
        failures.append("final_state_hash does not match canonical_hash(final_state)")

    # 1. Verify trace_deltas continuity via apply_diff (AUDIT-05)
    trace_deltas = execution_bundle.get("trace_deltas")
    trace_chain_valid = True
    if type(trace_deltas) is not list or len(trace_deltas) == 0:
        trace_chain_valid = False
        failures.append("AUDIT-05: trace_deltas is missing or empty")
    else:
        reconstructed = copy.deepcopy(initial_state)
        if trace_deltas[0].get("delta", {}).get("base_hash") != initial_state_hash:
            trace_chain_valid = False
            failures.append("AUDIT-05: trace_deltas[0].delta.base_hash does not match initial_state_hash")
        for idx, entry in enumerate(trace_deltas):
            if type(entry) is not dict or "delta" not in entry or "state_hash" not in entry:
                trace_chain_valid = False
                failures.append(f"AUDIT-05: malformed trace entry at index {idx}")
                break
            try:
                reconstructed = apply_diff(reconstructed, entry["delta"])
            except Exception as exc:
                trace_chain_valid = False
                failures.append(f"AUDIT-05: apply_diff failed at trace index {idx}: {exc}")
                break
            if entry["state_hash"] != entry["delta"]["result_hash"]:
                trace_chain_valid = False
                failures.append(f"AUDIT-05: trace entry {idx} state_hash != delta.result_hash")
                break
        if trace_chain_valid and canonical_hash(reconstructed) != final_state_hash:
            trace_chain_valid = False
            failures.append(
                f"AUDIT-05: final reconstructed state hash {canonical_hash(reconstructed)} != final_state_hash {final_state_hash}"
            )
    checks["trace_chain_valid"] = trace_chain_valid

    # 2. Independently recompute human vs fixture Hype pool & verify INV-BOT-ISOLATION (AUDIT-03)
    command_log = execution_bundle.get("command_log", [])
    if type(command_log) is not list:
        failures.append("command_log must be a list")
        command_log = []

    human_hazards_applied = 0
    fixture_hazards_applied = 0
    seen_applied_hazard_ids: Set[str] = set()
    bot_isolation_ok = True

    for idx, entry in enumerate(command_log):
        if type(entry) is not dict or "cmd" not in entry or "status" not in entry:
            failures.append(f"Malformed command_log entry at index {idx}")
            continue
        cmd = entry["cmd"]
        status = entry["status"]
        if type(cmd) is not dict:
            continue
        kind = cmd.get("kind")
        prov = cmd.get("provenance")
        payload = cmd.get("payload", {}) if isinstance(cmd.get("payload"), dict) else {}

        if prov == "bot" and kind in ("hazard.propose", "viewer.counter", "operator.failover", "operator.recover"):
            if status == "applied":
                bot_isolation_ok = False
                failures.append(f"INV-BOT-ISOLATION: bot command {kind} at index {idx} was applied")

        if prov == "fixture" and kind == "viewer.counter":
            if status == "applied":
                bot_isolation_ok = False
                failures.append(f"INV-BOT-ISOLATION: fixture viewer.counter at index {idx} was applied")

        if kind == "hazard.propose" and status == "applied":
            h_id = payload.get("hazard_id")
            if h_id in seen_applied_hazard_ids:
                failures.append(f"INV-COMMAND-VAL: duplicate hazard_id {h_id} was applied more than once")
            if type(h_id) is str:
                seen_applied_hazard_ids.add(h_id)
            if prov == "human":
                human_hazards_applied += 1
            elif prov == "fixture":
                fixture_hazards_applied += 1
            else:
                bot_isolation_ok = False
                failures.append(f"INV-BOT-ISOLATION: hazard.propose with provenance {prov} was applied")

    expected_human_pool = min(60, 20 * human_hazards_applied)
    expected_synthetic_pool = min(60, 20 * fixture_hazards_applied)

    bounty = final_state.get("bounty", {})
    observed_pool = bounty.get("pool")
    observed_synthetic_pool = bounty.get("synthetic_fixture_pool", 0)

    if observed_pool != expected_human_pool:
        bot_isolation_ok = False
        failures.append(
            f"INV-BOT-ISOLATION / AUDIT-03: observed live pool {observed_pool} != recomputed human pool {expected_human_pool}"
        )
    if observed_synthetic_pool != expected_synthetic_pool:
        bot_isolation_ok = False
        failures.append(
            f"INV-BOT-ISOLATION / AUDIT-03: observed synthetic_fixture_pool {observed_synthetic_pool} != recomputed fixture pool {expected_synthetic_pool}"
        )
    checks["inv_bot_isolation"] = bot_isolation_ok

    # 3. Verify core safety, turn, settlement, and hotfix invariants
    mov = final_state.get("movement", {})
    safety_caps_ok = (
        mov.get("turn_slowdown_ticks", 0) <= COLLISION_SLOWDOWN_TICKS
        and mov.get("match_slowdown_ticks", 0) <= COLLISION_SLOWDOWN_TICKS * MAX_TURNS
        and mov.get("slowdown_ticks_remaining", 0) <= COLLISION_SLOWDOWN_TICKS
    )
    if not safety_caps_ok:
        failures.append(f"INV-SAFETY-CAPS violated: movement={mov}")
    checks["inv_safety_caps"] = safety_caps_ok

    max_turns_ok = final_state.get("turn", 1) <= MAX_TURNS and final_state.get("tick", 0) <= MATCH_DEADLINE_TICKS
    if not max_turns_ok:
        failures.append(f"INV-MAX-TURNS violated: turn={final_state.get('turn')}, tick={final_state.get('tick')}")
    checks["inv_max_turns"] = max_turns_ok

    hotfix_rules = execution_bundle.get("hotfix_rules", {})
    hotfix_ok = (
        type(hotfix_rules) is dict
        and set(hotfix_rules.keys()).issubset(PERMITTED_HOTFIX_FIELDS)
        and 0.0 <= float(hotfix_rules.get("slowdown_fraction", 0.20)) <= 0.20
        and 0 <= int(hotfix_rules.get("slowdown_duration_ticks", COLLISION_SLOWDOWN_TICKS)) <= 40
    )
    if not hotfix_ok:
        failures.append(f"INV-HOTFIX-SAFETY violated: hotfix_rules={hotfix_rules}")
    checks["inv_hotfix_safety"] = hotfix_ok

    settlement = execution_bundle.get("terminal_settlement")
    status_val = final_state.get("status")
    settlement_ok = True
    if status_val == "delivered":
        if type(settlement) is not dict or settlement.get("status") != "delivered" or settlement.get("settled_once") is not True:
            settlement_ok = False
            failures.append("INV-SETTLEMENT-ONCE: delivered state missing valid terminal_settlement")
        else:
            if settlement.get("live_participant_minted_from_fixture") is not False:
                settlement_ok = False
                failures.append("AUDIT-03: live_participant_minted_from_fixture must be False")
            exp_total = expected_human_pool // 2 if bounty.get("collision_halved") else expected_human_pool
            exp_streamer = exp_total // 2
            exp_aud_pool = exp_total - exp_streamer
            elig_voters = final_state.get("audience", {}).get("eligible_voters_count", 0)
            exp_aud_alloc = exp_aud_pool if elig_voters > 0 else 0
            exp_aud_withheld = 0 if elig_voters > 0 else exp_aud_pool
            exp_rational = str(Fraction(exp_aud_pool, elig_voters)) if elig_voters > 0 else "0"
            if (
                settlement.get("total_hype") != exp_total
                or settlement.get("streamer_share") != exp_streamer
                or settlement.get("audience_share_total") != exp_aud_alloc
                or settlement.get("audience_withheld") != exp_aud_withheld
                or settlement.get("per_voter_rational") != exp_rational
            ):
                settlement_ok = False
                failures.append(
                    f"INV-SETTLEMENT-ONCE arithmetic mismatch: observed={settlement}, expected_total={exp_total}"
                )
    elif status_val == "wiped":
        if type(settlement) is not dict or settlement.get("status") != "wiped" or settlement.get("total_hype") != 0:
            settlement_ok = False
            failures.append(f"INV-WIPE-CLEAN violated: {settlement}")
    elif status_val == "racing":
        if settlement is not None:
            settlement_ok = False
            failures.append("INV-SETTLEMENT-ONCE: racing state must not have terminal_settlement")
    checks["inv_settlement"] = settlement_ok

    # 4. Evaluate concrete expected_oracle assertions (AUDIT-02)
    unknown_keys = set(oracle.keys()) - RECOGNIZED_ORACLE_KEYS
    if unknown_keys:
        failures.append(f"AUDIT-02: unrecognized expected_oracle keys: {sorted(unknown_keys)}")

    def _check_eq(oracle_key: str, actual_val: Any):
        if oracle_key in oracle:
            exp_val = oracle[oracle_key]
            ok = actual_val == exp_val
            checks[oracle_key] = ok
            if not ok:
                failures.append(f"Oracle mismatch on {oracle_key}: expected {exp_val!r}, got {actual_val!r}")

    _check_eq("expected_final_status", final_state.get("status"))
    _check_eq("expected_final_tick", final_state.get("tick"))
    if "expected_final_tick_range" in oracle:
        rng = oracle["expected_final_tick_range"]
        t_val = final_state.get("tick", -1)
        ok = isinstance(rng, (list, tuple)) and len(rng) == 2 and rng[0] <= t_val <= rng[1]
        checks["expected_final_tick_range"] = ok
        if not ok:
            failures.append(f"Oracle mismatch on expected_final_tick_range: expected {rng!r}, got tick {t_val!r}")

    _check_eq("expected_final_turn", final_state.get("turn"))
    _check_eq("expected_final_phase", final_state.get("phase"))
    _check_eq("expected_lane", final_state.get("avatar", {}).get("lane"))
    _check_eq("expected_pool", bounty.get("pool"))
    _check_eq("expected_synthetic_fixture_pool", bounty.get("synthetic_fixture_pool"))
    _check_eq("expected_collisions_total", bounty.get("collisions_total"))
    _check_eq("expected_collision_halved", bounty.get("collision_halved"))
    _check_eq("expected_hazard_countered", final_state.get("hazard", {}).get("hazard_countered"))
    _check_eq("expected_warning_active", final_state.get("hazard", {}).get("warning_active"))
    _check_eq("expected_obstacle_active", final_state.get("hazard", {}).get("obstacle_active"))
    _check_eq("expected_is_paused", final_state.get("is_paused"))
    _check_eq("expected_execution_mode", execution_bundle.get("execution_mode"))
    _check_eq("expected_roster_size", final_state.get("audience", {}).get("roster_size"))
    _check_eq("expected_eligible_voters_count", final_state.get("audience", {}).get("eligible_voters_count"))
    _check_eq("expected_booths_visited", sorted(final_state.get("booths", [])))
    if "expected_booths_subset" in oracle:
        sub = set(oracle["expected_booths_subset"])
        actual_booths = set(final_state.get("booths", []))
        ok = sub.issubset(actual_booths)
        checks["expected_booths_subset"] = ok
        if not ok:
            failures.append(f"Oracle mismatch on expected_booths_subset: expected subset {sorted(sub)}, got {sorted(actual_booths)}")
    _check_eq("expected_audio_state", final_state.get("audio_state"))
    _check_eq("expected_applied_hotfix_version", execution_bundle.get("applied_hotfix_version"))

    if "expected_hotfix_rules" in oracle:
        exp_hf = oracle["expected_hotfix_rules"]
        ok = type(exp_hf) is dict and all(hotfix_rules.get(k) == v for k, v in exp_hf.items())
        checks["expected_hotfix_rules"] = ok
        if not ok:
            failures.append(f"Oracle mismatch on expected_hotfix_rules: expected {exp_hf!r}, got {hotfix_rules!r}")

    if "expected_command_statuses" in oracle:
        exp_statuses = oracle["expected_command_statuses"]
        actual_statuses = [c.get("status") for c in command_log]
        if isinstance(exp_statuses, list):
            ok = actual_statuses == exp_statuses
        elif isinstance(exp_statuses, dict):
            ok = all(actual_statuses[int(k)] == v for k, v in exp_statuses.items() if int(k) < len(actual_statuses))
        else:
            ok = False
        checks["expected_command_statuses"] = ok
        if not ok:
            failures.append(
                f"Oracle mismatch on expected_command_statuses: expected {exp_statuses!r}, got {actual_statuses!r}"
            )

    if "expected_settlement" in oracle:
        exp_set = oracle["expected_settlement"]
        if exp_set is None:
            ok = settlement is None
        else:
            ok = type(settlement) is dict and all(settlement.get(k) == v for k, v in exp_set.items())
        checks["expected_settlement"] = ok
        if not ok:
            failures.append(f"Oracle mismatch on expected_settlement: expected {exp_set!r}, got {settlement!r}")

    if "expected_boundary_labels" in oracle:
        exp_labels = oracle["expected_boundary_labels"]
        b_hashes = execution_bundle.get("boundary_hashes", {})
        b_keys = set(b_hashes.keys()) if isinstance(b_hashes, dict) else set()
        missing_labels = []
        for lbl in exp_labels:
            if lbl not in b_keys and not any(k.endswith(f"_{lbl}") for k in b_keys):
                missing_labels.append(lbl)
        ok = len(missing_labels) == 0
        checks["expected_boundary_labels"] = ok
        if not ok:
            failures.append(f"Oracle mismatch on expected_boundary_labels: missing {missing_labels} in {sorted(b_keys)}")

    raw_eval = {
        "scenario_id": contract.get("scenario_id"),
        "passed": len(failures) == 0,
        "failures": failures,
        "checks": checks,
        "terminal_settlement": settlement,
    }
    invariant_evaluations = evaluate_scenario_properties(
        contract,
        command_log,
        trace_deltas if trace_chain_valid else [],
        (initial_state, final_state),
        oracle_evaluation=raw_eval,
    )
    invariants_verified = [r["invariant_id"] for r in invariant_evaluations if r.get("status") == "PASS"]
    declared_invariants = list(contract.get("invariants_tested", []))
    all_declared_passed = (
        len(invariants_verified) == len(declared_invariants)
        and all(r.get("status") == "PASS" for r in invariant_evaluations)
    )
    if not all_declared_passed:
        failing_props = [r["invariant_id"] for r in invariant_evaluations if r.get("status") != "PASS"]
        failures.append(f"Declared invariant verification failed: {failing_props}")

    passed_overall = (len(failures) == 0 and all_declared_passed)

    return {
        "scenario_id": contract.get("scenario_id"),
        "passed": passed_overall,
        "failures": failures,
        "checks": checks,
        "invariants_verified": invariants_verified if passed_overall else [],
        "invariant_evaluations": invariant_evaluations,
        "trace_chain_valid": trace_chain_valid,
        "recomputed_human_pool": expected_human_pool,
        "recomputed_synthetic_fixture_pool": expected_synthetic_pool,
    }
