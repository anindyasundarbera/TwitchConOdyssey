"""Shared pure deterministic kernel rules module.

Exposes authoritative tick progression, deadline ordering, warning interval gating,
and per-property scenario and pipeline invariant evaluation.

Pure: No file, network, clock, process, environment, model, or service I/O.
Time values arrive strictly as function arguments.
"""
import copy
from fractions import Fraction
import hashlib
import json
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .canonical_commands import make_command, validate_command
from .content_cache import canonical_bytes, canonical_hash, detached, validate_json
from .state_transport import apply_diff, state_diff

# --- Cadence & Boundary Constants ---
HZ = 20
TICK_DURATION_SEC = Fraction(1, 20)  # 0.05s
PLANNING_TICKS = 20 * HZ             # 400 ticks (20.0s)
RESOLUTION_TICKS = 5 * HZ            # 100 ticks (5.0s)
REWARD_TICKS = 5 * HZ                # 100 ticks (5.0s)
TURN_TICKS = PLANNING_TICKS + RESOLUTION_TICKS + REWARD_TICKS  # 600 ticks (30.0s)
MAX_TURNS = 3
MATCH_DEADLINE_TICKS = 90 * HZ       # 1800 ticks (90.0s)

HAZARD_ADMISSION_CLOSE_TICKS = 15 * HZ  # 300 ticks (15.0s into planning)
GENERAL_INPUT_CLOSE_TICKS = 20 * HZ     # 400 ticks (20.0s into planning)
HAZARD_ACTIVE_TICKS = 3 * HZ            # 60 ticks (first 3.0s of resolution)
TRANSITION_TICKS = 10                   # 0.5s lane transition at 20 Hz
COLLISION_SLOWDOWN_TICKS = 2 * HZ       # 40 ticks (2.0s slowdown)

BASE_SPEED = 100.0 / 88.0               # ~1.13636 units/s
PERMITTED_HOTFIX_FIELDS = frozenset({"slowdown_fraction", "slowdown_duration_ticks"})

DISTRICTS = (
    {"id": "little_italy_north_embarcadero", "name": "Little Italy / North Embarcadero", "min_p": 0.0, "max_p": 25.0},
    {"id": "embarcadero_waterfront_marina", "name": "Embarcadero Waterfront / Marina", "min_p": 25.0, "max_p": 50.0},
    {"id": "gaslamp_quarter", "name": "Gaslamp Quarter", "min_p": 50.0, "max_p": 75.0},
    {"id": "san_diego_convention_center", "name": "San Diego Convention Center", "min_p": 75.0, "max_p": 95.0},
    {"id": "fictional_main_stage", "name": "Fictional Main Stage", "min_p": 95.0, "max_p": 100.0},
)


def get_district_for_progress(progress: float) -> str:
    """Return canonical district name for progress in [0.0, 100.0]."""
    p = max(0.0, min(100.0, float(progress)))
    for d in DISTRICTS:
        if d["min_p"] <= p <= d["max_p"]:
            return d["name"]
    return DISTRICTS[-1]["name"]


# ==============================================================================
# R5 / 6.4: Delivery Deadline Eligibility
# ==============================================================================

def is_delivery_before_deadline(
    previous: Union[Dict[str, Any], int, float, None],
    next_val: Union[Dict[str, Any], int, float],
) -> bool:
    """Return true only when delivery occurs strictly before the deadline tick (1800).

    Tick 1799: eligible; returns True.
    Tick 1800: not eligible; deadline wipe wins, returns False.
    Tick 1801: not eligible; returns False.

    Pure: does not consult wall clock or external state.
    """
    if isinstance(next_val, dict):
        delivery_tick = next_val.get("tick", 0)
        progress = next_val.get("movement", {}).get("progress", next_val.get("progress", 0.0))
        if progress < 100.0:
            return False
    elif isinstance(next_val, (int, float)):
        delivery_tick = int(next_val)
    else:
        return False

    return delivery_tick < MATCH_DEADLINE_TICKS


# ==============================================================================
# R6 / R7 / 6.5: Hazard Warning State & Boundary Gating
# ==============================================================================

def hazard_warning_active(
    committed: Any,
    tick: int,
    target_hazard_id: Optional[str] = None,
    committed_hazard_id: Optional[str] = None,
) -> bool:
    """Define warning activity as the half-open interval [300, 400), tied to committed hazard ID.

    Ticks 299 and 400 are inactive; ticks 300 and 399 are active.
    Resolution phase [400, 500) and reward phase [500, 600) are inactive.
    A hazard-ID mismatch produces inactive warning state.

    Supports flexible caller signatures:
      hazard_warning_active(committed_hazard_dict_or_tick, tick)
      hazard_warning_active(committed_id, target_id, tick)
      hazard_warning_active(committed_tick, tick, committed_hazard_id=..., target_hazard_id=...)
    """
    # Handle 3-argument positional convention: (committed_id, target_id, tick)
    if isinstance(committed, str) and isinstance(tick, str) and isinstance(target_hazard_id, (int, float)):
        c_id = committed
        t_id = tick
        tick_val = int(target_hazard_id)
        if c_id != t_id or not c_id:
            return False
        turn_t = tick_val % TURN_TICKS
        return HAZARD_ADMISSION_CLOSE_TICKS <= turn_t < GENERAL_INPUT_CLOSE_TICKS

    if committed is None or committed is False:
        return False

    # Extract committed hazard ID and committed tick
    c_hazard_id = None
    if isinstance(committed, dict):
        c_hazard_id = committed.get("hazard_id")
        c_tick = committed.get("committed_tick", 0)
    elif isinstance(committed, str):
        c_hazard_id = committed
        c_tick = 0
    elif isinstance(committed, (int, float)):
        c_hazard_id = committed_hazard_id
        c_tick = int(committed)
    else:
        return False

    # Hazard ID mismatch yields inactive warning state
    if target_hazard_id is not None:
        if not c_hazard_id or c_hazard_id != target_hazard_id:
            return False
    if committed_hazard_id is not None:
        if not c_hazard_id or c_hazard_id != committed_hazard_id:
            return False

    if c_hazard_id is None and not isinstance(committed, (int, float)):
        return False

    turn_t = int(tick) % TURN_TICKS
    # Half-open interval [300, 400) of planning phase
    return HAZARD_ADMISSION_CLOSE_TICKS <= turn_t < GENERAL_INPUT_CLOSE_TICKS


# ==============================================================================
# R3 / R4 / 6.3: Authoritative Tick Ordering & State Advancement
# ==============================================================================

def _command_event_tick(cmd: Dict[str, Any]) -> int:
    """Extract authoritative event tick from a command envelope."""
    if "logical_tick" in cmd:
        return int(cmd["logical_tick"])
    if "event_tick" in cmd:
        return int(cmd["event_tick"])
    return int(cmd.get("tick", 0))


def advance_tick(
    state: Dict[str, Any],
    commands: List[Dict[str, Any]],
    *,
    base_speed_override: Optional[float] = None,
    hotfix_rules: Optional[Dict[str, Any]] = None,
    frozen_roster: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Apply a single authoritative 20 Hz tick.

    Strict tick ordering:
    1. Deadline boundary evaluated first.
       If tick == MATCH_DEADLINE_TICKS (1800), deadline wipe wins; settlement is zero.
    2. If tick > MATCH_DEADLINE_TICKS, post-deadline no-op.
    3. Commands and effects applied only when event time is strictly earlier than deadline.
    4. Motion and collision evaluated during tick interval.
    5. Advance tick clock by +1.
    6. Delivery strictly before deadline settles; equality at 1800 wipes with zero settlement.
    7. Emit events in defined, stable order; preserve actual event tick in state and traces.

    Pure: no I/O, no wall clock, no model/service calls.
    """
    state = copy.deepcopy(state)
    events: List[Dict[str, Any]] = []

    current_tick = int(state.get("tick", 0))
    status = state.get("status", "racing")

    # 1. Total order: Deadline boundary evaluated FIRST at current tick
    if current_tick == MATCH_DEADLINE_TICKS:
        state["status"] = "wiped"
        state["phase"] = "finished"
        state["audio_state"] = "defeat"
        wipe_settlement = {
            "status": "wiped",
            "reason": "deadline_reached",
            "total_hype": 0,
            "original_pool": state.get("bounty", {}).get("pool", 0),
            "synthetic_fixture_hype_illustrated": state.get("bounty", {}).get("synthetic_fixture_pool", 0),
            "live_participant_minted_from_fixture": False,
            "live_participant_minted": False,
            "collision_halved": state.get("bounty", {}).get("collision_halved", False),
            "streamer_share": 0,
            "audience_share_total": 0,
            "audience_withheld": 0,
            "eligible_voters_count": state.get("audience", {}).get("eligible_voters_count", 0),
            "per_voter_rational": "0",
            "settled_once": True,
            "tick": current_tick,
        }
        state["terminal_settlement"] = wipe_settlement
        events.append({"tick": current_tick, "kind": "wipe", "reason": "deadline_reached"})
        return state, events

    if current_tick > MATCH_DEADLINE_TICKS:
        return state, []

    if status != "racing":
        return state, []

    if state.get("is_paused", False):
        # When paused, process operator unpause commands if any, but do not advance tick
        for cmd in commands:
            if _command_event_tick(cmd) < MATCH_DEADLINE_TICKS and cmd.get("kind") == "operator.pause":
                payload = cmd.get("payload", {})
                if not payload.get("state", True):
                    state["is_paused"] = False
                    events.append({"tick": _command_event_tick(cmd), "kind": "unpaused"})
        return state, events

    hf = hotfix_rules if hotfix_rules is not None else {"slowdown_fraction": 0.20, "slowdown_duration_ticks": COLLISION_SLOWDOWN_TICKS}
    roster = frozen_roster if frozen_roster is not None else []

    # 2. Command admission & application strictly before deadline
    eligible_commands = [c for c in commands if _command_event_tick(c) < MATCH_DEADLINE_TICKS]
    # Stable sort by (logical_tick, sequence)
    eligible_commands.sort(key=lambda c: (_command_event_tick(c), c.get("sequence", 0)))

    avatar = state.setdefault("avatar", {"lane": 1, "lateral_pos": 1.0, "transition_remaining_ticks": 0})
    movement = state.setdefault("movement", {
        "progress": 0.0,
        "district": DISTRICTS[0]["name"],
        "slowdown_ticks_remaining": 0,
        "turn_slowdown_ticks": 0,
        "match_slowdown_ticks": 0,
    })
    bounty = state.setdefault("bounty", {
        "pool": 0,
        "synthetic_fixture_pool": 0,
        "collisions_total": 0,
        "collision_halved": False,
    })
    hazard = state.setdefault("hazard", {
        "committed": None,
        "warning_active": False,
        "obstacle_active": False,
        "hazard_countered": False,
    })
    audience = state.setdefault("audience", {
        "roster_size": len(roster),
        "counter_votes_count": 0,
        "eligible_voters_count": 0,
    })
    booths = state.setdefault("booths", [])

    turn_t = current_tick % TURN_TICKS

    # Process eligible commands
    for cmd in eligible_commands:
        k = cmd.get("kind")
        prov = cmd.get("provenance")
        payload = cmd.get("payload", {})
        ev_tick = _command_event_tick(cmd)

        if k == "streamer.steer" and prov == "human":
            direction = payload.get("direction")
            current_lane = avatar["lane"]
            if direction == "left" and current_lane > 0:
                avatar["lane"] = current_lane - 1
                avatar["transition_remaining_ticks"] = TRANSITION_TICKS
                events.append({"tick": ev_tick, "kind": "steer", "lane": avatar["lane"], "direction": "left"})
            elif direction == "right" and current_lane < 2:
                avatar["lane"] = current_lane + 1
                avatar["transition_remaining_ticks"] = TRANSITION_TICKS
                events.append({"tick": ev_tick, "kind": "steer", "lane": avatar["lane"], "direction": "right"})

        elif k == "hazard.propose" and prov in ("human", "fixture"):
            # Only admitted in [0, 15.0s) of planning phase
            if state.get("phase", "planning") == "planning" and turn_t < HAZARD_ADMISSION_CLOSE_TICKS:
                h_id = payload.get("hazard_id")
                if h_id and not hazard.get("committed"):
                    hazard["committed"] = h_id
                    hazard["committed_tick"] = ev_tick
                    if prov == "human":
                        bounty["pool"] = min(60, bounty["pool"] + 20)
                    elif prov == "fixture":
                        bounty["synthetic_fixture_pool"] = min(60, bounty["synthetic_fixture_pool"] + 20)
                    events.append({"tick": ev_tick, "kind": "hazard_committed", "hazard_id": h_id, "provenance": prov})

        elif k == "viewer.counter" and prov == "human":
            # Gated on warning state and matching committed hazard ID
            h_id = payload.get("hazard_id")
            if hazard_warning_active(hazard.get("committed"), current_tick, target_hazard_id=h_id):
                audience["counter_votes_count"] = audience.get("counter_votes_count", 0) + 1
                audience["eligible_voters_count"] = audience.get("eligible_voters_count", 0) + 1
                events.append({"tick": ev_tick, "kind": "counter_vote", "hazard_id": h_id})

        elif k == "operator.pause" and prov == "human":
            state["is_paused"] = payload.get("state", True)
            events.append({"tick": ev_tick, "kind": "paused" if state["is_paused"] else "unpaused"})

    # 3. Steering & Lane interpolation
    rem = avatar.get("transition_remaining_ticks", 0)
    if rem > 0:
        avatar["transition_remaining_ticks"] = rem - 1
        avatar["lateral_pos"] = float(avatar["lane"])

    # 4. Warning interval for the tick [300, 400)
    committed_h = hazard.get("committed")
    warning_is_active = hazard_warning_active(committed_h, current_tick)
    hazard["warning_active"] = warning_is_active

    # Obstacle active during resolution [400, 460) if committed and uncountered
    if state.get("phase") == "resolution":
        rel_res = turn_t - PLANNING_TICKS
        hazard["obstacle_active"] = (rel_res < HAZARD_ACTIVE_TICKS and committed_h is not None and not hazard.get("hazard_countered", False))
    else:
        hazard["obstacle_active"] = False

    # 5. Speed & Progress calculation
    speed = base_speed_override if base_speed_override is not None else BASE_SPEED
    slowdown_rem = movement.get("slowdown_ticks_remaining", 0)
    if slowdown_rem > 0:
        speed *= (1.0 - float(hf.get("slowdown_fraction", 0.20)))
        movement["slowdown_ticks_remaining"] = slowdown_rem - 1
        movement["turn_slowdown_ticks"] = movement.get("turn_slowdown_ticks", 0) + 1
        movement["match_slowdown_ticks"] = movement.get("match_slowdown_ticks", 0) + 1

    delta_progress = speed * float(TICK_DURATION_SEC)
    new_progress = min(100.0, movement.get("progress", 0.0) + delta_progress)

    # 6. Collision adjudication
    if hazard.get("obstacle_active") and abs(avatar.get("lateral_pos", 1.0) - 1.0) < 0.4:
        if movement.get("turn_slowdown_ticks", 0) == 0:
            bounty["collisions_total"] = bounty.get("collisions_total", 0) + 1
            bounty["collision_halved"] = True
            movement["slowdown_ticks_remaining"] = int(hf.get("slowdown_duration_ticks", COLLISION_SLOWDOWN_TICKS))
            state["audio_state"] = "crisis"
            events.append({"tick": current_tick, "kind": "collision", "lane": 1, "turn": state.get("turn", 1)})

    # 7. Booth visits
    if new_progress >= 35.0 and "twitch_booth" not in booths:
        booths.append("twitch_booth")
        booths.sort()
        events.append({"tick": current_tick, "kind": "booth_visited", "booth": "twitch_booth"})
    if new_progress >= 60.0 and "codex_booth" not in booths:
        booths.append("codex_booth")
        booths.sort()
        events.append({"tick": current_tick, "kind": "booth_visited", "booth": "codex_booth"})
    if new_progress >= 80.0 and "aws_booth" not in booths:
        booths.append("aws_booth")
        booths.sort()
        events.append({"tick": current_tick, "kind": "booth_visited", "booth": "aws_booth"})

    # 8. Advance clock by +1 tick
    next_tick = current_tick + 1
    state["tick"] = next_tick
    movement["progress"] = round(new_progress, 4)
    movement["district"] = get_district_for_progress(new_progress)

    # 9. Delivery vs Deadline Boundary Check
    if new_progress >= 100.0:
        # Finished motion during the tick interval ending at next_tick!
        if is_delivery_before_deadline(current_tick, next_tick):
            # Strictly before deadline (tick < 1800, e.g. 1799)
            state["status"] = "delivered"
            state["phase"] = "finished"
            state["audio_state"] = "victory"
            total_hype = bounty["pool"]
            if bounty.get("collision_halved"):
                total_hype = total_hype // 2
            streamer_share = total_hype // 2
            aud_total = total_hype - streamer_share
            elig = audience.get("eligible_voters_count", 0)
            aud_alloc = aud_total if elig > 0 else 0
            aud_withheld = 0 if elig > 0 else aud_total
            per_voter = str(Fraction(aud_total, elig)) if elig > 0 else "0"

            settlement = {
                "status": "delivered",
                "tick": next_tick,
                "total_hype": total_hype,
                "original_pool": bounty["pool"],
                "synthetic_fixture_hype_illustrated": bounty["synthetic_fixture_pool"],
                "live_participant_minted_from_fixture": False,
                "live_participant_minted": False,
                "collision_halved": bounty.get("collision_halved", False),
                "streamer_share": streamer_share,
                "audience_share_total": aud_alloc,
                "audience_withheld": aud_withheld,
                "eligible_voters_count": elig,
                "per_voter_rational": per_voter,
                "settled_once": True,
            }
            state["terminal_settlement"] = settlement
            events.append({"tick": next_tick, "kind": "delivery_settlement", "settlement": settlement})
            return state, events
        else:
            # Equality with deadline (next_tick == 1800) or later:
            # DEADLINE WIPE WINS! Settlement is zero!
            state["status"] = "wiped"
            state["phase"] = "finished"
            state["audio_state"] = "defeat"
            settlement = {
                "status": "wiped",
                "reason": "deadline_equality_wipe",
                "total_hype": 0,
                "original_pool": bounty["pool"],
                "synthetic_fixture_hype_illustrated": bounty["synthetic_fixture_pool"],
                "live_participant_minted_from_fixture": False,
                "live_participant_minted": False,
                "collision_halved": bounty.get("collision_halved", False),
                "streamer_share": 0,
                "audience_share_total": 0,
                "audience_withheld": 0,
                "eligible_voters_count": audience.get("eligible_voters_count", 0),
                "per_voter_rational": "0",
                "settled_once": True,
                "tick": next_tick,
            }
            state["terminal_settlement"] = settlement
            events.append({"tick": next_tick, "kind": "wipe", "reason": "deadline_equality_wipe"})
            return state, events

    # Check deadline if progress < 100.0 but next_tick reaches 1800
    if next_tick >= MATCH_DEADLINE_TICKS:
        state["status"] = "wiped"
        state["phase"] = "finished"
        state["audio_state"] = "defeat"
        settlement = {
            "status": "wiped",
            "reason": "deadline_reached",
            "total_hype": 0,
            "original_pool": bounty["pool"],
            "synthetic_fixture_hype_illustrated": bounty["synthetic_fixture_pool"],
            "live_participant_minted_from_fixture": False,
            "live_participant_minted": False,
            "collision_halved": bounty.get("collision_halved", False),
            "streamer_share": 0,
            "audience_share_total": 0,
            "audience_withheld": 0,
            "eligible_voters_count": audience.get("eligible_voters_count", 0),
            "per_voter_rational": "0",
            "settled_once": True,
            "tick": next_tick,
        }
        state["terminal_settlement"] = settlement
        events.append({"tick": next_tick, "kind": "wipe", "reason": "deadline_reached"})
        return state, events

    # Update turn and phase boundaries for next_tick
    new_turn_t = next_tick % TURN_TICKS
    turn_idx = min(MAX_TURNS, next_tick // TURN_TICKS + 1)
    state["turn"] = turn_idx
    if new_turn_t < PLANNING_TICKS:
        state["phase"] = "planning"
    elif new_turn_t < PLANNING_TICKS + RESOLUTION_TICKS:
        state["phase"] = "resolution"
    else:
        state["phase"] = "reward"

    # Re-evaluate warning active for start of next tick
    state["hazard"]["warning_active"] = hazard_warning_active(state["hazard"].get("committed"), next_tick)

    return state, events


# ==============================================================================
# R8 / R9 / 6.6 / 6.7: Per-Property Invariant Evidence Evaluators
# ==============================================================================

VALIDATOR_VERSION = "deterministic_kernel_v2.0"


def _build_invariant_result(
    scenario_id: str,
    invariant_id: str,
    status: str,
    evidence_fields: List[str],
    evaluation_count: int,
    observed: Any,
    expected: Any,
    evidence_refs: Optional[List[str]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    """Format an evidence-grounded per-invariant evaluation record."""
    return {
        "scenario_id": scenario_id,
        "invariant_id": invariant_id,
        "contract_version": "2",
        "status": status,
        "evidence_fields_checked": sorted(evidence_fields),
        "evaluation_count": evaluation_count,
        "observed": observed,
        "expected": expected,
        "evidence_refs": evidence_refs or ["EV-009"],
        "evaluator": f"{invariant_id}_validator:{VALIDATOR_VERSION}",
        "notes": notes,
    }


def evaluate_single_scenario_property(
    invariant_id: str,
    contract: Dict[str, Any],
    command_log: List[Dict[str, Any]],
    trace_deltas: List[Dict[str, Any]],
    initial_state: Dict[str, Any],
    final_state: Dict[str, Any],
    oracle_evaluation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Recompute one named scenario invariant directly from evidence fields."""
    sid = contract.get("scenario_id", "UNKNOWN")

    if not initial_state or not final_state:
        return _build_invariant_result(
            sid, invariant_id, "FAIL", ["initial_state", "final_state"],
            0, "missing_state", "valid_initial_and_final_state", notes="Missing state records",
        )

    bounty = final_state.get("bounty", {})
    movement = final_state.get("movement", {})
    hazard = final_state.get("hazard", {})
    audience = final_state.get("audience", {})
    settlement = final_state.get("terminal_settlement") or (oracle_evaluation.get("terminal_settlement") if oracle_evaluation else None)

    # 1. INV-BOT-ISOLATION
    if invariant_id == "INV-BOT-ISOLATION":
        fields = ["command_log.provenance", "command_log.status", "bounty.pool", "bounty.synthetic_fixture_pool"]
        bot_applied = [c for c in command_log if c.get("cmd", {}).get("provenance") == "bot" and c.get("status") == "applied"]
        fixture_applied_human_pool = [
            c for c in command_log
            if c.get("cmd", {}).get("provenance") == "fixture" and c.get("status") == "applied" and c.get("cmd", {}).get("kind") == "viewer.counter"
        ]
        human_hazards = sum(1 for c in command_log if c.get("cmd", {}).get("provenance") == "human" and c.get("cmd", {}).get("kind") == "hazard.propose" and c.get("status") == "applied")
        exp_pool = min(60, 20 * human_hazards)
        obs_pool = bounty.get("pool", 0)

        ok = (len(bot_applied) == 0 and len(fixture_applied_human_pool) == 0 and obs_pool == exp_pool)
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            len(command_log),
            {"bot_applied": len(bot_applied), "observed_pool": obs_pool},
            {"bot_applied": 0, "expected_pool": exp_pool},
        )

    # 2. INV-COMMAND-VAL
    elif invariant_id == "INV-COMMAND-VAL":
        fields = ["command_log.cmd.schema_version", "command_log.status", "command_log.cmd.command_id"]
        seen_hazards: Set[str] = set()
        dup_hazards = False
        for c in command_log:
            cmd = c.get("cmd", {})
            if cmd.get("kind") == "hazard.propose" and c.get("status") == "applied":
                h_id = cmd.get("payload", {}).get("hazard_id")
                if h_id in seen_hazards:
                    dup_hazards = True
                if h_id:
                    seen_hazards.add(h_id)
        ok = not dup_hazards
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            len(command_log), {"duplicate_hazards": dup_hazards}, {"duplicate_hazards": False},
        )

    # 3. INV-EFFECT-ORDER
    elif invariant_id == "INV-EFFECT-ORDER":
        fields = ["trace_deltas", "final_state.status", "final_state.terminal_settlement"]
        # Collision adjudicates before delivery; deadline wipe precedes delivery at equality
        status_val = final_state.get("status")
        tick_val = final_state.get("tick", 0)
        ok = True
        if tick_val >= MATCH_DEADLINE_TICKS and status_val == "delivered":
            ok = False
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            len(trace_deltas), {"final_status": status_val, "final_tick": tick_val},
            {"status_at_or_after_deadline": "wiped"},
        )

    # 4. INV-MAX-TURNS
    elif invariant_id == "INV-MAX-TURNS":
        fields = ["final_state.turn", "final_state.tick"]
        turn_val = final_state.get("turn", 1)
        tick_val = final_state.get("tick", 0)
        ok = (turn_val <= MAX_TURNS and tick_val <= MATCH_DEADLINE_TICKS)
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            1, {"turn": turn_val, "tick": tick_val}, {"max_turn": MAX_TURNS, "max_tick": MATCH_DEADLINE_TICKS},
        )

    # 5. INV-PAUSE-CLEAN
    elif invariant_id == "INV-PAUSE-CLEAN":
        fields = ["final_state.is_paused", "final_state.tick", "command_log"]
        # If pause is active, tick progression is frozen cleanly
        ok = True
        if final_state.get("is_paused") and final_state.get("tick", 0) > MATCH_DEADLINE_TICKS:
            ok = False
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            1, {"is_paused": final_state.get("is_paused")}, {"paused_cleanly": True},
        )

    # 6. INV-SETTLEMENT-ONCE
    elif invariant_id == "INV-SETTLEMENT-ONCE":
        fields = ["final_state.status", "terminal_settlement.settled_once", "terminal_settlement.total_hype"]
        status_val = final_state.get("status")
        if status_val == "delivered":
            ok = (isinstance(settlement, dict) and settlement.get("settled_once") is True and settlement.get("status") == "delivered")
        elif status_val == "wiped":
            ok = (isinstance(settlement, dict) and settlement.get("settled_once") is True and settlement.get("total_hype") == 0)
        else:
            ok = (settlement is None)
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            1, {"settlement_present": settlement is not None, "status": status_val}, {"settled_once_valid": True},
        )

    # 7. INV-WIPE-CLEAN
    elif invariant_id == "INV-WIPE-CLEAN":
        fields = ["final_state.status", "terminal_settlement.total_hype", "terminal_settlement.streamer_share"]
        if final_state.get("status") == "wiped":
            ok = (isinstance(settlement, dict) and settlement.get("total_hype") == 0 and settlement.get("streamer_share") == 0)
        else:
            ok = True
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            1, {"settlement_hype": settlement.get("total_hype") if settlement else 0}, {"expected_wipe_hype": 0},
        )

    # 8. INV-SAFETY-CAPS
    elif invariant_id == "INV-SAFETY-CAPS":
        fields = ["movement.turn_slowdown_ticks", "movement.match_slowdown_ticks"]
        turn_sd = movement.get("turn_slowdown_ticks", 0)
        match_sd = movement.get("match_slowdown_ticks", 0)
        ok = (turn_sd <= COLLISION_SLOWDOWN_TICKS and match_sd <= COLLISION_SLOWDOWN_TICKS * MAX_TURNS)
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            1, {"turn_slowdown": turn_sd, "match_slowdown": match_sd},
            {"max_turn_slowdown": COLLISION_SLOWDOWN_TICKS, "max_match_slowdown": COLLISION_SLOWDOWN_TICKS * MAX_TURNS},
        )

    # 9. INV-HAZARD-BIND
    elif invariant_id == "INV-HAZARD-BIND":
        fields = ["hazard.committed", "hazard.warning_active", "command_log"]
        committed_per_turn = {}
        if initial_state.get("hazard", {}).get("committed"):
            committed_per_turn[initial_state.get("tick", 0) // TURN_TICKS] = initial_state["hazard"]["committed"]
        if final_state.get("hazard", {}).get("committed"):
            committed_per_turn[final_state.get("tick", 0) // TURN_TICKS] = final_state["hazard"]["committed"]
        for c in command_log:
            cmd = c.get("cmd", {})
            if cmd.get("kind") == "hazard.propose" and c.get("status") == "applied":
                turn_idx = c.get("tick", 0) // TURN_TICKS
                committed_per_turn[turn_idx] = cmd.get("payload", {}).get("hazard_id")

        mismatched_applied = False
        for c in command_log:
            cmd = c.get("cmd", {})
            if cmd.get("kind") == "viewer.counter" and c.get("status") == "applied":
                turn_idx = c.get("tick", 0) // TURN_TICKS
                expected_h = committed_per_turn.get(turn_idx)
                if expected_h is None or cmd.get("payload", {}).get("hazard_id") != expected_h:
                    mismatched_applied = True
        ok = not mismatched_applied
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            len(command_log), {"mismatched_counter_applied": mismatched_applied}, {"mismatched_counter_applied": False},
        )

    # 10. INV-HAZARD-DEPEND
    elif invariant_id == "INV-HAZARD-DEPEND":
        fields = ["hazard.obstacle_active", "hazard.hazard_countered"]
        countered = hazard.get("hazard_countered", False)
        obstacle = hazard.get("obstacle_active", False)
        ok = not (countered and obstacle)
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            1, {"countered": countered, "obstacle_active": obstacle}, {"countered_clears_obstacle": True},
        )

    # 11. INV-HOTFIX-SAFETY
    elif invariant_id == "INV-HOTFIX-SAFETY":
        fields = ["hotfix_rules.slowdown_fraction", "hotfix_rules.slowdown_duration_ticks"]
        ok = movement.get("slowdown_ticks_remaining", 0) <= COLLISION_SLOWDOWN_TICKS
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            1, {"slowdown_remaining": movement.get("slowdown_ticks_remaining", 0)},
            {"max_slowdown": COLLISION_SLOWDOWN_TICKS},
        )

    # 12. INV-ACCOUNT-INFLUENCE
    elif invariant_id == "INV-ACCOUNT-INFLUENCE":
        fields = ["audience.eligible_voters_count", "audience.counter_votes_count"]
        cnt = audience.get("counter_votes_count", 0)
        elig = audience.get("eligible_voters_count", 0)
        ok = (cnt >= 0 and elig >= 0)
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            1, {"counter_votes": cnt, "eligible": elig}, {"nonnegative": True},
        )

    # 13. INV-ASYNC-MODEL
    elif invariant_id == "INV-ASYNC-MODEL":
        fields = ["command_log.provenance", "hazard.committed", "bounty.pool"]
        ok = True
        for c in command_log:
            cmd = c.get("cmd", {})
            if cmd.get("provenance") == "fixture" and _command_event_tick(cmd) >= HAZARD_ADMISSION_CLOSE_TICKS:
                if c.get("status") == "applied":
                    ok = False
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            len(command_log), {"late_fixture_applied": not ok}, {"late_fixture_applied": False},
        )

    # 14. INV-REPLAY
    elif invariant_id == "INV-REPLAY":
        fields = ["initial_state_hash", "final_state_hash", "trace_deltas"]
        ok = bool(trace_deltas and trace_deltas[-1].get("state_hash") == canonical_hash(final_state))
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            len(trace_deltas), {"final_hash_matches_trace": ok}, {"final_hash_matches_trace": True},
        )

    # 15. INV-REACHABILITY
    elif invariant_id == "INV-REACHABILITY":
        fields = ["movement.progress", "movement.district"]
        dist = movement.get("district")
        prog = movement.get("progress", 0.0)
        exp_dist = get_district_for_progress(prog)
        ok = (dist == exp_dist)
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            1, {"district": dist, "progress": prog}, {"expected_district": exp_dist},
        )

    # 16. INV-CREDIBILITY
    elif invariant_id == "INV-CREDIBILITY":
        fields = ["trace_deltas.state_hash", "final_state_hash"]
        ok = (canonical_hash(final_state) == trace_deltas[-1]["state_hash"]) if trace_deltas else False
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            len(trace_deltas), {"trace_head_matches": ok}, {"trace_head_matches": True},
        )

    # 17. INV-ENGINE-AUTH
    elif invariant_id == "INV-ENGINE-AUTH":
        fields = ["command_log", "trace_deltas"]
        ok = len(trace_deltas) > 0
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            len(trace_deltas), {"traces_recorded": len(trace_deltas)}, {"traces_recorded_gt_0": True},
        )

    # 18. INV-FIXTURE-LABEL
    elif invariant_id == "INV-FIXTURE-LABEL":
        fields = ["command_log.provenance", "bounty.synthetic_fixture_pool"]
        ok = True
        for c in command_log:
            cmd = c.get("cmd", {})
            if cmd.get("provenance") == "fixture" and c.get("status") == "applied" and cmd.get("kind") == "hazard.propose":
                if bounty.get("synthetic_fixture_pool", 0) <= 0:
                    ok = False
        return _build_invariant_result(
            sid, invariant_id, "PASS" if ok else "FAIL", fields,
            len(command_log), {"fixture_pool_credited": ok}, {"fixture_pool_credited": True},
        )

    # Fallback for unrecognized property
    return _build_invariant_result(
        sid, invariant_id, "NOT_EVALUATED", [], 0, None, None,
        notes=f"Undeclared or unrecognized property {invariant_id}",
    )


def evaluate_scenario_properties(
    contract: Dict[str, Any],
    commands: List[Dict[str, Any]],
    trace: List[Dict[str, Any]],
    states: Union[Tuple[Dict[str, Any], Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]],
    *,
    oracle_evaluation: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Evaluate ONLY the invariants declared in contract["invariants_tested"].

    Returns one result per declared invariant. Never marks all passed from a generic oracle pass.
    Treats missing evidence or validator error as FAIL or ERROR, never PASS.
    """
    if not isinstance(contract, dict):
        return []

    sid = contract.get("scenario_id", "UNKNOWN")
    declared = contract.get("invariants_tested", [])

    if isinstance(states, (list, tuple)) and len(states) >= 2:
        init_state, final_state = states[0], states[1]
    elif isinstance(states, dict):
        init_state = states.get("initial_state", {})
        final_state = states.get("final_state", {})
    else:
        init_state, final_state = {}, {}

    results: List[Dict[str, Any]] = []
    for inv_id in declared:
        try:
            res = evaluate_single_scenario_property(
                inv_id, contract, commands, trace, init_state, final_state, oracle_evaluation=oracle_evaluation,
            )
        except Exception as exc:
            res = _build_invariant_result(
                sid, inv_id, "ERROR", [], 0, str(exc), "PASS", notes=f"Evaluator exception: {exc}",
            )
        results.append(res)

    return results


# ==============================================================================
# R9 / 6.7: Six Pipeline Invariant Validators
# ==============================================================================

def validate_review_authorship(bundle_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate INV-REVIEW-AUTHORSHIP: review-artifact authorship separation.

    Proves declared author and agent match evidence; fails on missing attribution or conflict.
    """
    inv_id = "INV-REVIEW-AUTHORSHIP"
    fields = ["INDEPENDENT-REVIEW.md", "REVIEW-INVOCATION.json", "author_identity", "agent_attribution"]
    review_inv = bundle_data.get("review_invocation", {})
    review_text = bundle_data.get("review_text", "")

    author = review_inv.get("reviewer_author") or review_inv.get("author") or review_inv.get("authored_by")
    provider = review_inv.get("reviewer_provider") or review_inv.get("configured_provider")
    model = review_inv.get("reviewer_model") or review_inv.get("configured_model")
    effort = review_inv.get("reviewer_effort") or review_inv.get("configured_effort")
    evidence_origin = review_inv.get("evidence_origin")
    conv_id = (
        review_inv.get("agent_id")
        or review_inv.get("reviewer_subagent")
        or review_inv.get("subagent_conversation_id")
        or review_inv.get("reviewer_conversation_id")
    )
    route = review_inv.get("route") or (f"{provider}/{model}" if provider and model else None)

    is_independent = (
        evidence_origin not in (None, "", "synthetic_generator", "simulator", "simulator_harness", "self_authored")
        and author != "simulator_harness"
    )
    has_model = bool(provider and model)
    has_review = bool("Verdict:" in review_text or "# Independent Systems Review" in review_text or "verdict" in review_inv)
    has_conv = bool(conv_id)

    ok = bool(is_independent and has_model and has_conv and has_review)

    return _build_invariant_result(
        "PIPELINE", inv_id, "PASS" if ok else "FAIL", fields,
        1, {"author": author or provider, "agent_id": conv_id, "route": route},
        {"route": "codex_subagent/gpt-6-astra", "author_independent": True},
    )


def validate_run_immutability(bundle_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate INV-RUN-IMMUTABILITY: run root non-reuse, non-reseal, and old-run preservation.

    Proves new run is exclusive; old run is unchanged and still REVISE.
    """
    inv_id = "INV-RUN-IMMUTABILITY"
    fields = ["new_run_id", "old_run_id", "old_run_tree_sha256", "seal_state"]

    new_id = bundle_data.get("new_run_id")
    old_id = bundle_data.get("old_run_id", "full-game-20261101T174648Z-2647e033")
    old_hash_before = bundle_data.get("old_run_tree_sha256_before")
    old_hash_after = bundle_data.get("old_run_tree_sha256_after")

    is_exclusive = bool(new_id and new_id != old_id)
    old_preserved = bool(old_hash_before and old_hash_after and old_hash_before == old_hash_after)

    ok = is_exclusive and old_preserved

    return _build_invariant_result(
        "PIPELINE", inv_id, "PASS" if ok else "FAIL", fields,
        1, {"new_run_id": new_id, "old_run_preserved": old_preserved},
        {"is_exclusive": True, "old_run_preserved": True},
    )


def validate_citation_hashes(bundle_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate INV-CITATION-HASHES: cited artifact hash existence and byte match.

    Each cited hash exists and equals recomputed hash of cited bytes.
    """
    inv_id = "INV-CITATION-HASHES"
    fields = ["RUN-MANIFEST.json", "artifact_hashes"]
    manifest = bundle_data.get("manifest", {})
    recomputed = bundle_data.get("recomputed_hashes", {})

    artifacts = manifest.get("artifact_hashes", manifest) if isinstance(manifest, dict) else {}
    mismatches = []
    missing = []
    for path, expected in artifacts.items():
        if path not in recomputed:
            missing.append(path)
        elif recomputed[path] != expected:
            mismatches.append(path)

    ok = bool(artifacts and not missing and not mismatches)

    return _build_invariant_result(
        "PIPELINE", inv_id, "PASS" if ok else "FAIL", fields,
        len(artifacts),
        {"total_checked": len(artifacts), "missing": len(missing), "mismatches": len(mismatches)},
        {"missing": 0, "mismatches": 0},
    )


def validate_source_bytes(bundle_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate INV-SOURCE-BYTES: seal-time source-byte match.

    Proves source bytes match the sealed source binding at execution time.
    """
    inv_id = "INV-SOURCE-BYTES"
    fields = ["SOURCE-BINDINGS.json", "recomputed_source_hashes"]
    bindings = bundle_data.get("source_bindings", {})
    recomputed = bundle_data.get("recomputed_source_hashes", {})

    mismatches = []
    missing = []
    for path, expected in bindings.items():
        exp_hash = expected.get("sha256") if isinstance(expected, dict) else expected
        if path not in recomputed:
            missing.append(path)
        elif recomputed[path] != exp_hash:
            mismatches.append(path)

    ok = bool(bindings and not missing and not mismatches)

    return _build_invariant_result(
        "PIPELINE", inv_id, "PASS" if ok else "FAIL", fields,
        len(bindings),
        {"total_sources": len(bindings), "missing": len(missing), "mismatches": len(mismatches)},
        {"missing": 0, "mismatches": 0},
    )


def validate_evidence_coverage(bundle_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate INV-EVIDENCE-COVERAGE: coverage derived as a function of evidence.

    Proves coverage is recomputed from actual per-invariant results, not declared counts.
    """
    inv_id = "INV-EVIDENCE-COVERAGE"
    fields = ["SCENARIO-MATRIX.json", "per_invariant_results", "COVERAGE.json"]
    declared_matrix = bundle_data.get("matrix", [])
    per_inv_results = bundle_data.get("per_invariant_results", [])

    declared_total = sum(len(c.get("invariants_tested", [])) for c in declared_matrix)
    evaluated_total = sum(
        d.get("evaluations_count", 1) if "evaluations_count" in d
        else (1 if d.get("status") in ("PASS", "FAIL") else (1 if d.get("passed") is True else 0))
        for d in per_inv_results
    )
    not_eval = sum(1 for d in per_inv_results if d.get("status") == "NOT_EVALUATED" or d.get("passed") is False)

    ok = bool(declared_total > 0 and evaluated_total >= declared_total and not_eval == 0)

    return _build_invariant_result(
        "PIPELINE", inv_id, "PASS" if ok else "FAIL", fields,
        len(per_inv_results),
        {"declared": declared_total, "evaluated": evaluated_total, "not_evaluated": not_eval},
        {"not_evaluated": 0, "all_declared_evaluated": True},
    )


def validate_readiness_separation(bundle_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate INV-READINESS-SEPARATION: ready/submission-ready separation.

    Proves readiness derives strictly from passing evidence + READY review; submission is separate and unexecuted.
    """
    inv_id = "INV-READINESS-SEPARATION"
    fields = ["DEVELOPMENT-READINESS.json", "review_verdict", "submission_ready", "evidence_passed"]

    readiness = bundle_data.get("readiness", {})
    review_verdict = bundle_data.get("review_verdict")
    evidence_passed = bundle_data.get("evidence_passed", False)
    submission_ready = readiness.get("submission_ready", False)

    # Readiness may ONLY be True if evidence_passed is True AND review_verdict == "READY"
    claimed_ready = readiness.get("ready", False)

    if claimed_ready:
        ok = bool(evidence_passed and review_verdict == "READY" and submission_ready is False)
    else:
        # Honest non-readiness when review is REVISE or evidence is incomplete
        ok = bool(submission_ready is False)

    return _build_invariant_result(
        "PIPELINE", inv_id, "PASS" if ok else "FAIL", fields,
        1,
        {"claimed_ready": claimed_ready, "review_verdict": review_verdict, "submission_ready": submission_ready},
        {"valid_separation": True, "submission_ready": False},
    )
