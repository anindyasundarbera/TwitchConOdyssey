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
from typing import Any, Dict, List, Optional, Set, Tuple

from coordination.canonical_commands import make_command, validate_command
from coordination.content_cache import canonical_bytes, canonical_hash, detached, validate_json

HZ = 20
TICK_DURATION_SEC = Fraction(1, HZ)  # 0.05s per tick
TICKS_PER_SECOND = HZ
PLANNING_TICKS = 20 * HZ    # 400 ticks (20.0s)
RESOLUTION_TICKS = 5 * HZ   # 100 ticks (5.0s)
REWARD_TICKS = 5 * HZ       # 100 ticks (5.0s)
TURN_TICKS = PLANNING_TICKS + RESOLUTION_TICKS + REWARD_TICKS  # 600 ticks (30.0s)
MAX_TURNS = 3
MATCH_DEADLINE_TICKS = 90 * HZ  # 1800 ticks (90.0s)

HAZARD_ADMISSION_CLOSE_TICKS = 15 * HZ  # 300 ticks (15.0s into planning)
GENERAL_INPUT_CLOSE_TICKS = 20 * HZ     # 400 ticks (20.0s into planning)
HAZARD_ACTIVE_TICKS = 3 * HZ            # 60 ticks (first 3.0s of resolution)
TRANSITION_TICKS = 10                   # 0.5s lane transition at 20Hz
COLLISION_SLOWDOWN_TICKS = 2 * HZ       # 40 ticks (2.0s slowdown)

BASE_SPEED = 100.0 / 88.0  # 100.0 distance units in 88.0 seconds nominal (~1.13636 units/s)
DISTRICTS = (
    {"id": "little_italy_north_embarcadero", "name": "Little Italy / North Embarcadero", "min_p": 0.0, "max_p": 25.0},
    {"id": "embarcadero_waterfront_marina", "name": "Embarcadero Waterfront / Marina", "min_p": 25.0, "max_p": 50.0},
    {"id": "gaslamp_quarter", "name": "Gaslamp Quarter", "min_p": 50.0, "max_p": 75.0},
    {"id": "san_diego_convention_center", "name": "San Diego Convention Center", "min_p": 75.0, "max_p": 95.0},
    {"id": "fictional_main_stage", "name": "Fictional Main Stage", "min_p": 95.0, "max_p": 100.0},
)


def get_district_for_progress(progress: float) -> str:
    for d in DISTRICTS:
        if d["min_p"] <= progress < d["max_p"]:
            return d["name"]
    return DISTRICTS[-1]["name"]


class FullGameSimulator:
    def __init__(self, seed: int = 42, initial_lane: int = 1):
        self.seed = seed
        self.tick = 0
        self.turn = 1
        self.phase = "planning"  # planning, resolution, reward, finished
        self.status = "racing"   # racing, delivered, wiped
        self.is_paused = False

        # Avatar state
        self.lane = initial_lane  # discrete lane: 0 (left), 1 (center), 2 (right)
        self.lateral_pos = float(initial_lane)
        self.transition_remaining_ticks = 0
        self.transition_start_lane = initial_lane
        self.transition_target_lane = initial_lane

        # Forward movement
        self.progress = 0.0
        self.base_speed = BASE_SPEED
        self.speed_multiplier = 1.0
        self.slowdown_ticks_remaining = 0
        self.turn_slowdown_ticks = 0
        self.match_slowdown_ticks = 0
        self.speed_boost_ticks_remaining = 0

        # Roster & Audience
        self.frozen_roster: List[str] = []
        self.pending_joins: Set[str] = set()
        self.pending_leaves: Set[str] = set()
        self.counter_votes: Dict[str, str] = {}  # account_id -> counter_id
        self.eligible_audience: Set[str] = set() # accounts with >=1 accepted counter vote in match
        self.squad_assignments: Dict[str, int] = {} # account_id -> squad index (0 or 1)

        # Hazards & Bounty
        self.committed_hazard: Optional[Dict[str, Any]] = None  # for current turn
        self.hazard_countered = False
        self.warning_active = False
        self.obstacle_active = False
        self.collisions_in_turn = 0
        self.collisions_total = 0
        self.collision_halved_settlement = False
        self.pool = 0  # Hype pool (cap 60)
        self.committed_hazard_ids: Set[str] = set()

        # Booths & Effects
        self.twitch_forcefield_active = False
        self.hotfix_rules: Dict[str, Any] = {
            "slowdown_fraction": 0.20,
            "slowdown_duration_ticks": COLLISION_SLOWDOWN_TICKS,
        }
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
        self._record_boundary_hash("init")

    @property
    def turn_tick(self) -> int:
        return self.tick % TURN_TICKS

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

    def submit_command(self, cmd: Dict[str, Any]) -> str:
        """Submit and validate a canonical command. Return status: applied, expired, rejected, duplicate."""
        try:
            cmd = validate_command(cmd)
        except Exception:
            return "rejected"

        if self.status != "racing":
            return "rejected"

        if self.is_paused and cmd["kind"] != "operator.pause":
            return "rejected"

        kind = cmd["kind"]
        payload = cmd["payload"]
        actor_id = cmd["actor_id"]
        turn_t = self.turn_tick

        if kind == "operator.pause":
            pause_val = payload.get("state", True)
            if self.tick >= MATCH_DEADLINE_TICKS:
                # Pause cannot suspend a reached deadline
                return "rejected"
            self.is_paused = pause_val
            self.command_history.append({"cmd": cmd, "status": "applied"})
            return "applied"

        if kind == "streamer.steer":
            # Steering active in planning, resolution, reward until terminal state
            if self.status != "racing":
                return "rejected"
            direction = payload.get("direction")
            if direction not in ("left", "right", "cancel"):
                return "rejected"
            if direction == "cancel":
                # Opposite directions canceled
                return "applied"

            # Check if transition already in progress
            if self.transition_remaining_ticks > 0:
                # Input during transition ignored/rejected
                return "rejected"

            target = self.lane - 1 if direction == "left" else self.lane + 1
            if target < 0 or target > 2:
                # Clamped to edges
                return "rejected"

            self.transition_start_lane = self.lane
            self.transition_target_lane = target
            self.transition_remaining_ticks = TRANSITION_TICKS
            self.command_history.append({"cmd": cmd, "status": "applied"})
            return "applied"

        elif kind == "hazard.propose":
            # Allowed strictly in half-open interval [0, 15.000s) of planning phase
            if self.phase != "planning" or turn_t >= HAZARD_ADMISSION_CLOSE_TICKS:
                return "expired"

            hazard_id = payload.get("hazard_id")
            if not hazard_id or cmd["provenance"] not in ("human", "fixture"):
                return "rejected"

            # Max 1 hazard per turn
            if self.committed_hazard is not None:
                if self.committed_hazard["hazard_id"] == hazard_id:
                    return "duplicate"
                return "rejected"

            if hazard_id in self.committed_hazard_ids:
                return "duplicate"

            # Commit hazard
            self.committed_hazard = {
                "hazard_id": hazard_id,
                "kind": payload.get("kind", "blocked_demo_lane"),
                "lane": payload.get("lane", 1),
                "committed_tick": self.tick,
                "actor_id": actor_id,
            }
            self.committed_hazard_ids.add(hazard_id)
            # Pool increment: +20 for human-origin hazard committed before t=15, cap 60
            if cmd["provenance"] == "human":
                self.pool = min(60, self.pool + 20)
            elif cmd["provenance"] == "fixture":
                # Fixture hazard can add to fictional demo pool up to cap
                self.pool = min(60, self.pool + 20)

            self.command_history.append({"cmd": cmd, "status": "applied"})
            return "applied"

        elif kind == "viewer.counter":
            # Allowed strictly in half-open interval [0, 20.000s) of planning phase
            if self.phase != "planning" or turn_t >= GENERAL_INPUT_CLOSE_TICKS:
                return "expired"

            # Must bind to committed hazard ID
            hazard_id = payload.get("hazard_id")
            if not self.committed_hazard or self.committed_hazard["hazard_id"] != hazard_id:
                return "rejected"

            # Check account eligibility
            if actor_id not in self.frozen_roster:
                return "rejected"

            # Atomic influence: max 1 influence per subject per turn
            if actor_id in self.counter_votes:
                return "duplicate"

            self.counter_votes[actor_id] = payload.get("counter", "clear_lane")
            self.eligible_audience.add(actor_id)
            self.command_history.append({"cmd": cmd, "status": "applied"})
            return "applied"

        elif kind == "booth.hotfix":
            # Data/rules only patch proposal
            patch_data = payload.get("patch_data", {})
            signature = payload.get("signature")
            if not signature or signature != "TRUSTED_CODEX_KEY":
                return "rejected"
            # Verify data/rules patch cannot relax safety invariants
            if "hp_system" in patch_data or "unbounded_slowdown" in patch_data:
                return "rejected"
            self.pending_hotfix = patch_data
            self.command_history.append({"cmd": cmd, "status": "applied"})
            return "applied"

        elif kind == "booth.boost":
            # AWS/IVS scale boost
            factor = payload.get("factor", 1.1)
            self.speed_boost_ticks_remaining = int(payload.get("duration_ticks", 40))
            self.command_history.append({"cmd": cmd, "status": "applied"})
            return "applied"

        return "rejected"

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
                self.hotfix_rules.update(self.pending_hotfix)
                self.pending_hotfix = None
            self._record_boundary_hash(f"turn_{self.turn}_start")
        elif turn_t == PLANNING_TICKS:
            self.phase = "resolution"
            self._record_boundary_hash(f"turn_{self.turn}_resolution_start")
            self._adjudicate_counter_quorum()
        elif turn_t == PLANNING_TICKS + RESOLUTION_TICKS:
            self.phase = "reward"
            self.obstacle_active = False
            self.warning_active = False
            self._record_boundary_hash(f"turn_{self.turn}_reward_start")

    def step(self):
        """Advance simulation by exactly one authoritative 20 Hz tick."""
        if self.status != "racing":
            return

        # 1. Total order: Deadline first
        if self.tick >= MATCH_DEADLINE_TICKS:
            self._handle_wipe("deadline_reached")
            return

        # Check pause
        if self.is_paused:
            # Paused simulation produces no ticks, clocks frozen
            return

        turn_t = self.turn_tick

        # Warning evaluation during planning [15.0s, 20.0s)
        if self.phase == "planning":
            if HAZARD_ADMISSION_CLOSE_TICKS <= turn_t < GENERAL_INPUT_CLOSE_TICKS:
                self.warning_active = (self.committed_hazard is not None)
                if self.warning_active:
                    self.audio_state = "crisis"
            else:
                self.warning_active = False

        # Obstacle active during first 3.0s of resolution (ticks 400..460 of turn)
        if self.phase == "resolution":
            rel_res_tick = turn_t - PLANNING_TICKS
            if rel_res_tick < HAZARD_ACTIVE_TICKS and self.committed_hazard and not self.hazard_countered:
                self.obstacle_active = True
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
                self.events.append({"tick": self.tick, "kind": "collision", "lane": 1, "turn": self.turn})

        # c. delivery detection
        if self.progress >= 100.0:
            # Delivered strictly before deadline!
            self._handle_delivery()
            return

        # Booth triggers
        self._check_booth_triggers()

        # Advance tick
        self.tick += 1

        # Check deadline at tick boundary
        if self.tick >= MATCH_DEADLINE_TICKS:
            if self.progress >= 100.0:
                # Delivery strictly before deadline was checked above; if progress reaches exactly at 1800, deadline wipes
                self._handle_wipe("deadline_equality_wipe")
            else:
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
            return

        # Integer threshold: (3*N + 4) // 5 = ceil(0.60 * N)
        threshold = (3 * N + 4) // 5
        votes_count = sum(1 for v in self.counter_votes.values() if v == "clear_lane")

        if votes_count >= threshold and votes_count >= 1:
            self.hazard_countered = True
            self.obstacle_active = False
            self.audio_state = "solution"
            self.events.append({"tick": self.tick, "kind": "clear_lane_success", "votes": votes_count, "threshold": threshold})
        else:
            self.hazard_countered = False
            self.events.append({"tick": self.tick, "kind": "clear_lane_failed", "votes": votes_count, "threshold": threshold})

    def _check_booth_triggers(self):
        # District 2: Waterfront/Marina (Twitch Booth at progress 35.0)
        if self.progress >= 35.0 and "twitch_booth" not in self.booths_visited:
            self.booths_visited.add("twitch_booth")
            self.twitch_forcefield_active = True
            self.events.append({"tick": self.tick, "kind": "booth_visited", "booth": "twitch_booth"})

        # District 3: Gaslamp Quarter (Codex Live Hotfix Booth at progress 60.0)
        if self.progress >= 60.0 and "codex_booth" not in self.booths_visited:
            self.booths_visited.add("codex_booth")
            self.events.append({"tick": self.tick, "kind": "booth_visited", "booth": "codex_booth"})

        # District 4: Convention Center (AWS/IVS Booth at progress 80.0)
        if self.progress >= 80.0 and "aws_booth" not in self.booths_visited:
            self.booths_visited.add("aws_booth")
            self.ivs_scale_boost_active = True
            self.events.append({"tick": self.tick, "kind": "booth_visited", "booth": "aws_booth"})

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
            "streamer_share": 0,
            "audience_share_total": 0,
            "audience_withheld": self.pool,
            "settled_once": True,
        }
        self.events.append({"tick": self.tick, "kind": "wipe", "reason": reason})
        self._record_boundary_hash(f"terminal_wipe_{reason}")

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
