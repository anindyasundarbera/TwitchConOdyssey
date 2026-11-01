"""Complete-game deterministic simulation orchestrator and two-stage evidence pipeline.

Implements the remediated two-stage simulation and finalization contract:
- Stage 1 (`--stage simulate`):
  - Allocates an exclusive new run directory (`exist_ok=False`), never overwriting the
    preserved rejected run (`full-game-20261101T102226Z-a8e33043`).
  - Freezes and hashes `SCENARIO-MATRIX.json` (46 concrete pre-execution contracts and
    independent expected oracles) and `CORPUS-MANIFEST.json` before tick 0.
  - Executes all 46 scenarios through `FullGameSimulator` / `execute_frozen_scenario`,
    emitting substantive `commands/<id>.json`, `traces/<id>.jsonl` (`state_diff` chains),
    and `state-hashes/<id>.json`, verified by `verify_scenario_trace_integrity`.
  - Mechanically derives `FEATURE-INVENTORY.json` and `COVERAGE.json` via
    `derive_feature_statuses` (`FEAT-14-READABILITY-AND-HUD` is `not_observed` in
    headless deterministic simulation).
  - Writes `ISSUES.json` (3 closed issues with real 64-hex SHA-256 `resolution_hash`)
    and `REVIEW-PACKET.md`, stopping before `INDEPENDENT-REVIEW.md`,
    `DEVELOPMENT-READINESS.json`, or `RUN-MANIFEST.json`.
- Stage 2 (`--stage finalize`):
  - Verifies `INDEPENDENT-REVIEW.md` and `REVIEW-INVOCATION.json` via
    `verify_independent_review_artifact`.
  - Writes `MODEL-USAGE.json`, computes `DEVELOPMENT-READINESS.json` via
    `compute_development_readiness`, writes `README.md`, and seals `RUN-MANIFEST.json` last.
"""

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from coordination.canonical_commands import make_command, validate_command
from coordination.content_cache import canonical_hash, detached, require_hash, validate_json
from coordination.evidence_pipeline import (
    AUDIT_SEVERITIES,
    AUDIT_VALIDATORS,
    AUTHORIZATION_TOKEN,
    PIPELINE_INVARIANTS,
    PRESERVED_REJECTED_RUN_ID,
    compute_development_readiness,
    create_immutable_run_root,
    derive_feature_statuses,
    derive_run_id,
    file_sha256,
    prepare_pending_review_packet,
    seal_run_manifest,
    verify_independent_review_artifact,
    verify_scenario_trace_integrity,
    verify_source_bindings,
    write_exclusive_json,
    write_exclusive_text,
)
from coordination.full_game_simulator import (
    BASE_SPEED,
    DISTRICTS,
    GENERAL_INPUT_CLOSE_TICKS,
    HAZARD_ADMISSION_CLOSE_TICKS,
    HZ,
    MATCH_DEADLINE_TICKS,
    PLANNING_TICKS,
    RESOLUTION_TICKS,
    REWARD_TICKS,
    TURN_TICKS,
    FullGameSimulator,
    ScenarioContract,
    evaluate_independent_oracles,
    execute_frozen_scenario,
    freeze_scenario_matrix,
    replay_command_stream,
    validate_scenario_contract,
)
from coordination.scenario_inputs import (
    build_corpus_manifest,
    generate_viewer_corpus,
    validate_corpus,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "artifacts/simulations/full-game"

AUTHORITATIVE_INPUTS = [
    "config/directive-policy.json",
    "config/model-policy.json",
    "docs/planning/STATUS.md",
    "docs/planning/CONTEXT-v2.md",
    "docs/planning/GAMEPLAN-v2.md",
    "docs/planning/gameplan-v2.json",
    "docs/planning/DECISIONS.md",
    "docs/planning/S1-SIMULATION-PROFILE.md",
    "docs/planning/S1-ASTRA-REVIEW.md",
    "docs/planning/S1-ASTRA-REVIEW-RESPONSE.md",
    "docs/planning/SAN-DIEGO-ROUTE.md",
    "docs/planning/research/S1-PLATFORM-EVIDENCE.md",
    "docs/planning/research/S1-SYSTEMS-EVIDENCE.md",
]

CODEBASE_SOURCES = [
    "coordination/canonical_commands.py",
    "coordination/content_cache.py",
    "coordination/context_contract.py",
    "coordination/evidence_pipeline.py",
    "coordination/full_game_simulator.py",
    "coordination/model_router.py",
    "coordination/plan_rehearsal.py",
    "coordination/run_full_game_simulation.py",
    "coordination/review_boundary.py",
    "coordination/scenario_inputs.py",
    "coordination/state_transport.py",
    "schemas/action.json",
    "schemas/validate.py",
    "server/engine.py",
    "server/app.py",
    "server/replay.py",
    "storage/store.py",
    "harness/run.py",
]

INVARIANTS = [
    {"id": "INV-REPLAY", "name": "Deterministic replay produces identical canonical final and boundary hashes"},
    {"id": "INV-ENGINE-AUTH", "name": "Engine alone owns physics and state mutation; models/fixtures cannot directly alter physics"},
    {"id": "INV-ASYNC-MODEL", "name": "Rendering/simulation never waits for an external model provider"},
    {"id": "INV-COMMAND-VAL", "name": "No late, duplicate, paused, unlinked, or invalid command mutates state"},
    {"id": "INV-ACCOUNT-INFLUENCE", "name": "Every eligible account contributes at most one influence per turn across channels"},
    {"id": "INV-BOT-ISOLATION", "name": "Bots/fixtures never impersonate humans, affect human quorum, create Hype, or receive live Hype"},
    {"id": "INV-HAZARD-BIND", "name": "Hazard commitment, warning, counter, and bounty increment share one committed ID"},
    {"id": "INV-HAZARD-DEPEND", "name": "No committed hazard means no warning, obstacle, or bounty increment"},
    {"id": "INV-SAFETY-CAPS", "name": "Safety caps prevent permanent control loss, stun lock, stacking, refresh, unbounded harm, or unavoidable death"},
    {"id": "INV-REACHABILITY", "name": "Every admitted obstacle state is avoidable under the selected control/geometry contract"},
    {"id": "INV-EFFECT-ORDER", "name": "clear_lane removal precedes collision; collision precedes delivery; deadline precedes equality-time delivery"},
    {"id": "INV-SETTLEMENT-ONCE", "name": "Settlement occurs at most once, only at terminal delivery, with exact selected arithmetic"},
    {"id": "INV-WIPE-CLEAN", "name": "Wipe/deadline/build-drop settles zero and new match carries no state"},
    {"id": "INV-MAX-TURNS", "name": "No fourth turn begins; match terminates strictly by deadline or prior delivery"},
    {"id": "INV-PAUSE-CLEAN", "name": "Pause produces no catch-up ticks and cannot suspend a reached deadline"},
    {"id": "INV-FIXTURE-LABEL", "name": "Fixture/live modes use the same canonical command schema and remain visibly distinguishable"},
    {"id": "INV-HOTFIX-SAFETY", "name": "Data/rules patches cannot relax hard invariants or activate outside a validated boundary"},
    {"id": "INV-CREDIBILITY", "name": "No unsupported promotional or live-service claim is emitted"},
]


def build_source_bindings() -> Dict[str, Any]:
    """Hash authoritative planning inputs and codebase sources."""
    bindings: Dict[str, Any] = {}
    for rel_path in AUTHORITATIVE_INPUTS:
        full_path = ROOT / rel_path
        bindings[rel_path] = {
            "path": rel_path,
            "sha256": file_sha256(full_path),
            "size_bytes": full_path.stat().st_size,
            "role": "authoritative_planning_input",
        }
    for rel_path in CODEBASE_SOURCES:
        full_path = ROOT / rel_path
        bindings[rel_path] = {
            "path": rel_path,
            "sha256": file_sha256(full_path),
            "size_bytes": full_path.stat().st_size,
            "role": "codebase_source",
        }
    return detached(bindings)


def build_feature_specs() -> List[Dict[str, Any]]:
    """Return declarative feature specifications without hardcoded pass/covered claims."""
    specs = [
        {
            "feature_id": "FEAT-01-SAN-DIEGO-ROUTE",
            "name": "Complete Stylized San Diego Journey",
            "category": "route_and_world",
            "source_paths": ["docs/planning/SAN-DIEGO-ROUTE.md", "docs/planning/GAMEPLAN-v2.md"],
            "authority_owner": "engine",
            "simulation_method": "deterministic_progress_and_district_mapping",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "avatar traverses Little Italy, Waterfront, Gaslamp, Convention Center, Main Stage strictly in order",
        },
        {
            "feature_id": "FEAT-02-STREAMER-CONTROL",
            "name": "Auto-Forward Three-Lane Streamer Control",
            "category": "controls",
            "source_paths": ["docs/planning/S1-SIMULATION-PROFILE.md#D-01", "docs/planning/GAMEPLAN-v2.md#D-01"],
            "authority_owner": "streamer_input_to_engine",
            "simulation_method": "fixed_step_linear_interpolation",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "3 lanes, 0.5s transition, edge clamping, opposite cancel, active through plan/res/reward, no confirmation/override",
        },
        {
            "feature_id": "FEAT-03-CADENCE-AND-CLOCK",
            "name": "Cadence, Active Deadline, and Cutoff Ordering",
            "category": "clock_and_lifecycle",
            "source_paths": ["docs/planning/S1-SIMULATION-PROFILE.md#D-05", "docs/planning/GAMEPLAN-v2.md#D-05"],
            "authority_owner": "engine_clock",
            "simulation_method": "integer_tick_monotonic_schedule",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "20s plan, 5s res, exactly 5.0s reward, 90s deadline, total ordering: deadline->close->pause->commands->effects",
        },
        {
            "feature_id": "FEAT-04-AUDIENCE-ACCOUNTING",
            "name": "Audience Ingestion, Account Linking, and Quorum",
            "category": "audience_and_fairness",
            "source_paths": ["docs/planning/S1-SIMULATION-PROFILE.md#D-03", "docs/planning/GAMEPLAN-v2.md#D-03"],
            "authority_owner": "audience_ledger",
            "simulation_method": "atomic_first_receipt_and_frozen_roster",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "account-level linking, max 1 influence/turn across channels, K=2 squads, ceil(0.60*N) quorum, ties=abstain, bot=0",
        },
        {
            "feature_id": "FEAT-05-HAZARD-AND-SURVIVAL",
            "name": "Human-Origin Hazard Commitment and Survival Contract",
            "category": "hazards_and_safety",
            "source_paths": ["docs/planning/S1-SIMULATION-PROFILE.md#D-02", "docs/planning/GAMEPLAN-v2.md#D-02"],
            "authority_owner": "engine_hazard_adjudicator",
            "simulation_method": "half_open_admission_and_collision_bounding",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "commit < t=15s, warning [15,20s), clear_lane removes before collision, 20% slowdown for 2s, 0 HP/stun, cap 6s/match",
        },
        {
            "feature_id": "FEAT-06-FICTIONAL-HYPE-REWARD",
            "name": "Fictional Hype Creation, Halving, and Terminal Settlement",
            "category": "rewards_and_economy",
            "source_paths": ["docs/planning/S1-SIMULATION-PROFILE.md#D-04", "docs/planning/GAMEPLAN-v2.md#D-04"],
            "authority_owner": "reward_settler",
            "simulation_method": "exact_rational_fraction_arithmetic",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "0 start, +20/accepted human hazard < t=15, cap 60, single collision halves total once, wipe settles 0, exact rational shares",
        },
        {
            "feature_id": "FEAT-07-OPENAI-CHAT-TO-ACTION",
            "name": "OpenAI Chat-to-Action Validation and Asynchronous Fallback",
            "category": "ai_integration",
            "source_paths": ["docs/planning/GAMEPLAN-v2.md", "config/model-policy.json"],
            "authority_owner": "adapter_and_local_validator",
            "simulation_method": "fixture_schedule_and_schema_validator",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "strict schemas, local revalidation, timeout min(dispatch+2s, cutoff), late discard, deterministic fallback",
        },
        {
            "feature_id": "FEAT-08-CODEX-LIVE-HOTFIX",
            "name": "Codex Live Hotfix Booth Data-Only Patching",
            "category": "booths_and_tooling",
            "source_paths": ["docs/planning/GAMEPLAN-v2.md", "docs/planning/DECISIONS.md#DECISION-02"],
            "authority_owner": "hotfix_verifier",
            "simulation_method": "turn_boundary_patch_adjudication",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "data/rules only, signature verification, turn-boundary activation, cannot relax safety invariants, rollback on failure",
        },
        {
            "feature_id": "FEAT-09-TWITCH-BOOTH",
            "name": "Twitch Booth Moderation-Forcefield Fiction",
            "category": "booths_and_tooling",
            "source_paths": ["docs/planning/GAMEPLAN-v2.md", "docs/planning/gameplan-v2.json"],
            "authority_owner": "diegetic_booth_manager",
            "simulation_method": "waypoint_trigger_and_hazard_conversion",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "triggers at progress 35.0% without minting live participant Hype from fixtures, clearly labeled fiction",
        },
        {
            "feature_id": "FEAT-10-AWS-IVS-BOOTH",
            "name": "AWS / Amazon IVS Booth Scale-Boost Fiction",
            "category": "booths_and_tooling",
            "source_paths": ["docs/planning/GAMEPLAN-v2.md", "docs/planning/research/S1-PLATFORM-EVIDENCE.md"],
            "authority_owner": "diegetic_booth_manager",
            "simulation_method": "speed_lane_acceleration_and_offline_fallback",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "+10% speed boost for up to 2s at progress 80.0%, graceful fallback when offline, no unsupported sponsorship claims",
        },
        {
            "feature_id": "FEAT-11-OFFLINE-FIXTURE-DRIVER",
            "name": "Offline Fixture Driver, Equivalence, and Recovery",
            "category": "resilience_and_failover",
            "source_paths": ["docs/planning/GAMEPLAN-v2.md", "docs/planning/DECISIONS.md#DECISION-01"],
            "authority_owner": "engine_transport_layer",
            "simulation_method": "replay_verification_and_state_hash_comparison",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "live-fixture and offline-fixture produce identical state hashes; safe phase-boundary failover and hash-verified recovery",
        },
        {
            "feature_id": "FEAT-12-BULLET-TIME-PRESENTATION",
            "name": "Bullet-Time Matrix Freeze Presentation Alignment",
            "category": "presentation_and_demo",
            "source_paths": ["docs/planning/GAMEPLAN-v2.md", "docs/planning/S1-SIMULATION-PROFILE.md"],
            "authority_owner": "presentation_layer",
            "simulation_method": "client_interpolation_against_authoritative_ticks",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "presentation slowdown state without stopping authoritative 20 Hz loop or extending real 90s deadline; visual overlay render capture tracked separately",
        },
        {
            "feature_id": "FEAT-13-ADAPTIVE-AUDIO",
            "name": "Adaptive Audio State Machine and Telemetry Cues",
            "category": "audio_and_feedback",
            "source_paths": ["docs/planning/GAMEPLAN-v2.md", "docs/planning/gameplan-v2.json"],
            "authority_owner": "audio_state_machine",
            "simulation_method": "discrete_state_transitions_on_engine_events",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "states: crisis, bullet_time, solution, victory, wipe; acoustic output and voiceover intelligibility tracked separately",
        },
        {
            "feature_id": "FEAT-14-READABILITY-AND-HUD",
            "name": "Broadcast and Mobile Readability Architecture",
            "category": "ui_and_broadcast",
            "source_paths": ["docs/planning/GAMEPLAN-v2.md#D-01", "docs/planning/S1-SIMULATION-PROFILE.md#D-01"],
            "authority_owner": "hud_formatter",
            "simulation_method": "minimal_telemetry_hud_projection",
            "required_evidence_kind": "render_capture_and_mobile_viewport",
            "oracle": "requires rendered browser/mobile viewport capture and compressed-video readability observation; not observed in headless simulation",
        },
        {
            "feature_id": "FEAT-15-PUBLIC-DEMO-TIMELINE",
            "name": "Three-Minute Public Demo Narrative and Claim Verification",
            "category": "presentation_and_demo",
            "source_paths": ["docs/planning/GAMEPLAN-v2.md", "docs/planning/DECISIONS.md#DECISION-03"],
            "authority_owner": "demo_director",
            "simulation_method": "timed_scenario_execution",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "timed demo state narrative, verified fixture labels, truthful CTA claims; rendered 3-minute video capture tracked separately",
        },
        {
            "feature_id": "FEAT-16-SECURITY-AND-PROVENANCE",
            "name": "Security, Privacy, Provenance, and Authoritative Writer",
            "category": "architecture_and_security",
            "source_paths": ["docs/planning/GAMEPLAN-v2.md", "coordination/canonical_commands.py"],
            "authority_owner": "security_perimeter",
            "simulation_method": "envelope_validation_and_size_capping",
            "required_evidence_kind": "deterministic_state_and_commands",
            "oracle": "single authoritative writer, detached envelopes, explicit human/bot/fixture provenance, no client physics",
        },
    ]
    return detached(specs)


build_feature_inventory = build_feature_specs


def _cmd_spec(
    tick: int,
    kind: str,
    actor_id: str,
    provenance: str,
    sequence: int,
    payload: Dict[str, Any],
    *,
    logical_tick: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "submit_at_tick": tick,
        "logical_tick": tick if logical_tick is None else logical_tick,
        "kind": kind,
        "actor_id": actor_id,
        "provenance": provenance,
        "sequence": sequence,
        "payload": payload,
    }


def build_frozen_scenario_contracts() -> List[Dict[str, Any]]:
    """Build all 46 pre-execution ScenarioContracts with concrete inputs and expected oracles."""
    roster_10 = [f"user_{i}" for i in range(10)]
    roster_7 = [f"v_{i}" for i in range(7)]
    roster_5 = [f"u_{i}" for i in range(5)]

    contracts: List[Dict[str, Any]] = [
        # --- Category 1: nominal_e2e (5 scenarios) ---
        {
            "scenario_id": "SCEN-E2E-01",
            "category": "nominal_e2e",
            "description": "Full 3-turn San Diego journey with avoided and crowd-cleared hazards reaching Main Stage before 90s deadline",
            "seed": 101,
            "initial_lane": 1,
            "initial_roster": roster_10,
            "scheduled_commands": [
                _cmd_spec(100, "hazard.propose", "user_0", "human", 1, {"hazard_id": "haz_t1", "lane": 1}),
                _cmd_spec(200, "streamer.steer", "streamer", "human", 2, {"direction": "left"}),
                _cmd_spec(700, "hazard.propose", "user_1", "human", 3, {"hazard_id": "haz_t2", "lane": 1}),
                *[
                    _cmd_spec(750 + i, "viewer.counter", f"user_{i}", "human", 4 + i, {"hazard_id": "haz_t2", "counter": "clear_lane"})
                    for i in range(7)
                ],
                _cmd_spec(1300, "hazard.propose", "user_2", "human", 20, {"hazard_id": "haz_t3", "lane": 1}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": [
                "FEAT-01-SAN-DIEGO-ROUTE",
                "FEAT-02-STREAMER-CONTROL",
                "FEAT-03-CADENCE-AND-CLOCK",
                "FEAT-04-AUDIENCE-ACCOUNTING",
                "FEAT-05-HAZARD-AND-SURVIVAL",
                "FEAT-06-FICTIONAL-HYPE-REWARD",
            ],
            "invariants_tested": [
                "INV-REPLAY",
                "INV-ENGINE-AUTH",
                "INV-EFFECT-ORDER",
                "INV-SETTLEMENT-ONCE",
                "INV-MAX-TURNS",
                "INV-HAZARD-BIND",
            ],
            "expected_oracle": {
                "expected_final_status": "delivered",
                "expected_final_tick": 1760,
                "expected_final_turn": 3,
                "expected_lane": 0,
                "expected_pool": 60,
                "expected_synthetic_fixture_pool": 0,
                "expected_collisions_total": 0,
                "expected_collision_halved": False,
                "expected_booths_visited": ["aws_booth", "codex_booth", "twitch_booth"],
                "expected_command_statuses": ["applied"] * 11,
                "expected_settlement": {
                    "status": "delivered",
                    "total_hype": 60,
                    "streamer_share": 30,
                    "audience_share_total": 30,
                    "audience_withheld": 0,
                    "eligible_voters_count": 7,
                    "per_voter_rational": "30/7",
                    "settled_once": True,
                },
                "expected_boundary_labels": ["init", "turn_2_start", "turn_3_start", "terminal_delivery"],
            },
        },
        {
            "scenario_id": "SCEN-E2E-02",
            "category": "nominal_e2e",
            "description": "Complete match wipe at exact 90s (1800-tick) deadline settling zero Hype",
            "seed": 102,
            "initial_lane": 1,
            "base_speed_override": 0.5,
            "initial_roster": ["user_0", "user_1"],
            "scheduled_commands": [
                _cmd_spec(50, "hazard.propose", "user_0", "human", 1, {"hazard_id": "haz_wipe_t1", "lane": 1}),
                _cmd_spec(60, "streamer.steer", "streamer", "human", 2, {"direction": "left"}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": [
                "FEAT-03-CADENCE-AND-CLOCK",
                "FEAT-05-HAZARD-AND-SURVIVAL",
                "FEAT-06-FICTIONAL-HYPE-REWARD",
            ],
            "invariants_tested": ["INV-WIPE-CLEAN", "INV-MAX-TURNS", "INV-SETTLEMENT-ONCE"],
            "expected_oracle": {
                "expected_final_status": "wiped",
                "expected_final_tick": 1800,
                "expected_final_turn": 3,
                "expected_pool": 20,
                "expected_collisions_total": 0,
                "expected_command_statuses": ["applied", "applied"],
                "expected_settlement": {
                    "status": "wiped",
                    "reason": "deadline_reached",
                    "total_hype": 0,
                    "streamer_share": 0,
                    "audience_share_total": 0,
                    "audience_withheld": 20,
                    "settled_once": True,
                },
            },
        },
        {
            "scenario_id": "SCEN-E2E-03",
            "category": "nominal_e2e",
            "description": "Three hazard turns (avoided, crowd-cleared, collided) halving 60 Hype pool once to 30 at delivery",
            "seed": 103,
            "initial_lane": 1,
            "initial_roster": roster_10,
            "scheduled_commands": [
                _cmd_spec(50, "hazard.propose", "user_0", "human", 1, {"hazard_id": "h1", "lane": 1}),
                _cmd_spec(100, "streamer.steer", "streamer", "human", 2, {"direction": "left"}),
                _cmd_spec(650, "hazard.propose", "user_1", "human", 3, {"hazard_id": "h2", "lane": 1}),
                *[
                    _cmd_spec(700 + i, "viewer.counter", f"user_{i}", "human", 4 + i, {"hazard_id": "h2", "counter": "clear_lane"})
                    for i in range(7)
                ],
                _cmd_spec(1250, "hazard.propose", "user_2", "human", 20, {"hazard_id": "h3", "lane": 1}),
                _cmd_spec(1300, "streamer.steer", "streamer", "human", 21, {"direction": "right"}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": [
                "FEAT-01-SAN-DIEGO-ROUTE",
                "FEAT-02-STREAMER-CONTROL",
                "FEAT-05-HAZARD-AND-SURVIVAL",
                "FEAT-06-FICTIONAL-HYPE-REWARD",
            ],
            "invariants_tested": ["INV-SAFETY-CAPS", "INV-SETTLEMENT-ONCE", "INV-EFFECT-ORDER"],
            "expected_oracle": {
                "expected_final_status": "delivered",
                "expected_final_tick": 1768,
                "expected_final_turn": 3,
                "expected_lane": 1,
                "expected_pool": 60,
                "expected_collisions_total": 1,
                "expected_collision_halved": True,
                "expected_command_statuses": ["applied"] * 12,
                "expected_settlement": {
                    "status": "delivered",
                    "total_hype": 30,
                    "original_pool": 60,
                    "collision_halved": True,
                    "streamer_share": 15,
                    "audience_share_total": 15,
                    "eligible_voters_count": 7,
                    "per_voter_rational": "15/7",
                    "settled_once": True,
                },
            },
        },
        {
            "scenario_id": "SCEN-E2E-04",
            "category": "nominal_e2e",
            "description": "Full public demo timeline visiting Twitch, Codex, and AWS/IVS booths with Bullet-Time state transition",
            "seed": 104,
            "initial_lane": 0,
            "initial_roster": ["viewer_a", "viewer_b"],
            "scheduled_commands": [
                _cmd_spec(240, "presentation.bullet_time", "demo_director", "fixture", 1, {"active": True, "freeze_tick": 240, "factor": 0.25}),
                _cmd_spec(300, "booth.hotfix", "codex_booth", "fixture", 2, {"patch_version": 1, "expiry_tick": 1800, "patch_data": {"slowdown_fraction": 0.15}, "signature": "CODEX_BOOTH_TRUSTED_V1"}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": [
                "FEAT-01-SAN-DIEGO-ROUTE",
                "FEAT-08-CODEX-LIVE-HOTFIX",
                "FEAT-09-TWITCH-BOOTH",
                "FEAT-10-AWS-IVS-BOOTH",
                "FEAT-12-BULLET-TIME-PRESENTATION",
                "FEAT-13-ADAPTIVE-AUDIO",
                "FEAT-15-PUBLIC-DEMO-TIMELINE",
            ],
            "invariants_tested": ["INV-CREDIBILITY", "INV-ENGINE-AUTH", "INV-HOTFIX-SAFETY"],
            "expected_oracle": {
                "expected_final_status": "delivered",
                "expected_final_tick": 1760,
                "expected_booths_visited": ["aws_booth", "codex_booth", "twitch_booth"],
                "expected_audio_state": "victory",
                "expected_applied_hotfix_version": 1,
                "expected_hotfix_rules": {"slowdown_fraction": 0.15, "slowdown_duration_ticks": 40},
                "expected_command_statuses": ["applied", "applied"],
            },
        },
        {
            "scenario_id": "SCEN-E2E-05",
            "category": "nominal_e2e",
            "description": "Public demo wipe variant with synthetic fixture hazard isolated from live participant pool",
            "seed": 105,
            "initial_lane": 1,
            "base_speed_override": 0.4,
            "initial_roster": ["viewer_a"],
            "scheduled_commands": [
                _cmd_spec(100, "hazard.propose", "fixture_driver", "fixture", 1, {"hazard_id": "h_demo_wipe", "lane": 1}),
                _cmd_spec(120, "streamer.steer", "streamer", "human", 2, {"direction": "left"}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": [
                "FEAT-13-ADAPTIVE-AUDIO",
                "FEAT-15-PUBLIC-DEMO-TIMELINE",
            ],
            "invariants_tested": ["INV-WIPE-CLEAN", "INV-BOT-ISOLATION", "INV-CREDIBILITY"],
            "expected_oracle": {
                "expected_final_status": "wiped",
                "expected_final_tick": 1800,
                "expected_pool": 0,
                "expected_synthetic_fixture_pool": 20,
                "expected_audio_state": "wipe",
                "expected_command_statuses": ["applied", "applied"],
                "expected_settlement": {
                    "status": "wiped",
                    "total_hype": 0,
                    "original_pool": 0,
                    "synthetic_fixture_hype_illustrated": 20,
                    "live_participant_minted_from_fixture": False,
                },
            },
        },
        # --- Category 2: control_and_safety (9 scenarios) ---
        {
            "scenario_id": "SCEN-CTRL-01",
            "category": "control_and_safety",
            "description": "Three-lane geometry traversal from right lane (2) through center (1) to left lane (0)",
            "seed": 201,
            "initial_lane": 2,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(0, "streamer.steer", "streamer", "human", 1, {"direction": "left"}),
                _cmd_spec(12, "streamer.steer", "streamer", "human", 2, {"direction": "left"}),
            ],
            "steps_to_run": 25,
            "features_exercised": ["FEAT-02-STREAMER-CONTROL"],
            "invariants_tested": ["INV-ENGINE-AUTH", "INV-COMMAND-VAL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 25,
                "expected_lane": 0,
                "expected_command_statuses": ["applied", "applied"],
            },
        },
        {
            "scenario_id": "SCEN-CTRL-02",
            "category": "control_and_safety",
            "description": "Same-tick opposite steering inputs cancel cleanly without lateral displacement",
            "seed": 202,
            "initial_lane": 1,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(0, "streamer.steer", "streamer", "human", 1, {"direction": "cancel"}),
            ],
            "steps_to_run": 5,
            "features_exercised": ["FEAT-02-STREAMER-CONTROL"],
            "invariants_tested": ["INV-COMMAND-VAL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 5,
                "expected_lane": 1,
                "expected_command_statuses": ["applied"],
            },
        },
        {
            "scenario_id": "SCEN-CTRL-03",
            "category": "control_and_safety",
            "description": "Edge lane clamping rejects left from lane 0 and right from lane 2 without wrapping",
            "seed": 203,
            "initial_lane": 0,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(0, "streamer.steer", "streamer", "human", 1, {"direction": "left"}),
                _cmd_spec(1, "streamer.steer", "streamer", "human", 2, {"direction": "right"}),
                _cmd_spec(12, "streamer.steer", "streamer", "human", 3, {"direction": "right"}),
                _cmd_spec(23, "streamer.steer", "streamer", "human", 4, {"direction": "right"}),
            ],
            "steps_to_run": 25,
            "features_exercised": ["FEAT-02-STREAMER-CONTROL"],
            "invariants_tested": ["INV-COMMAND-VAL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 25,
                "expected_lane": 2,
                "expected_command_statuses": ["rejected", "applied", "applied", "rejected"],
            },
        },
        {
            "scenario_id": "SCEN-CTRL-04",
            "category": "control_and_safety",
            "description": "In-flight 0.5s (10-tick) transition lockout rejects overlapping steering commands",
            "seed": 204,
            "initial_lane": 1,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(0, "streamer.steer", "streamer", "human", 1, {"direction": "left"}),
                _cmd_spec(1, "streamer.steer", "streamer", "human", 2, {"direction": "right"}),
                _cmd_spec(5, "streamer.steer", "streamer", "human", 3, {"direction": "left"}),
            ],
            "steps_to_run": 10,
            "features_exercised": ["FEAT-02-STREAMER-CONTROL"],
            "invariants_tested": ["INV-COMMAND-VAL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 10,
                "expected_lane": 0,
                "expected_command_statuses": ["applied", "rejected", "rejected"],
            },
        },
        {
            "scenario_id": "SCEN-CTRL-05",
            "category": "control_and_safety",
            "description": "Completed steering shift holds discrete target lane without auto-repeat",
            "seed": 205,
            "initial_lane": 1,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(0, "streamer.steer", "streamer", "human", 1, {"direction": "left"}),
            ],
            "steps_to_run": 15,
            "features_exercised": ["FEAT-02-STREAMER-CONTROL"],
            "invariants_tested": ["INV-COMMAND-VAL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 15,
                "expected_lane": 0,
                "expected_command_statuses": ["applied"],
            },
        },
        {
            "scenario_id": "SCEN-CTRL-06",
            "category": "control_and_safety",
            "description": "Obstacle reachability: steering after warning onset (t=15s) clears center lane before resolution (t=20s)",
            "seed": 206,
            "initial_lane": 1,
            "initial_roster": ["user_0"],
            "scheduled_commands": [
                _cmd_spec(200, "hazard.propose", "user_0", "human", 1, {"hazard_id": "h_reach", "lane": 1}),
                _cmd_spec(310, "streamer.steer", "streamer", "human", 2, {"direction": "left"}),
            ],
            "steps_to_run": 460,
            "features_exercised": ["FEAT-05-HAZARD-AND-SURVIVAL"],
            "invariants_tested": ["INV-REACHABILITY", "INV-HAZARD-BIND", "INV-SAFETY-CAPS"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 460,
                "expected_final_phase": "resolution",
                "expected_lane": 0,
                "expected_pool": 20,
                "expected_collisions_total": 0,
                "expected_command_statuses": ["applied", "applied"],
            },
        },
        {
            "scenario_id": "SCEN-CTRL-07",
            "category": "control_and_safety",
            "description": "Collision slowdown capped at 40 ticks (2.0s) per turn with zero multi-hit stacking on a single obstacle",
            "seed": 207,
            "initial_lane": 1,
            "initial_roster": ["user_0"],
            "scheduled_commands": [
                _cmd_spec(100, "hazard.propose", "user_0", "human", 1, {"hazard_id": "h_cap", "lane": 1}),
            ],
            "steps_to_run": 450,
            "features_exercised": ["FEAT-05-HAZARD-AND-SURVIVAL"],
            "invariants_tested": ["INV-SAFETY-CAPS", "INV-HAZARD-DEPEND"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 450,
                "expected_final_phase": "resolution",
                "expected_pool": 20,
                "expected_collisions_total": 1,
                "expected_collision_halved": True,
                "expected_command_statuses": ["applied"],
            },
        },
        {
            "scenario_id": "SCEN-CTRL-08",
            "category": "control_and_safety",
            "description": "Delivery strictly prior to tick 1800 settles delivered rather than deadline wipe",
            "seed": 208,
            "initial_lane": 0,
            "initial_progress": 99.90,
            "initial_tick": 1758,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(1758, "streamer.steer", "streamer", "human", 1, {"direction": "right"}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": ["FEAT-03-CADENCE-AND-CLOCK"],
            "invariants_tested": ["INV-EFFECT-ORDER", "INV-MAX-TURNS", "INV-SETTLEMENT-ONCE"],
            "expected_oracle": {
                "expected_final_status": "delivered",
                "expected_final_tick_range": [1758, 1762],
                "expected_collisions_total": 0,
                "expected_command_statuses": ["applied"],
            },
        },
        {
            "scenario_id": "SCEN-CTRL-09",
            "category": "control_and_safety",
            "description": "Same-tick pre-deadline collision and delivery adjudicates collision first and halves settlement once",
            "seed": 210,
            "initial_lane": 1,
            "initial_progress": 77.26,
            "initial_roster": ["user_0"],
            "scheduled_commands": [
                _cmd_spec(100, "hazard.propose", "user_0", "human", 1, {"hazard_id": "h_same", "lane": 1}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": [
                "FEAT-05-HAZARD-AND-SURVIVAL",
                "FEAT-06-FICTIONAL-HYPE-REWARD",
            ],
            "invariants_tested": ["INV-EFFECT-ORDER", "INV-SETTLEMENT-ONCE"],
            "expected_oracle": {
                "expected_final_status": "delivered",
                "expected_final_tick": 401,
                "expected_pool": 20,
                "expected_collisions_total": 1,
                "expected_collision_halved": True,
                "expected_command_statuses": ["applied"],
                "expected_settlement": {
                    "status": "delivered",
                    "total_hype": 10,
                    "original_pool": 20,
                    "collision_halved": True,
                    "streamer_share": 5,
                    "audience_share_total": 0,
                    "audience_withheld": 5,
                    "settled_once": True,
                },
            },
        },
        # --- Category 3: phase_and_clock (6 scenarios) ---
        {
            "scenario_id": "SCEN-CLK-01",
            "category": "phase_and_clock",
            "description": "Half-open hazard admission window [0, 15.0s): tick 299 applies, ticks 300 and 301 expire",
            "seed": 301,
            "initial_lane": 1,
            "initial_tick": 298,
            "initial_roster": ["user_0"],
            "scheduled_commands": [
                _cmd_spec(299, "hazard.propose", "user_0", "human", 1, {"hazard_id": "h_cut1", "lane": 1}),
                _cmd_spec(300, "hazard.propose", "user_0", "human", 2, {"hazard_id": "h_cut2", "lane": 1}),
                _cmd_spec(301, "hazard.propose", "user_0", "human", 3, {"hazard_id": "h_cut3", "lane": 1}),
            ],
            "steps_to_run": 5,
            "features_exercised": [
                "FEAT-03-CADENCE-AND-CLOCK",
                "FEAT-05-HAZARD-AND-SURVIVAL",
            ],
            "invariants_tested": ["INV-COMMAND-VAL", "INV-HAZARD-BIND"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 303,
                "expected_pool": 20,
                "expected_warning_active": True,
                "expected_command_statuses": ["applied", "expired", "expired"],
            },
        },
        {
            "scenario_id": "SCEN-CLK-02",
            "category": "phase_and_clock",
            "description": "Half-open counter-vote window [0, 20.0s): tick 399 applies, ticks 400 and 401 expire",
            "seed": 304,
            "initial_lane": 1,
            "initial_roster": ["v_cnt_1", "v_cnt_2"],
            "scheduled_commands": [
                _cmd_spec(50, "hazard.propose", "v_cnt_1", "human", 1, {"hazard_id": "h_cnt", "lane": 1}),
                _cmd_spec(399, "viewer.counter", "v_cnt_1", "human", 2, {"hazard_id": "h_cnt", "counter": "clear_lane"}),
                _cmd_spec(400, "viewer.counter", "v_cnt_2", "human", 3, {"hazard_id": "h_cnt", "counter": "clear_lane"}),
                _cmd_spec(401, "viewer.counter", "v_cnt_2", "human", 4, {"hazard_id": "h_cnt", "counter": "clear_lane"}),
            ],
            "steps_to_run": 402,
            "features_exercised": [
                "FEAT-03-CADENCE-AND-CLOCK",
                "FEAT-04-AUDIENCE-ACCOUNTING",
            ],
            "invariants_tested": ["INV-COMMAND-VAL", "INV-ACCOUNT-INFLUENCE"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 402,
                "expected_final_phase": "resolution",
                "expected_eligible_voters_count": 1,
                "expected_command_statuses": ["applied", "applied", "expired", "expired"],
            },
        },
        {
            "scenario_id": "SCEN-CLK-03",
            "category": "phase_and_clock",
            "description": "Late model completion arriving at tick 310 expires without warning, obstacle, or pool increment",
            "seed": 306,
            "initial_lane": 1,
            "initial_tick": 305,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(310, "hazard.propose", "ai_model", "fixture", 1, {"hazard_id": "h_late", "lane": 1}),
            ],
            "steps_to_run": 100,
            "features_exercised": ["FEAT-07-OPENAI-CHAT-TO-ACTION"],
            "invariants_tested": ["INV-ASYNC-MODEL", "INV-HAZARD-DEPEND", "INV-COMMAND-VAL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 405,
                "expected_final_phase": "resolution",
                "expected_pool": 0,
                "expected_synthetic_fixture_pool": 0,
                "expected_warning_active": False,
                "expected_obstacle_active": False,
                "expected_collisions_total": 0,
                "expected_command_statuses": ["expired"],
            },
        },
        {
            "scenario_id": "SCEN-CLK-04",
            "category": "phase_and_clock",
            "description": "Phase-close boundary coincidence with operator pause freezes tick progression cleanly at tick 400",
            "seed": 307,
            "initial_lane": 1,
            "initial_tick": 399,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(400, "operator.pause", "stage_operator", "human", 1, {"state": True}),
            ],
            "steps_to_run": 5,
            "features_exercised": ["FEAT-03-CADENCE-AND-CLOCK"],
            "invariants_tested": ["INV-PAUSE-CLEAN", "INV-EFFECT-ORDER"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 400,
                "expected_final_phase": "resolution",
                "expected_is_paused": True,
                "expected_command_statuses": ["applied"],
            },
        },
        {
            "scenario_id": "SCEN-CLK-05",
            "category": "phase_and_clock",
            "description": "Pause rejects gameplay commands while active and resumes without catch-up ticks",
            "seed": 308,
            "initial_lane": 1,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(0, "operator.pause", "stage_operator", "human", 1, {"state": True}),
                _cmd_spec(0, "streamer.steer", "streamer", "human", 2, {"direction": "left"}),
                _cmd_spec(0, "operator.pause", "stage_operator", "human", 3, {"state": False}),
                _cmd_spec(2, "streamer.steer", "streamer", "human", 4, {"direction": "left"}),
            ],
            "steps_to_run": 5,
            "features_exercised": ["FEAT-03-CADENCE-AND-CLOCK"],
            "invariants_tested": ["INV-PAUSE-CLEAN", "INV-COMMAND-VAL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 5,
                "expected_is_paused": False,
                "expected_command_statuses": ["applied", "rejected", "applied", "applied"],
            },
        },
        {
            "scenario_id": "SCEN-CLK-06",
            "category": "phase_and_clock",
            "description": "Three-turn bound: match completes in Turn 3 and Turn 4 never begins",
            "seed": 309,
            "initial_lane": 0,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(1210, "streamer.steer", "streamer", "human", 1, {"direction": "right"}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": ["FEAT-03-CADENCE-AND-CLOCK"],
            "invariants_tested": ["INV-MAX-TURNS"],
            "expected_oracle": {
                "expected_final_status": "delivered",
                "expected_final_tick": 1760,
                "expected_final_turn": 3,
                "expected_lane": 1,
                "expected_command_statuses": ["applied"],
                "expected_boundary_labels": ["init", "turn_2_start", "turn_3_start", "terminal_delivery"],
            },
        },
        # --- Category 4: audience_scale (6 scenarios) ---
        {
            "scenario_id": "SCEN-AUD-01",
            "category": "audience_scale",
            "description": "Small roster N=1 quorum: single eligible counter vote satisfies ceil(0.60*1)=1 and clears lane",
            "seed": 402,
            "initial_lane": 1,
            "initial_roster": ["user_single"],
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "user_single", "human", 1, {"hazard_id": "h1", "lane": 1}),
                _cmd_spec(20, "viewer.counter", "user_single", "human", 2, {"hazard_id": "h1", "counter": "clear_lane"}),
            ],
            "steps_to_run": 401,
            "features_exercised": ["FEAT-04-AUDIENCE-ACCOUNTING"],
            "invariants_tested": ["INV-ACCOUNT-INFLUENCE", "INV-EFFECT-ORDER"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 401,
                "expected_final_phase": "resolution",
                "expected_roster_size": 1,
                "expected_eligible_voters_count": 1,
                "expected_hazard_countered": True,
                "expected_obstacle_active": False,
                "expected_command_statuses": ["applied", "applied"],
            },
        },
        {
            "scenario_id": "SCEN-AUD-02",
            "category": "audience_scale",
            "description": "Quorum boundary N=5: 3 eligible counter votes satisfy ceil(0.60*5)=3 threshold",
            "seed": 404,
            "initial_lane": 1,
            "initial_roster": roster_5,
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "u_0", "human", 1, {"hazard_id": "h5", "lane": 1}),
                _cmd_spec(20, "viewer.counter", "u_0", "human", 2, {"hazard_id": "h5", "counter": "clear_lane"}),
                _cmd_spec(21, "viewer.counter", "u_1", "human", 3, {"hazard_id": "h5", "counter": "clear_lane"}),
                _cmd_spec(22, "viewer.counter", "u_2", "human", 4, {"hazard_id": "h5", "counter": "clear_lane"}),
            ],
            "steps_to_run": 401,
            "features_exercised": ["FEAT-04-AUDIENCE-ACCOUNTING"],
            "invariants_tested": ["INV-ACCOUNT-INFLUENCE"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 401,
                "expected_final_phase": "resolution",
                "expected_roster_size": 5,
                "expected_eligible_voters_count": 3,
                "expected_hazard_countered": True,
                "expected_obstacle_active": False,
                "expected_command_statuses": ["applied", "applied", "applied", "applied"],
            },
        },
        {
            "scenario_id": "SCEN-AUD-03",
            "category": "audience_scale",
            "description": "100,000-message fixture corpus evaluation: fixture hazard and counter commands never mint live Hype or human quorum",
            "seed": 42,
            "initial_lane": 1,
            "initial_roster": ["human_voter_0", "human_voter_1"],
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "fixture-viewer-0", "fixture", 1, {"hazard_id": "h_corpus_fixture", "lane": 1}),
                _cmd_spec(20, "viewer.counter", "fixture-viewer-1", "fixture", 2, {"hazard_id": "h_corpus_fixture", "counter": "clear_lane"}),
                _cmd_spec(21, "viewer.counter", "fixture-viewer-2", "fixture", 3, {"hazard_id": "h_corpus_fixture", "counter": "clear_lane"}),
            ],
            "steps_to_run": 401,
            "features_exercised": ["FEAT-04-AUDIENCE-ACCOUNTING"],
            "invariants_tested": ["INV-BOT-ISOLATION", "INV-FIXTURE-LABEL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 401,
                "expected_final_phase": "resolution",
                "expected_pool": 0,
                "expected_synthetic_fixture_pool": 20,
                "expected_eligible_voters_count": 0,
                "expected_hazard_countered": False,
                "expected_command_statuses": ["applied", "rejected", "rejected"],
            },
        },
        {
            "scenario_id": "SCEN-AUD-04",
            "category": "audience_scale",
            "description": "Cross-channel atomic deduplication: first valid counter vote applies and second from same account is duplicate",
            "seed": 405,
            "initial_lane": 1,
            "initial_roster": ["v_cross"],
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "v_cross", "human", 1, {"hazard_id": "h_dup", "lane": 1}),
                _cmd_spec(20, "viewer.counter", "v_cross", "human", 2, {"hazard_id": "h_dup", "counter": "clear_lane"}),
                _cmd_spec(21, "viewer.counter", "v_cross", "human", 3, {"hazard_id": "h_dup", "counter": "clear_lane"}),
            ],
            "steps_to_run": 30,
            "features_exercised": ["FEAT-04-AUDIENCE-ACCOUNTING"],
            "invariants_tested": ["INV-ACCOUNT-INFLUENCE", "INV-COMMAND-VAL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 30,
                "expected_eligible_voters_count": 1,
                "expected_command_statuses": ["applied", "applied", "duplicate"],
            },
        },
        {
            "scenario_id": "SCEN-AUD-05",
            "category": "audience_scale",
            "description": "Mid-turn account registration deferred to Turn 2 frozen roster boundary",
            "seed": 406,
            "initial_lane": 1,
            "initial_roster": ["u_init"],
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "u_init", "human", 1, {"hazard_id": "h_t1", "lane": 1}),
                _cmd_spec(15, "audience.register", "u_late", "human", 2, {"account_id": "u_late"}),
                _cmd_spec(20, "viewer.counter", "u_late", "human", 3, {"hazard_id": "h_t1", "counter": "clear_lane"}),
                _cmd_spec(601, "hazard.propose", "u_init", "human", 4, {"hazard_id": "h_t2", "lane": 1}),
                _cmd_spec(601, "viewer.counter", "u_late", "human", 5, {"hazard_id": "h_t2", "counter": "clear_lane"}),
            ],
            "steps_to_run": 601,
            "features_exercised": ["FEAT-04-AUDIENCE-ACCOUNTING"],
            "invariants_tested": ["INV-ACCOUNT-INFLUENCE"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 601,
                "expected_final_turn": 2,
                "expected_roster_size": 2,
                "expected_eligible_voters_count": 1,
                "expected_command_statuses": ["applied", "applied", "rejected", "applied", "applied"],
            },
        },
        {
            "scenario_id": "SCEN-AUD-06",
            "category": "audience_scale",
            "description": "Unlinked human accounts and bot provenance rejected from hazard commitment and quorum voting",
            "seed": 407,
            "initial_lane": 1,
            "initial_roster": ["human_user"],
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "bot_actor", "bot", 1, {"hazard_id": "h_bot", "lane": 1}),
                _cmd_spec(12, "hazard.propose", "human_user", "human", 2, {"hazard_id": "h_real", "lane": 1}),
                _cmd_spec(20, "viewer.counter", "unlinked_rando", "human", 3, {"hazard_id": "h_real", "counter": "clear_lane"}),
                _cmd_spec(21, "viewer.counter", "bot_actor", "bot", 4, {"hazard_id": "h_real", "counter": "clear_lane"}),
            ],
            "steps_to_run": 30,
            "features_exercised": [
                "FEAT-04-AUDIENCE-ACCOUNTING",
                "FEAT-16-SECURITY-AND-PROVENANCE",
            ],
            "invariants_tested": ["INV-BOT-ISOLATION", "INV-COMMAND-VAL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 30,
                "expected_pool": 20,
                "expected_synthetic_fixture_pool": 0,
                "expected_eligible_voters_count": 0,
                "expected_command_statuses": ["rejected", "applied", "rejected", "rejected"],
            },
        },
        # --- Category 5: incentive_attacks (6 scenarios) ---
        {
            "scenario_id": "SCEN-REW-01",
            "category": "incentive_attacks",
            "description": "Safe-danger farming bounded at 20 Hype/turn and 60 Hype/match cap",
            "seed": 501,
            "initial_lane": 0,
            "initial_roster": ["v_farm"],
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "v_farm", "human", 10, {"hazard_id": "haz_farm_1", "lane": 1}),
                _cmd_spec(20, "viewer.counter", "v_farm", "human", 11, {"hazard_id": "haz_farm_1", "counter": "clear_lane"}),
                _cmd_spec(610, "hazard.propose", "v_farm", "human", 20, {"hazard_id": "haz_farm_2", "lane": 1}),
                _cmd_spec(620, "viewer.counter", "v_farm", "human", 21, {"hazard_id": "haz_farm_2", "counter": "clear_lane"}),
                _cmd_spec(1210, "hazard.propose", "v_farm", "human", 30, {"hazard_id": "haz_farm_3", "lane": 1}),
                _cmd_spec(1220, "viewer.counter", "v_farm", "human", 31, {"hazard_id": "haz_farm_3", "counter": "clear_lane"}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": ["FEAT-06-FICTIONAL-HYPE-REWARD"],
            "invariants_tested": ["INV-HAZARD-BIND", "INV-SETTLEMENT-ONCE"],
            "expected_oracle": {
                "expected_final_status": "delivered",
                "expected_final_tick": 1760,
                "expected_pool": 60,
                "expected_collisions_total": 0,
                "expected_command_statuses": ["applied"] * 6,
                "expected_settlement": {
                    "status": "delivered",
                    "total_hype": 60,
                    "streamer_share": 30,
                    "audience_share_total": 30,
                    "eligible_voters_count": 1,
                    "per_voter_rational": "30",
                },
            },
        },
        {
            "scenario_id": "SCEN-REW-02",
            "category": "incentive_attacks",
            "description": "Duplicate hazard_id returns duplicate and second distinct hazard in same turn returns rejected",
            "seed": 502,
            "initial_lane": 1,
            "initial_roster": ["u1", "u2"],
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "u1", "human", 1, {"hazard_id": "dup_haz", "lane": 1}),
                _cmd_spec(11, "hazard.propose", "u2", "human", 2, {"hazard_id": "dup_haz", "lane": 1}),
                _cmd_spec(12, "hazard.propose", "u2", "human", 3, {"hazard_id": "second_haz_same_turn", "lane": 1}),
            ],
            "steps_to_run": 25,
            "features_exercised": ["FEAT-06-FICTIONAL-HYPE-REWARD"],
            "invariants_tested": ["INV-COMMAND-VAL", "INV-HAZARD-BIND"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 25,
                "expected_pool": 20,
                "expected_command_statuses": ["applied", "duplicate", "rejected"],
            },
        },
        {
            "scenario_id": "SCEN-REW-03",
            "category": "incentive_attacks",
            "description": "Danger-only proposers who cast zero counter votes earn 0 audience share; audience half is withheld",
            "seed": 503,
            "initial_lane": 0,
            "initial_roster": ["danger_proposer"],
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "danger_proposer", "human", 1, {"hazard_id": "h_do", "lane": 1}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": ["FEAT-06-FICTIONAL-HYPE-REWARD"],
            "invariants_tested": ["INV-SETTLEMENT-ONCE", "INV-HAZARD-BIND"],
            "expected_oracle": {
                "expected_final_status": "delivered",
                "expected_final_tick": 1760,
                "expected_pool": 20,
                "expected_eligible_voters_count": 0,
                "expected_command_statuses": ["applied"],
                "expected_settlement": {
                    "status": "delivered",
                    "total_hype": 20,
                    "streamer_share": 10,
                    "audience_share_total": 0,
                    "audience_withheld": 10,
                    "eligible_voters_count": 0,
                    "per_voter_rational": "0",
                },
            },
        },
        {
            "scenario_id": "SCEN-REW-04",
            "category": "incentive_attacks",
            "description": "Multiple collisions across turns halve the final Hype pool only once before 50/50 split",
            "seed": 504,
            "initial_lane": 1,
            "initial_roster": ["v_0", "v_1"],
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "v_0", "human", 1, {"hazard_id": "h_mc_1", "lane": 1}),
                _cmd_spec(610, "hazard.propose", "v_1", "human", 2, {"hazard_id": "h_mc_2", "lane": 1}),
                _cmd_spec(620, "viewer.counter", "v_0", "human", 3, {"hazard_id": "h_mc_2", "counter": "clear_lane"}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": ["FEAT-06-FICTIONAL-HYPE-REWARD"],
            "invariants_tested": ["INV-SETTLEMENT-ONCE", "INV-SAFETY-CAPS"],
            "expected_oracle": {
                "expected_final_status": "delivered",
                "expected_final_tick": 1776,
                "expected_pool": 40,
                "expected_collisions_total": 2,
                "expected_collision_halved": True,
                "expected_command_statuses": ["applied", "applied", "applied"],
                "expected_settlement": {
                    "status": "delivered",
                    "total_hype": 20,
                    "original_pool": 40,
                    "collision_halved": True,
                    "streamer_share": 10,
                    "audience_share_total": 10,
                    "audience_withheld": 0,
                    "eligible_voters_count": 1,
                    "per_voter_rational": "10",
                },
            },
        },
        {
            "scenario_id": "SCEN-REW-05",
            "category": "incentive_attacks",
            "description": "Empty eligible audience at terminal delivery withholds audience share without carry or rounding redistribution",
            "seed": 505,
            "initial_lane": 0,
            "initial_progress": 98.0,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(0, "hazard.propose", "user_0", "human", 1, {"hazard_id": "h_na", "lane": 1}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": ["FEAT-06-FICTIONAL-HYPE-REWARD"],
            "invariants_tested": ["INV-SETTLEMENT-ONCE"],
            "expected_oracle": {
                "expected_final_status": "delivered",
                "expected_final_tick": 36,
                "expected_pool": 20,
                "expected_eligible_voters_count": 0,
                "expected_command_statuses": ["applied"],
                "expected_settlement": {
                    "status": "delivered",
                    "total_hype": 20,
                    "streamer_share": 10,
                    "audience_share_total": 0,
                    "audience_withheld": 10,
                    "eligible_voters_count": 0,
                    "per_voter_rational": "0",
                },
            },
        },
        {
            "scenario_id": "SCEN-REW-06",
            "category": "incentive_attacks",
            "description": "Exact rational division of 30 audience Hype across 7 eligible voters (30/7) and companion 3-voter check (10)",
            "seed": 506,
            "initial_lane": 0,
            "initial_roster": roster_7,
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "v_0", "human", 1, {"hazard_id": "h_rat_1", "lane": 1}),
                *[
                    _cmd_spec(20 + i, "viewer.counter", f"v_{i}", "human", 2 + i, {"hazard_id": "h_rat_1", "counter": "clear_lane"})
                    for i in range(7)
                ],
                _cmd_spec(610, "hazard.propose", "v_1", "human", 10, {"hazard_id": "h_rat_2", "lane": 1}),
                _cmd_spec(1210, "hazard.propose", "v_2", "human", 11, {"hazard_id": "h_rat_3", "lane": 1}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": ["FEAT-06-FICTIONAL-HYPE-REWARD"],
            "invariants_tested": ["INV-SETTLEMENT-ONCE", "INV-ACCOUNT-INFLUENCE"],
            "expected_oracle": {
                "expected_final_status": "delivered",
                "expected_final_tick": 1760,
                "expected_pool": 60,
                "expected_eligible_voters_count": 7,
                "expected_command_statuses": ["applied"] * 10,
                "expected_settlement": {
                    "status": "delivered",
                    "total_hype": 60,
                    "streamer_share": 30,
                    "audience_share_total": 30,
                    "audience_withheld": 0,
                    "eligible_voters_count": 7,
                    "per_voter_rational": "30/7",
                    "settled_once": True,
                },
            },
        },
        # --- Category 6: model_failures (4 scenarios) ---
        {
            "scenario_id": "SCEN-MDL-01",
            "category": "model_failures",
            "description": "Malformed model schema / refusal payload rejected by local validator while fallback command applies",
            "seed": 601,
            "initial_lane": 1,
            "initial_roster": [],
            "scheduled_commands": [
                {
                    "tick": 0,
                    "raw_command": {
                        "schema_version": 999,
                        "kind": "hazard.propose",
                        "payload": "not_a_dict",
                    },
                },
                _cmd_spec(2, "streamer.steer", "streamer", "human", 1, {"direction": "left"}),
            ],
            "steps_to_run": 12,
            "features_exercised": ["FEAT-07-OPENAI-CHAT-TO-ACTION"],
            "invariants_tested": ["INV-COMMAND-VAL", "INV-ASYNC-MODEL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 12,
                "expected_lane": 0,
                "expected_command_statuses": ["rejected", "applied"],
            },
        },
        {
            "scenario_id": "SCEN-MDL-02",
            "category": "model_failures",
            "description": "Oversized actor identifier and injected envelope fields rejected before state mutation",
            "seed": 602,
            "initial_lane": 1,
            "initial_roster": [],
            "scheduled_commands": [
                {
                    "tick": 0,
                    "raw_command": {
                        "schema_version": 1,
                        "command_id": "0" * 64,
                        "kind": "hazard.propose",
                        "actor_id": "actor_" + ("x" * 160),
                        "provenance": "human",
                        "logical_tick": 0,
                        "sequence": 1,
                        "payload": {"hazard_id": "h_big"},
                    },
                },
                {
                    "tick": 1,
                    "raw_command": {
                        "schema_version": 1,
                        "command_id": "0" * 64,
                        "kind": "hazard.propose",
                        "actor_id": "u",
                        "provenance": "human",
                        "logical_tick": 1,
                        "sequence": 2,
                        "injected_physics": True,
                        "payload": {"hazard_id": "h_inj"},
                    },
                },
            ],
            "steps_to_run": 5,
            "features_exercised": [
                "FEAT-07-OPENAI-CHAT-TO-ACTION",
                "FEAT-16-SECURITY-AND-PROVENANCE",
            ],
            "invariants_tested": ["INV-COMMAND-VAL", "INV-ENGINE-AUTH"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 5,
                "expected_pool": 0,
                "expected_command_statuses": ["rejected", "rejected"],
            },
        },
        {
            "scenario_id": "SCEN-MDL-03",
            "category": "model_failures",
            "description": "Provider latency never blocks 20 Hz ticks; late model hazard arrival after tick 300 is discarded as expired",
            "seed": 603,
            "initial_lane": 1,
            "initial_roster": ["v_async"],
            "scheduled_commands": [
                _cmd_spec(10, "streamer.steer", "streamer", "human", 1, {"direction": "left"}),
                _cmd_spec(310, "hazard.propose", "ai_adapter", "fixture", 2, {"hazard_id": "h_delayed", "lane": 1}),
            ],
            "steps_to_run": 320,
            "features_exercised": ["FEAT-07-OPENAI-CHAT-TO-ACTION"],
            "invariants_tested": ["INV-ASYNC-MODEL", "INV-COMMAND-VAL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 320,
                "expected_lane": 0,
                "expected_pool": 0,
                "expected_synthetic_fixture_pool": 0,
                "expected_command_statuses": ["applied", "expired"],
            },
        },
        {
            "scenario_id": "SCEN-MDL-04",
            "category": "model_failures",
            "description": "Deterministic command validation statuses across applied, duplicate, rejected, and expired paths",
            "seed": 604,
            "initial_lane": 1,
            "initial_roster": ["v_det"],
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "v_det", "human", 1, {"hazard_id": "h_det", "lane": 1}),
                _cmd_spec(20, "viewer.counter", "v_det", "human", 2, {"hazard_id": "h_det", "counter": "clear_lane"}),
                _cmd_spec(21, "viewer.counter", "v_det", "human", 3, {"hazard_id": "h_det", "counter": "clear_lane"}),
                _cmd_spec(22, "viewer.counter", "unlinked_user", "human", 4, {"hazard_id": "h_det", "counter": "clear_lane"}),
                _cmd_spec(405, "viewer.counter", "v_det", "human", 5, {"hazard_id": "h_det", "counter": "clear_lane"}),
            ],
            "steps_to_run": 405,
            "features_exercised": ["FEAT-07-OPENAI-CHAT-TO-ACTION"],
            "invariants_tested": ["INV-COMMAND-VAL", "INV-ACCOUNT-INFLUENCE"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 405,
                "expected_final_phase": "resolution",
                "expected_command_statuses": ["applied", "applied", "duplicate", "rejected", "expired"],
            },
        },
        # --- Category 7: offline_and_failover (3 scenarios) ---
        {
            "scenario_id": "SCEN-OFF-01",
            "category": "offline_and_failover",
            "description": "Offline fixture driver mode at phase boundary produces identical state hashes under canonical replay",
            "seed": 701,
            "initial_lane": 1,
            "initial_roster": ["v_0", "v_1"],
            "scheduled_commands": [
                _cmd_spec(0, "operator.failover", "stage_operator", "human", 1, {"reason": "offline_driver_test"}),
                _cmd_spec(10, "hazard.propose", "fixture_driver", "fixture", 2, {"hazard_id": "h_off_1", "lane": 1}),
                _cmd_spec(20, "streamer.steer", "streamer", "human", 3, {"direction": "left"}),
            ],
            "steps_to_run": 50,
            "features_exercised": ["FEAT-11-OFFLINE-FIXTURE-DRIVER"],
            "invariants_tested": ["INV-REPLAY", "INV-FIXTURE-LABEL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 50,
                "expected_lane": 0,
                "expected_execution_mode": "offline_fixture",
                "expected_pool": 0,
                "expected_synthetic_fixture_pool": 20,
                "expected_command_statuses": ["applied", "applied", "applied"],
            },
        },
        {
            "scenario_id": "SCEN-OFF-02",
            "category": "offline_and_failover",
            "description": "D-06 failover boundary: mid-phase and automatic client failover rejected; stage-operator phase-close failover applied",
            "seed": 702,
            "initial_lane": 1,
            "initial_tick": 398,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(399, "operator.failover", "stage_operator", "human", 1, {"reason": "mid_phase_attempt"}),
                _cmd_spec(400, "operator.failover", "client_auto", "human", 2, {"automatic": True}),
                _cmd_spec(400, "operator.failover", "stage_operator", "human", 3, {"reason": "phase_boundary_confirmed"}),
            ],
            "steps_to_run": 5,
            "features_exercised": ["FEAT-11-OFFLINE-FIXTURE-DRIVER"],
            "invariants_tested": ["INV-ENGINE-AUTH", "INV-COMMAND-VAL", "INV-FIXTURE-LABEL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 403,
                "expected_final_phase": "resolution",
                "expected_execution_mode": "offline_fixture",
                "expected_command_statuses": ["rejected", "rejected", "applied"],
            },
        },
        {
            "scenario_id": "SCEN-OFF-03",
            "category": "offline_and_failover",
            "description": "D-06 recovery acceptance: operator.recover at tick 400 with mismatched expected_state_hash is rejected",
            "seed": 703,
            "initial_lane": 1,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(400, "operator.failover", "stage_operator", "human", 1, {"reason": "network_drop"}),
                _cmd_spec(
                    400,
                    "operator.recover",
                    "stage_operator",
                    "human",
                    2,
                    {
                        "health_ok": True,
                        "expected_state_hash": "0" * 64,
                        "expected_tick": 400,
                        "expected_turn": 1,
                        "expected_phase": "resolution",
                    },
                ),
                _cmd_spec(
                    400,
                    "operator.recover",
                    "stage_operator",
                    "human",
                    3,
                    {
                        "health_ok": False,
                        "expected_state_hash": "0" * 64,
                    },
                ),
            ],
            "steps_to_run": 400,
            "features_exercised": ["FEAT-11-OFFLINE-FIXTURE-DRIVER"],
            "invariants_tested": ["INV-REPLAY", "INV-ENGINE-AUTH", "INV-COMMAND-VAL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 400,
                "expected_final_phase": "resolution",
                "expected_execution_mode": "offline_fixture",
                "expected_command_statuses": ["applied", "rejected", "rejected"],
            },
        },
        # --- Category 8: hotfix_and_booth (4 scenarios) ---
        {
            "scenario_id": "SCEN-HOT-01",
            "category": "hotfix_and_booth",
            "description": "D-07 Codex Live Hotfix Booth valid signed data patch stages in Turn 1 and activates at Turn 2 boundary",
            "seed": 704,
            "initial_lane": 1,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(
                    100,
                    "booth.hotfix",
                    "codex_booth",
                    "fixture",
                    1,
                    {
                        "patch_version": 1,
                        "expiry_tick": 1800,
                        "patch_data": {"slowdown_fraction": 0.15, "slowdown_duration_ticks": 30},
                        "signature": "CODEX_BOOTH_TRUSTED_V1",
                    },
                ),
            ],
            "steps_to_run": 601,
            "features_exercised": ["FEAT-08-CODEX-LIVE-HOTFIX"],
            "invariants_tested": ["INV-HOTFIX-SAFETY", "INV-ENGINE-AUTH"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 601,
                "expected_final_turn": 2,
                "expected_applied_hotfix_version": 1,
                "expected_hotfix_rules": {"slowdown_fraction": 0.15, "slowdown_duration_ticks": 30},
                "expected_command_statuses": ["applied"],
            },
        },
        {
            "scenario_id": "SCEN-HOT-02",
            "category": "hotfix_and_booth",
            "description": "D-07 hotfix safety: disallowed keys, out-of-range slowdown, untrusted signer, and mid-turn rollback rejected",
            "seed": 705,
            "initial_lane": 1,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(5, "booth.hotfix", "attacker", "fixture", 1, {"patch_version": 1, "patch_data": {"hp_system": True}, "signature": "TRUSTED_CODEX_KEY"}),
                _cmd_spec(6, "booth.hotfix", "attacker", "fixture", 2, {"patch_version": 1, "patch_data": {"slowdown_fraction": 0.50}, "signature": "TRUSTED_CODEX_KEY"}),
                _cmd_spec(7, "booth.hotfix", "attacker", "fixture", 3, {"patch_version": 1, "patch_data": {"slowdown_fraction": 0.10}, "signature": "UNTRUSTED_KEY"}),
                _cmd_spec(8, "operator.rollback_hotfix", "stage_operator", "human", 4, {}),
            ],
            "steps_to_run": 20,
            "features_exercised": ["FEAT-08-CODEX-LIVE-HOTFIX"],
            "invariants_tested": ["INV-HOTFIX-SAFETY", "INV-SAFETY-CAPS", "INV-COMMAND-VAL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 20,
                "expected_applied_hotfix_version": 0,
                "expected_hotfix_rules": {"slowdown_fraction": 0.20, "slowdown_duration_ticks": 40},
                "expected_command_statuses": ["rejected", "rejected", "rejected", "rejected"],
            },
        },
        {
            "scenario_id": "SCEN-HOT-03",
            "category": "hotfix_and_booth",
            "description": "Twitch Booth waypoint at progress 35.0% activates forcefield metaphor without minting live Hype from fixtures",
            "seed": 706,
            "initial_lane": 1,
            "initial_progress": 34.90,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(0, "hazard.propose", "fixture_actor", "fixture", 1, {"hazard_id": "h_twitch_booth", "lane": 1}),
            ],
            "steps_to_run": 10,
            "features_exercised": ["FEAT-09-TWITCH-BOOTH", "FEAT-01-SAN-DIEGO-ROUTE"],
            "invariants_tested": ["INV-CREDIBILITY", "INV-BOT-ISOLATION"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 10,
                "expected_pool": 0,
                "expected_synthetic_fixture_pool": 20,
                "expected_booths_visited": ["twitch_booth"],
                "expected_command_statuses": ["applied"],
            },
        },
        {
            "scenario_id": "SCEN-HOT-04",
            "category": "hotfix_and_booth",
            "description": "AWS/IVS Booth waypoint at progress 80.0% applies bounded +10% scale boost and rejects >40-tick duration",
            "seed": 707,
            "initial_lane": 1,
            "initial_progress": 79.90,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(2, "booth.boost", "aws_booth", "fixture", 1, {"duration_ticks": 20}),
                _cmd_spec(3, "booth.boost", "aws_booth", "fixture", 2, {"duration_ticks": 999}),
            ],
            "steps_to_run": 15,
            "features_exercised": ["FEAT-10-AWS-IVS-BOOTH", "FEAT-01-SAN-DIEGO-ROUTE"],
            "invariants_tested": ["INV-CREDIBILITY", "INV-SAFETY-CAPS"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 15,
                "expected_booths_subset": ["aws_booth"],
                "expected_command_statuses": ["applied", "rejected"],
            },
        },
        # --- Category 9: presentation_and_audio (3 scenarios) ---
        {
            "scenario_id": "SCEN-PRS-01",
            "category": "presentation_and_audio",
            "description": "Bullet-Time presentation state activates without stopping authoritative 20 Hz ticks; invalid factor rejected",
            "seed": 801,
            "initial_lane": 1,
            "initial_roster": [],
            "scheduled_commands": [
                _cmd_spec(0, "presentation.bullet_time", "presentation_director", "fixture", 1, {"active": True, "freeze_tick": 0, "factor": 0.25}),
                _cmd_spec(1, "presentation.bullet_time", "presentation_director", "fixture", 2, {"active": True, "factor": 2.5}),
            ],
            "steps_to_run": 10,
            "features_exercised": ["FEAT-12-BULLET-TIME-PRESENTATION"],
            "invariants_tested": ["INV-ENGINE-AUTH", "INV-COMMAND-VAL"],
            "expected_oracle": {
                "expected_final_status": "racing",
                "expected_final_tick": 10,
                "expected_audio_state": "bullet_time",
                "expected_command_statuses": ["applied", "rejected"],
            },
        },
        {
            "scenario_id": "SCEN-PRS-02",
            "category": "presentation_and_audio",
            "description": "Adaptive audio state machine transitions across warning (crisis), quorum clear (solution), and delivery (victory)",
            "seed": 802,
            "initial_lane": 0,
            "initial_progress": 77.0,
            "initial_roster": ["v_aud"],
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "v_aud", "human", 1, {"hazard_id": "h_aud", "lane": 1}),
                _cmd_spec(310, "viewer.counter", "v_aud", "human", 2, {"hazard_id": "h_aud", "counter": "clear_lane"}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": ["FEAT-13-ADAPTIVE-AUDIO"],
            "invariants_tested": ["INV-CREDIBILITY", "INV-EFFECT-ORDER"],
            "expected_oracle": {
                "expected_final_status": "delivered",
                "expected_final_tick_range": [401, 415],
                "expected_audio_state": "victory",
                "expected_hazard_countered": True,
                "expected_pool": 20,
                "expected_command_statuses": ["applied", "applied"],
            },
        },
        {
            "scenario_id": "SCEN-PRS-03",
            "category": "presentation_and_audio",
            "description": "Truthful claims and provenance audit: fixture hazard and booth triggers never mint live participant Hype",
            "seed": 803,
            "initial_lane": 0,
            "initial_roster": ["human_viewer"],
            "scheduled_commands": [
                _cmd_spec(10, "hazard.propose", "fixture_driver", "fixture", 1, {"hazard_id": "h_prs_fixture", "lane": 1}),
                _cmd_spec(610, "hazard.propose", "human_viewer", "human", 2, {"hazard_id": "h_prs_human", "lane": 1}),
                _cmd_spec(620, "viewer.counter", "human_viewer", "human", 3, {"hazard_id": "h_prs_human", "counter": "clear_lane"}),
            ],
            "steps_to_run": "until_terminal_or_deadline",
            "features_exercised": [
                "FEAT-15-PUBLIC-DEMO-TIMELINE",
                "FEAT-16-SECURITY-AND-PROVENANCE",
            ],
            "invariants_tested": ["INV-CREDIBILITY", "INV-BOT-ISOLATION", "INV-FIXTURE-LABEL"],
            "expected_oracle": {
                "expected_final_status": "delivered",
                "expected_final_tick": 1760,
                "expected_pool": 20,
                "expected_synthetic_fixture_pool": 20,
                "expected_booths_visited": ["aws_booth", "codex_booth", "twitch_booth"],
                "expected_command_statuses": ["applied", "applied", "applied"],
                "expected_settlement": {
                    "status": "delivered",
                    "total_hype": 20,
                    "original_pool": 20,
                    "synthetic_fixture_hype_illustrated": 20,
                    "live_participant_minted_from_fixture": False,
                    "live_participant_minted": False,
                    "streamer_share": 10,
                    "audience_share_total": 10,
                    "audience_withheld": 0,
                    "eligible_voters_count": 1,
                    "per_voter_rational": "10",
                    "settled_once": True,
                },
            },
        },
    ]

    return [validate_scenario_contract(c) for c in contracts]


def _verify_companion_checks() -> Dict[str, Any]:
    """Run companion deterministic assertions for SCEN-REW-06 (3-voter rational '10') and SCEN-MDL-02 (>64KB rejection)."""
    # 1. SCEN-REW-06 companion 3-voter FullGameSimulator delivery
    sim_3v = FullGameSimulator(seed=5060, initial_lane=0, initial_roster=["v_0", "v_1", "v_2"])
    sim_3v.submit_command(make_command("hazard.propose", "v_0", "human", 0, 1, {"hazard_id": "h_3v_1", "lane": 1}))
    for idx in range(3):
        sim_3v.submit_command(
            make_command("viewer.counter", f"v_{idx}", "human", 0, 2 + idx, {"hazard_id": "h_3v_1", "counter": "clear_lane"})
        )
    for _ in range(TURN_TICKS):
        sim_3v.step()
    sim_3v.submit_command(make_command("hazard.propose", "v_1", "human", 600, 10, {"hazard_id": "h_3v_2", "lane": 1}))
    for _ in range(TURN_TICKS):
        sim_3v.step()
    sim_3v.submit_command(make_command("hazard.propose", "v_2", "human", 1200, 11, {"hazard_id": "h_3v_3", "lane": 1}))
    while sim_3v.status == "racing" and sim_3v.tick < MATCH_DEADLINE_TICKS:
        sim_3v.step()
    sim_3v.finalize_trace()
    if sim_3v.status != "delivered" or sim_3v.terminal_settlement is None:
        raise ValueError("SCEN-REW-06 3-voter companion simulation failed to deliver")
    if sim_3v.terminal_settlement.get("per_voter_rational") != "10":
        raise ValueError(
            f"SCEN-REW-06 3-voter companion expected per_voter_rational == '10', got {sim_3v.terminal_settlement.get('per_voter_rational')!r}"
        )

    # 2. SCEN-MDL-02 >64KB payload rejection before command construction
    oversized_rejected = False
    try:
        make_command("hazard.propose", "u", "human", 10, 1, {"hazard_id": "h_big", "junk": "x" * 70000})
    except ValueError:
        oversized_rejected = True
    if not oversized_rejected:
        raise ValueError("SCEN-MDL-02 >64KB command payload was not rejected by make_command")

    return {
        "rew_06_three_voter_per_voter_rational": sim_3v.terminal_settlement["per_voter_rational"],
        "rew_06_three_voter_final_state_hash": canonical_hash(sim_3v.get_canonical_state()),
        "mdl_02_oversized_64kb_rejected": oversized_rejected,
    }


def build_issues_list() -> List[Dict[str, Any]]:
    """Build the 3 closed remediation issues bound to real SHA-256 hashes of GAMEPLAN-v2.md and DECISIONS.md."""
    gameplan_sha = file_sha256(ROOT / "docs/planning/GAMEPLAN-v2.md")
    gameplan_json_sha = file_sha256(ROOT / "docs/planning/gameplan-v2.json")
    decisions_sha = file_sha256(ROOT / "docs/planning/DECISIONS.md")
    simulator_sha = file_sha256(ROOT / "coordination/full_game_simulator.py")
    common_evidence_hashes = {
        "coordination/full_game_simulator.py": simulator_sha,
        "docs/planning/GAMEPLAN-v2.md": gameplan_sha,
        "docs/planning/gameplan-v2.json": gameplan_json_sha,
        "docs/planning/DECISIONS.md": decisions_sha,
    }
    issues = [
        {
            "issue_id": "ISSUE-SIM-01",
            "severity": "S2",
            "affected_features": ["FEAT-02-STREAMER-CONTROL"],
            "affected_scenarios": ["SCEN-CTRL-03", "SCEN-CTRL-04"],
            "affected_invariants": ["INV-COMMAND-VAL"],
            "category": "plan",
            "root_cause": "plan",
            "root_cause_confidence": "high",
            "title": "Unspecified edge-clamping and transition lockout during 0.5s steering shift",
            "expected_behavior": "Input during active 10-tick transition is rejected; edge movement clamped to lanes [0, 2] without wrapping",
            "observed_behavior": "Revision 4 baseline plan did not specify whether steering requests during an in-flight 0.5s transition queue, overwrite, or reject",
            "evidence_paths": [
                "coordination/full_game_simulator.py",
                "docs/planning/GAMEPLAN-v2.md",
                "docs/planning/DECISIONS.md",
            ],
            "evidence_hashes": common_evidence_hashes,
            "deterministic_reproduction_command": "python3 -m unittest tests.test_full_game_simulation -v",
            "alternatives_considered": [
                "Input queueing during active transition",
                "Wrap-around lane movement",
            ],
            "blocks_simulation_validity": False,
            "blocks_report_review": False,
            "blocks_development": False,
            "proposed_remediation": "Synchronized in Revision 5 (DECISION-04 / D-01): inputs during an active 10-tick transition are rejected; edge moves fail closed",
            "remediation_owner": "Principal Simulation Orchestrator",
            "status": "closed",
            "resolution_hash": gameplan_sha,
        },
        {
            "issue_id": "ISSUE-SIM-02",
            "severity": "S2",
            "affected_features": ["FEAT-01-SAN-DIEGO-ROUTE", "FEAT-03-CADENCE-AND-CLOCK"],
            "affected_scenarios": ["SCEN-E2E-01", "SCEN-E2E-03", "SCEN-CTRL-08"],
            "affected_invariants": ["INV-MAX-TURNS", "INV-EFFECT-ORDER", "INV-SAFETY-CAPS"],
            "category": "plan",
            "root_cause": "plan",
            "root_cause_confidence": "high",
            "title": "Missing nominal route speed and progress calibration relative to 90s deadline",
            "expected_behavior": "Streamer at nominal free speed (100/88 units/s) reaches finish at 88.0s nominal and 89.2s with max 3 collisions (< 90.0s deadline)",
            "observed_behavior": "Revision 4 baseline plan left nominal free speed unspecified, risking inadvertent wipe on full-clear runs",
            "evidence_paths": [
                "coordination/full_game_simulator.py",
                "docs/planning/GAMEPLAN-v2.md",
                "docs/planning/DECISIONS.md",
            ],
            "evidence_hashes": common_evidence_hashes,
            "deterministic_reproduction_command": "python3 -m unittest tests.test_full_game_simulation -v",
            "alternatives_considered": [
                "Dynamic route distance shortening",
                "Extending active deadline grace period",
            ],
            "blocks_simulation_validity": False,
            "blocks_report_review": False,
            "blocks_development": False,
            "proposed_remediation": "Synchronized in Revision 5 (DECISION-04 / D-02 & D-05): calibrate base speed to exact rational 100/88 units/s across the 100.0-unit 5-district San Diego route",
            "remediation_owner": "Principal Simulation Orchestrator",
            "status": "closed",
            "resolution_hash": gameplan_sha,
        },
        {
            "issue_id": "ISSUE-SIM-03",
            "severity": "S2",
            "affected_features": [
                "FEAT-01-SAN-DIEGO-ROUTE",
                "FEAT-08-CODEX-LIVE-HOTFIX",
                "FEAT-09-TWITCH-BOOTH",
                "FEAT-10-AWS-IVS-BOOTH",
            ],
            "affected_scenarios": ["SCEN-E2E-04", "SCEN-HOT-01", "SCEN-HOT-03", "SCEN-HOT-04", "SCEN-PRS-03"],
            "affected_invariants": ["INV-CREDIBILITY", "INV-ENGINE-AUTH"],
            "category": "plan",
            "root_cause": "plan",
            "root_cause_confidence": "high",
            "title": "Unspecified diegetic booth progress waypoints and bounded effect triggers along San Diego route",
            "expected_behavior": "Diegetic booths trigger deterministically at progress 35.0% (twitch_booth), 60.0% (codex_booth), 80.0% (aws_booth), and 100.0% (fictional_main_stage)",
            "observed_behavior": "Revision 4 baseline plan named the diegetic booths and districts without binding exact route progress percentages in the machine-readable specification",
            "evidence_paths": [
                "coordination/full_game_simulator.py",
                "docs/planning/GAMEPLAN-v2.md",
                "docs/planning/DECISIONS.md",
            ],
            "evidence_hashes": common_evidence_hashes,
            "deterministic_reproduction_command": "python3 -m unittest tests.test_full_game_simulation -v",
            "alternatives_considered": [
                "Turn-number-based booth triggers independent of route progress",
                "Omitting booth progress waypoints from deterministic simulation",
            ],
            "blocks_simulation_validity": False,
            "blocks_report_review": False,
            "blocks_development": False,
            "proposed_remediation": "Synchronized in Revision 5 (DECISION-04 / D-09): bind diegetic booth waypoints at 35.0%, 60.0%, 80.0%, and 100.0% progress across GAMEPLAN-v2.md, gameplan-v2.json, and S1-SIMULATION-PROFILE.md",
            "remediation_owner": "Principal Simulation Orchestrator",
            "status": "closed",
            "resolution_hash": gameplan_sha,
        },
    ]
    return detached(issues)


def run_simulation_stage(
    output_root: Optional[Path] = None,
    run_id: Optional[str] = None,
    authorize_token: str = AUTHORIZATION_TOKEN,
) -> Path:
    """Execute Stage 1 (`--stage simulate`): freeze matrix/corpus, run 46 scenarios, and emit pre-review artifacts."""
    base_dir = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    profile_sha = file_sha256(ROOT / "docs/planning/S1-SIMULATION-PROFILE.md")
    if run_id is None:
        run_id = derive_run_id(profile_sha)

    run_dir = create_immutable_run_root(base_dir, run_id, authorize_token)

    # 1. Authoritative source bindings & authorization record
    source_bindings = build_source_bindings()
    write_exclusive_json(run_dir / "SOURCE-BINDINGS.json", source_bindings)

    machine_plan = json.loads((ROOT / "docs/planning/gameplan-v2.json").read_text())
    directive_policy = json.loads((ROOT / "config/directive-policy.json").read_text())
    plan_revision = machine_plan["revision"]["number"]
    ledger_revision = directive_policy["revision"]
    write_exclusive_json(run_dir / "STAGE-METADATA.json", {
        "stage": "pre_review", "review_observed": False,
        "candidate_plan_revision": plan_revision,
        "directive_ledger_revision": ledger_revision,
    })

    gameplan_sha = file_sha256(ROOT / "docs/planning/GAMEPLAN-v2.md")
    gameplan_json_sha = file_sha256(ROOT / "docs/planning/gameplan-v2.json")
    decisions_sha = file_sha256(ROOT / "docs/planning/DECISIONS.md")

    write_exclusive_text(
        run_dir / "AUTHORIZATION.md",
        f"""# Simulation Run Authorization

- **Run ID:** `{run_id}`
- **Authorization Token:** `{AUTHORIZATION_TOKEN}`
- **Authorization Provenance:** `config/directive-policy.json` (`remediation_rerun_and_decision_delegation`) & `docs/planning/DECISIONS.md` (`{decisions_sha}`)
- **Scope:** Deterministic local full-game simulation and Revision 5 plan remediation verification only. No deployment, platform provisioning, live credentials, real Twitch moderation, or live participant rewards.
- **Synchronized Plan Revision:** Revision 5 (`GAMEPLAN-v2.md` SHA-256 `{gameplan_sha}`, `gameplan-v2.json` SHA-256 `{gameplan_json_sha}`).
""",
    )

    # 2. Assumptions, Gaps, and Delegated Decisions
    write_exclusive_text(
        run_dir / "ASSUMPTIONS-AND-GAPS.md",
        """# Prerequisites, Assumptions, and Evidence Gaps

Before tick 0, all deterministic clarifications, delegated product decisions, and capability boundaries were classified:

### 1. Deterministic Clarifications & Delegated Remediation Decisions (Synchronized in Revision 5)
- **ISSUE-SIM-01 (`D-01` Steering Interpolation, Lockout & Edge Clamping):** 3 discrete lanes `0, 1, 2` (width `1.0` unit); `0.5s` (`10`-tick at `20 Hz`) linear interpolation; inputs during an active transition return `rejected`; edge moves from lane `0` left or lane `2` right return `rejected`; same-tick opposite inputs cancel.
- **ISSUE-SIM-02 (`D-02` / `D-05` Route Speed Calibration):** `100.0` distance units across the 5 stylized San Diego districts at exact nominal speed `100/88` units/s (`88.0s` nominal completion; `89.2s` with maximum 3 collisions, strictly before the `90.0s` / `1800`-tick deadline).
- **ISSUE-SIM-03 (`DECISION-04` Diegetic Booth Waypoints):**
  - Twitch Booth (`twitch_booth`): progress `35.0%` (Embarcadero Waterfront / Marina)
  - Codex Live Hotfix Booth (`codex_booth`): progress `60.0%` (Gaslamp Quarter)
  - AWS / Amazon IVS Booth (`aws_booth`): progress `80.0%` (San Diego Convention Center)
  - Fictional Main Stage (`fictional_main_stage`): arrival threshold `100.0%`
- **DECISION-01 (`D-06` Failover & Recovery Boundary):** Stage-operator-confirmed failover (`operator.failover`) valid strictly at safe phase boundaries (`turn_tick in {0, 400, 500}`); live recovery (`operator.recover`) requires health check and exact canonical `state_hash` match.
- **DECISION-02 (`D-07` Data-Only Hotfix Trust & Rollback):** Trusted-key signed `booth.hotfix` restricted to `{"slowdown_fraction", "slowdown_duration_ticks"}` within safety caps (`[0.0, 0.20]` and `[0, 40]`), monotonic version, valid expiry, activating strictly at turn boundary (`turn_tick == 0`) with turn-boundary rollback (`operator.rollback_hotfix`).
- **DECISION-03 (`D-08` Readiness Scope Separation & Honest Coverage):** Separates `simulation_and_plan_ready` from `submission_ready` (`false` until external live Twitch and rendered video capture).

### 2. Unobserved Capabilities in Headless Deterministic Simulation (`AUDIT-04`)
- `FEAT-14-READABILITY-AND-HUD`: Browser/mobile viewport rendering and compressed-video readability are `not_observed` in headless deterministic execution.
- `FEAT-12-BULLET-TIME-PRESENTATION`, `FEAT-13-ADAPTIVE-AUDIO`, `FEAT-15-PUBLIC-DEMO-TIMELINE`: State-machine, tick-progression, and claim-provenance contracts are verified (`partially_observed_state_only`), while visual Canvas interpolation, Web Audio acoustic output/voiceover intelligibility, and rendered 3-minute video capture remain `not_observed` until browser/live verification.
""",
    )

    write_exclusive_text(
        run_dir / "HUMAN-DECISIONS.md",
        f"""# Delegated Product Decisions & Remaining External Submission Gates

Recorded in [`docs/planning/DECISIONS.md`](../../../docs/planning/DECISIONS.md) (SHA-256 `{decisions_sha}`) under requester delegation (`remediation_rerun_and_decision_delegation`):

1. **DECISION-01 (`D-06`: Failover Authority & Recovery Acceptance) — `DELEGATED_ACCEPTED` (`PROVISIONAL`)**
   - Stage-operator-confirmed failover (`operator.failover`) restricted to phase boundaries (`turn_tick in {{0, 400, 500}}`); automatic client takeover rejected; `operator.recover` requires `health_ok=True` and exact `expected_state_hash` match.

2. **DECISION-02 (`D-07`: Data-Only Hotfix Trust & Signing) — `DELEGATED_ACCEPTED` (`PROVISIONAL`)**
   - `booth.hotfix` restricted to `slowdown_fraction` (`[0.0, 0.20]`) and `slowdown_duration_ticks` (`[0, 40]`) with trusted signature (`CODEX_BOOTH_TRUSTED_V1`), monotonic `patch_version`, `expiry_tick`, and turn-boundary activation/rollback.

3. **DECISION-03 (`D-08`: Simulation vs Live Submission Readiness Split) — `DELEGATED_ACCEPTED` (`PROVISIONAL`)**
   - Separates `simulation_and_plan_ready` from `submission_ready: false`; labels all booths as non-sponsor diegetic metaphors; derives unrendered visual/audio/live capabilities honestly as `not_observed`.

4. **DECISION-04 (`D-09` / `ISSUE-SIM-01..03`: Steering Lockout, `100/88` Speed, Booth Waypoints) — `DELEGATED_ACCEPTED` (`PROVISIONAL`)**
   - Synchronized across Revision {plan_revision} of `GAMEPLAN-v2.md`, `gameplan-v2.json`, `S1-SIMULATION-PROFILE.md`, and `config/directive-policy.json` Revision {ledger_revision}.

### Remaining External Gate (Non-Blocking for Offline-Slice Development, Blocking for Final Live Submission):
- `live_submission_external_capture` (`gate: "before_live_submission"`): Live external Twitch channel integration, rendered browser/mobile viewport capture, and under-3-minute public demo video recording remain deferred until separate live-submission authorization.
""",
    )

    # 3. Pre-execution Corpus Manifest & Seeds (`AUDIT-08`)
    contracts = build_frozen_scenario_contracts()
    seeds_data = {
        "master_seed": 42,
        "corpus_seed": 42,
        "corpus_count": 100000,
        "scenario_seeds": {c["scenario_id"]: c["seed"] for c in contracts},
    }
    write_exclusive_json(run_dir / "seeds.json", seeds_data)

    corpus = generate_viewer_corpus(seed=42, count=100000)
    corpus_manifest = build_corpus_manifest(corpus)
    write_exclusive_json(run_dir / "CORPUS-MANIFEST.json", corpus_manifest)

    # 4. Freeze and write SCENARIO-MATRIX.json BEFORE tick 0 of any scenario (`AUDIT-02`)
    frozen_matrix_info = freeze_scenario_matrix(contracts, run_dir / "SCENARIO-MATRIX.json")
    frozen_contracts = frozen_matrix_info["contracts"]
    write_exclusive_json(run_dir / "MATRIX-FREEZE.json", {
        "scenario_matrix_sha256": frozen_matrix_info["matrix_sha256"],
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_before_execution": True,
    })
    catalog = [{**inv, "kind": "scenario"} for inv in INVARIANTS] + [
        {**inv, "kind": "pipeline", "evaluation_stage": "readiness_and_seal"}
        for inv in PIPELINE_INVARIANTS
    ]
    write_exclusive_json(run_dir / "INVARIANT-CATALOG.json", catalog)
    write_exclusive_json(run_dir / "READINESS-CONTRACT.json", {
        "schema_version": 2, "candidate_plan_revision": plan_revision,
        "scenario_ids": [c["scenario_id"] for c in frozen_contracts],
        "invariant_ids": [i["id"] for i in catalog],
        "scenario_matrix_sha256": frozen_matrix_info["matrix_sha256"],
        "invariant_catalog_sha256": file_sha256(run_dir / "INVARIANT-CATALOG.json"),
        "source_bindings_sha256": file_sha256(run_dir / "SOURCE-BINDINGS.json"),
        "feature_specs": build_feature_specs(),
        "unresolved_decisions": directive_policy["unresolved_decisions"],
        "required_work_packages_order": [
            "WP-01-core-engine-implementation", "WP-02-hud-and-mobile-presentation",
            "WP-03-twitch-extension-linking", "WP-04-codex-booth-telemetry",
            "WP-05-submission-demo-pipeline",
        ],
    })

    # 5. Execute all 46 frozen scenarios and verify trace integrity (`AUDIT-05`)
    scenario_results: List[Dict[str, Any]] = []
    scenario_hashes: Dict[str, str] = {}
    inv_records: Dict[str, List[bool]] = {inv["id"]: [] for inv in INVARIANTS}
    e2e_01_bundle: Optional[Dict[str, Any]] = None
    off_01_bundle: Optional[Dict[str, Any]] = None

    for contract in frozen_contracts:
        scen_id = contract["scenario_id"]
        bundle = execute_frozen_scenario(contract, artifact_dir=run_dir)
        trace_check = verify_scenario_trace_integrity(
            scen_id,
            run_dir,
            expected_contract_hash=contract["contract_hash"],
        )
        if not bundle["passed"]:
            raise ValueError(
                f"Scenario {scen_id} failed independent oracle: {bundle['oracle_evaluation']['failures']}"
            )

        scenario_hashes[scen_id] = bundle["final_state_hash"]
        invariants_verified = bundle["oracle_evaluation"]["invariants_verified"]
        for inv_id in contract["invariants_tested"]:
            inv_records[inv_id].append(inv_id in invariants_verified and bundle["passed"])

        scenario_results.append(
            {
                "scenario_id": scen_id,
                "category": contract["category"],
                "contract_hash": contract["contract_hash"],
                "verdict": bundle["verdict"],
                "final_tick": bundle["final_tick"],
                "final_turn": bundle["final_turn"],
                "final_phase": bundle["final_phase"],
                "final_status": bundle["final_status"],
                "initial_state_hash": bundle["initial_state_hash"],
                "state_hash": bundle["final_state_hash"],
                "commands_count": trace_check["commands_count"],
                "trace_records_count": trace_check["trace_records_count"],
                "commands_sha256": trace_check["commands_sha256"],
                "trace_sha256": trace_check["trace_sha256"],
                "features": list(contract["features_exercised"]),
                "features_exercised": list(contract["features_exercised"]),
                "invariants_passed": list(invariants_verified),
            }
        )
        if scen_id == "SCEN-E2E-01":
            e2e_01_bundle = bundle
        elif scen_id == "SCEN-OFF-01":
            off_01_bundle = bundle

    companion_checks = _verify_companion_checks()

    # Golden replay verification on SCEN-E2E-01 (2 independent replays) and SCEN-OFF-01
    if e2e_01_bundle is None or off_01_bundle is None:
        raise ValueError("Missing SCEN-E2E-01 or SCEN-OFF-01 execution bundle")

    replay_1 = replay_command_stream(
        seed=e2e_01_bundle["seed"],
        initial_lane=e2e_01_bundle["initial_lane"],
        initial_roster=e2e_01_bundle["initial_roster"],
        command_log=e2e_01_bundle["command_log"],
        steps_to_run=e2e_01_bundle["steps_to_run"],
        expected_final_state_hash=e2e_01_bundle["final_state_hash"],
    )
    replay_2 = replay_command_stream(
        seed=e2e_01_bundle["seed"],
        initial_lane=e2e_01_bundle["initial_lane"],
        initial_roster=e2e_01_bundle["initial_roster"],
        command_log=e2e_01_bundle["command_log"],
        steps_to_run=e2e_01_bundle["steps_to_run"],
        expected_final_state_hash=e2e_01_bundle["final_state_hash"],
    )
    off_replay = replay_command_stream(
        seed=off_01_bundle["seed"],
        initial_lane=off_01_bundle["initial_lane"],
        initial_roster=off_01_bundle["initial_roster"],
        command_log=off_01_bundle["command_log"],
        steps_to_run=off_01_bundle["steps_to_run"],
        expected_final_state_hash=off_01_bundle["final_state_hash"],
    )
    golden_replay_verified = (
        replay_1["final_state_hash"]
        == replay_2["final_state_hash"]
        == e2e_01_bundle["final_state_hash"]
        and replay_1["boundary_hashes"] == replay_2["boundary_hashes"] == e2e_01_bundle["boundary_hashes"]
        and off_replay["final_state_hash"] == off_01_bundle["final_state_hash"]
    )
    inv_records["INV-REPLAY"].append(golden_replay_verified)

    # Write results/SCENARIO-RESULTS.jsonl and state-hashes/scenario_hashes.json
    results_jsonl = "\n".join(json.dumps(r, sort_keys=False) for r in scenario_results) + "\n"
    write_exclusive_text(run_dir / "results/SCENARIO-RESULTS.jsonl", results_jsonl)
    write_exclusive_json(run_dir / "state-hashes/scenario_hashes.json", scenario_hashes)

    # 6. Compute and write INVARIANT-RESULTS.json
    inv_summary: List[Dict[str, Any]] = []
    for inv in INVARIANTS:
        evals = inv_records[inv["id"]]
        passed = len(evals) > 0 and all(evals)
        inv_summary.append(
            {
                "invariant_id": inv["id"],
                "name": inv["name"],
                "evaluations_count": len(evals),
                "passed": passed,
            }
        )
    write_exclusive_json(run_dir / "INVARIANT-RESULTS.json", inv_summary)
    passed_invariants_count = sum(1 for inv in inv_summary if inv["passed"])

    # 7. Mechanically derive FEATURE-INVENTORY.json and COVERAGE.json (`AUDIT-04`)
    feature_specs = build_feature_specs()
    derived_inventory, coverage_summary = derive_feature_statuses(
        feature_specs,
        scenario_results,
        render_observed=False,
        audio_observed=False,
        live_service_observed=False,
        total_invariants=len(INVARIANTS),
        passed_invariants=passed_invariants_count,
    )
    write_exclusive_json(run_dir / "FEATURE-INVENTORY.json", derived_inventory)
    write_exclusive_json(run_dir / "COVERAGE.json", coverage_summary)

    # 8. Write ISSUES.json (`AUDIT-06`), PLAN-CHANGELOG.md, REMEDIATION-RESULTS.json, REGRESSION-RESULTS.json
    issues = build_issues_list()
    write_exclusive_json(run_dir / "ISSUES.json", issues)

    write_exclusive_text(
        run_dir / "PLAN-CHANGELOG.md",
        f"""# Plan Changelog — Synchronized Revision 5

- **Base Revision:** Revision 4 (2026-11-01)
- **Synchronized Revision:** Revision 5 (2026-11-01)
- **Authoritative Plan SHA-256 (`docs/planning/GAMEPLAN-v2.md`):** `{gameplan_sha}`
- **Authoritative Machine Plan SHA-256 (`docs/planning/gameplan-v2.json`):** `{gameplan_json_sha}`
- **Delegated Decision Ledger (`docs/planning/DECISIONS.md`):** `{decisions_sha}`

### Synchronized Remediation Changes:
1. **`ISSUE-SIM-01` (`D-01` Steering Interpolation, Transition Lockout & Edge Clamping):**
   - Transition duration is `0.5s` (`10` ticks at `20 Hz`) across discrete lanes `[0, 2]`.
   - Lateral movement is clamped to `[0, 2]`; edge steering inputs fail closed (`rejected`).
   - Steering inputs received while `transition_remaining_ticks > 0` are rejected (`transition_lockout`).
   - Same-tick opposite steering inputs cancel out.

2. **`ISSUE-SIM-02` (`D-02` / `D-05` Base Travel Speed & Route Calibration):**
   - Route length is `100.0` distance units across the 5 San Diego districts (`[0,25), [25,50), [50,75), [75,95), [95,100]`).
   - Nominal free speed is exact rational `100/88` units/s (`88.0s` nominal arrival; `89.2s` with max 3 collisions, strictly preceding the `90.0s` deadline).

3. **`ISSUE-SIM-03` (`DECISION-04` Diegetic Booth Waypoints):**
   - Twitch Booth (`twitch_booth`): progress `35.0%` (Embarcadero Waterfront / Marina).
   - Codex Live Hotfix Booth (`codex_booth`): progress `60.0%` (Gaslamp Quarter).
   - AWS / Amazon IVS Booth (`aws_booth`): progress `80.0%` (San Diego Convention Center).
   - Fictional Main Stage (`fictional_main_stage`): progress `100.0%`.

4. **`DECISION-01..03` (`D-06` Failover, `D-07` Hotfix Allowlist/Signing, `D-08` Readiness Scope Separation):**
   - Recorded in `docs/planning/DECISIONS.md` and synchronized across `GAMEPLAN-v2.md` Revision {plan_revision}, `gameplan-v2.json` Revision {plan_revision}, `S1-SIMULATION-PROFILE.md`, and `config/directive-policy.json` Revision {ledger_revision}.
""",
    )

    remediation_results = {
        "total_issues_triaged": len(issues),
        "closed_issues": sum(1 for item in issues if item["status"] == "closed"),
        "remaining_open_issues": sum(1 for item in issues if item["status"] != "closed"),
        "plan_remedies_verified": True,
        "candidate_plan_revision": plan_revision,
        "candidate_plan_sha256": gameplan_sha,
        "candidate_gameplan_json_sha256": gameplan_json_sha,
        "decisions_sha256": decisions_sha,
        "companion_checks": companion_checks,
    }
    write_exclusive_json(run_dir / "REMEDIATION-RESULTS.json", remediation_results)

    passed_scenarios_count = sum(1 for s in scenario_results if s["verdict"] == "passed")
    failed_scenarios_count = sum(1 for s in scenario_results if s["verdict"] != "passed")
    regression_results = {
        "regression_verdict": (
            "passed"
            if passed_scenarios_count == len(frozen_contracts)
            and failed_scenarios_count == 0
            and passed_invariants_count == len(INVARIANTS)
            and golden_replay_verified
            else "failed"
        ),
        "scenarios_executed": len(scenario_results),
        "scenarios_passed": passed_scenarios_count,
        "scenarios_failed": failed_scenarios_count,
        "invariants_passed": passed_invariants_count,
        "invariants_failed": len(INVARIANTS) - passed_invariants_count,
        "golden_replay_verified": golden_replay_verified,
        "golden_replay_final_state_hash": replay_1["final_state_hash"],
        "offline_replay_final_state_hash": off_replay["final_state_hash"],
        "scenario_matrix_sha256": frozen_matrix_info["matrix_sha256"],
        "corpus_sha256": corpus_manifest["sha256"],
    }
    write_exclusive_json(run_dir / "REGRESSION-RESULTS.json", regression_results)

    claims_provenance = [
        {
            "claim": "San Diego 5-district route progression and booth waypoints",
            "status": "observed_in_deterministic_state",
            "provenance": "deterministic_simulation",
            "basis": "Verified in SCEN-E2E-01, SCEN-E2E-04, SCEN-HOT-03, SCEN-HOT-04, SCEN-PRS-03",
        },
        {
            "claim": "90s active simulation deadline and 20/5/5s cadence",
            "status": "observed_in_deterministic_state",
            "provenance": "deterministic_simulation",
            "basis": "Enforced by deterministic 20 Hz integer tick clock at tick 1800 across SCEN-E2E-01..05 and SCEN-CLK-01..06",
        },
        {
            "claim": "Twitch Chat / Extension viewer participation",
            "status": "fixture",
            "provenance": "generated_fixture",
            "basis": "Seeded 100,000-message synthetic viewer corpus (CORPUS-MANIFEST.json) and canonical command fixtures; zero live Twitch connection claimed",
        },
        {
            "claim": "Fixture and bot Hype isolation (D-04 / AUDIT-03)",
            "status": "observed_in_deterministic_state",
            "provenance": "deterministic_simulation",
            "basis": "Fixture hazards increment synthetic_fixture_pool only; live participant pool and settlement remain strictly human-origin (verified in SCEN-E2E-05, SCEN-AUD-03, SCEN-AUD-06, SCEN-PRS-03)",
        },
        {
            "claim": "Twitch, Codex, and AWS/IVS Booth moments",
            "status": "fictional_diegetic_metaphor",
            "provenance": "project_design",
            "basis": "Explicitly labeled non-sponsor in-game metaphors; not proof of vendor endorsement or live cloud integration",
        },
        {
            "claim": "Browser/Mobile HUD readability and acoustic output (FEAT-14, FEAT-12/13/15 sub-claims)",
            "status": "not_observed",
            "provenance": "capability_boundary",
            "basis": "Headless deterministic kernel simulation does not execute browser Canvas 2D rendering, Web Audio synthesis, or 3-minute video capture",
        },
    ]
    write_exclusive_json(run_dir / "CLAIMS-AND-PROVENANCE.json", claims_provenance)

    write_exclusive_text(
        run_dir / "SIMULATION-REPORT.md",
        f"""# TwitchCon Odyssey — Complete Game Deterministic Simulation Report

**Run ID:** `{run_id}`  
**Date:** 2026-11-01  
**Stage:** Pre-Review Evidence Bundle (`simulate` complete; no independent review observed at this stage)  
**Synchronized Plan Revision:** Revision 5 (`GAMEPLAN-v2.md` `{gameplan_sha}`)  

## 1. Executive Summary
The deterministic full-game simulation evaluated the Revision 5 TwitchCon Odyssey specification across 46 pre-frozen scenario contracts (`SCENARIO-MATRIX.json` SHA-256 `{frozen_matrix_info["matrix_sha256"]}`) and 18 mandatory invariants. Every scenario executed against `FullGameSimulator` and emitted substantive canonical command logs (`commands/<id>.json`), `state_diff` hash-chained traces (`traces/<id>.jsonl`), and boundary state hashes (`state-hashes/<id>.json`).

All three plan/simulation issues (`ISSUE-SIM-01` steering lockout/clamping, `ISSUE-SIM-02` `100/88` nominal speed calibration, and `ISSUE-SIM-03` diegetic booth progress waypoints `35.0% / 60.0% / 80.0% / 100.0%`) and delegated decisions (`DECISION-01..04`) are synchronized and closed with real SHA-256 bindings.

## 2. Mechanically Derived Feature Coverage & Scenario Summary
- **Active Features Inventoried:** `{coverage_summary["total_active_features"]}`
- **Fully Observed in Deterministic State:** `{coverage_summary["fully_observed_features"]}` (`FEAT-01` through `FEAT-11`, `FEAT-16`)
- **Partially Observed (State Contract Passed, Render/Audio/Video Sub-Claims Unobserved):** `{coverage_summary["partially_observed_state_only_features"]}` (`FEAT-12`, `FEAT-13`, `FEAT-15`)
- **Not Observed in Headless Simulation:** `{coverage_summary["not_observed_features"]}` (`FEAT-14-READABILITY-AND-HUD`)
- **Scenarios Evaluated:** `{passed_scenarios_count}/{len(scenario_results)}` passed
- **Invariants Verified:** `{passed_invariants_count}/{len(INVARIANTS)}` passed
- **100,000-Message Seeded Corpus SHA-256:** `{corpus_manifest["sha256"]}` (`verified_regeneration_match: true`)
- **Golden Replay Hash (`SCEN-E2E-01`):** `{replay_1["final_state_hash"]}` (verified across 2 independent replays)

## 3. Audit Remediation Verification (`AUDIT-01` through `AUDIT-09`)
- **`AUDIT-01` & `AUDIT-09`:** `run_simulation_stage` creates an exclusive new run directory and writes `REVIEW-PACKET.md` without authoring `INDEPENDENT-REVIEW.md` or pre-hashing `DEVELOPMENT-READINESS.json`.
- **`AUDIT-02`:** `SCENARIO-MATRIX.json` is frozen and hashed before tick 0 with concrete expected oracle dictionaries for all 46 scenarios.
- **`AUDIT-03`:** `FullGameSimulator` isolates `synthetic_fixture_pool` from `pool`; bots and fixtures contribute `0` to live participant Hype and human quorum.
- **`AUDIT-04`:** `FEATURE-INVENTORY.json` and `COVERAGE.json` are derived mechanically from scenario results and environment capabilities (`render_observed: false`).
- **`AUDIT-05`:** All 46 scenarios emit substantive command envelopes and `state_diff` delta traces verified by `verify_scenario_trace_integrity`.
- **`AUDIT-06` & `AUDIT-07`:** Revision 5 plan files and `DECISION-01..04` are synchronized with 64-hex SHA-256 digests; `DEVELOPMENT-READINESS.json` is deferred to `--stage finalize` after independent review verification.
- **`AUDIT-08`:** `CORPUS-MANIFEST.json` binds the 64-hex SHA-256 digest of the regenerated 100,000-message fixture corpus.
""",
    )

    # Stable audit closure records cite real raw/aggregate evidence. Review gates
    # remain pending until an external invocation is verified at finalization.
    audit_evidence = {
        rel: file_sha256(run_dir / rel) for rel in (
            "READINESS-CONTRACT.json", "INVARIANT-CATALOG.json", "MATRIX-FREEZE.json",
            "results/SCENARIO-RESULTS.jsonl", "SOURCE-BINDINGS.json", "CORPUS-MANIFEST.json",
            "INVARIANT-RESULTS.json", "COVERAGE.json", "ISSUES.json", "STAGE-METADATA.json",
            "PLAN-CHANGELOG.md", "SIMULATION-REPORT.md",
        )
    }
    audit_records = []
    for finding, validators in AUDIT_VALIDATORS.items():
        pending = finding in ("AUDIT-01", "AUDIT-10")
        historical = finding == "AUDIT-16"
        audit_records.append({
            "id": finding, "severity": AUDIT_SEVERITIES[finding],
            "status": "pending_external_review" if pending else "open" if historical else "closed",
            "blocking": pending or finding in ("AUDIT-11", "AUDIT-12", "AUDIT-13"),
            "validator_ids": validators, "evidence_hashes": audit_evidence,
            "resolution_hash": canonical_hash(audit_evidence),
            "note": "Historical review remains unverifiable; never retroactively certified" if historical else (
                "Closure evaluated from these validators at readiness/seal; not a gameplay scenario"),
        })
    write_exclusive_json(run_dir / "AUDIT-FINDINGS.json", audit_records)

    # 9. Bind the entire pre-review evidence surface before external review.
    prepare_pending_review_packet(run_dir, run_id)

    return run_dir


def run_finalize_stage(
    output_root: Optional[Path] = None,
    run_id: Optional[str] = None,
) -> Path:
    """Execute Stage 2 (`--stage finalize`): verify independent review, compute readiness, and seal manifest."""
    if output_root is None:
        base_dir = DEFAULT_OUTPUT_ROOT
    else:
        base_dir = Path(output_root)

    if run_id is None:
        if (base_dir / "REVIEW-PACKET.md").is_file() or base_dir.name.startswith("full-game-"):
            run_dir = base_dir
            run_id = run_dir.name
        else:
            raise ValueError("run_id is required for finalize stage")
    else:
        run_dir = base_dir / run_id

    if run_id == PRESERVED_REJECTED_RUN_ID or run_dir.name == PRESERVED_REJECTED_RUN_ID:
        raise PermissionError(f"Refusing to modify preserved rejected run directory: {run_dir}")
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Run directory does not exist: {run_dir}")
    if (run_dir / "RUN-MANIFEST.json").exists():
        raise FileExistsError("Finalized runs cannot be reused or resealed")
    verify_source_bindings(run_dir)

    # 1. Verify external independent review artifact and anti-forgery bindings (`AUDIT-01`)
    review_verification = verify_independent_review_artifact(run_dir)
    invocation_data = json.loads((run_dir / "REVIEW-INVOCATION.json").read_text(encoding="utf-8"))
    review_packet_text = (run_dir / "REVIEW-PACKET.md").read_text(encoding="utf-8")

    # MODEL-USAGE.json is externally authored by coordination.review_boundary.

    # 3. Mechanically compute and write DEVELOPMENT-READINESS.json (`AUDIT-07`)
    readiness = compute_development_readiness(
        run_dir,
        review_verdict=review_verification["verdict"],
        independent_review_verified=review_verification["verified"],
    )
    write_exclusive_json(run_dir / "DEVELOPMENT-READINESS.json", readiness)

    # 4. Write README.md
    profile_first8 = file_sha256(ROOT / "docs/planning/S1-SIMULATION-PROFILE.md")[:8]
    write_exclusive_text(
        run_dir / "README.md",
        f"""# Full Game Simulation Evidence Bundle

**Run ID:** `{run_id}`  
**Authoritative Profile First-8:** `{profile_first8}`  
**Review Verdict:** `{review_verification["verdict"]}`  
**Simulation & Plan Ready (`ready`):** `{readiness["ready"]}`  
**Live Submission Ready (`submission_ready`):** `{readiness["submission_ready"]}`  

This bundle contains the immutable two-stage evidence for the deterministic simulation of TwitchCon Odyssey (Revision {readiness["candidate_plan_revision"]}). The actual reviewer was `{invocation_data["reviewer_provider"]}/{invocation_data["reviewer_model"]}` at `{invocation_data["reviewer_effort"]}` effort; configured gate satisfied: `{readiness["gates"]["independent_review_uses_configured_gate"]}`.

### Key Evidence Artifacts:
- [`SIMULATION-REPORT.md`](SIMULATION-REPORT.md)
- [`REVIEW-PACKET.md`](REVIEW-PACKET.md)
- [`INDEPENDENT-REVIEW.md`](INDEPENDENT-REVIEW.md)
- [`REVIEW-INVOCATION.json`](REVIEW-INVOCATION.json)
- [`DEVELOPMENT-READINESS.json`](DEVELOPMENT-READINESS.json)
- [`FEATURE-INVENTORY.json`](FEATURE-INVENTORY.json)
- [`COVERAGE.json`](COVERAGE.json)
- [`SCENARIO-MATRIX.json`](SCENARIO-MATRIX.json)
- [`CORPUS-MANIFEST.json`](CORPUS-MANIFEST.json)
- [`INVARIANT-RESULTS.json`](INVARIANT-RESULTS.json)
- [`ISSUES.json`](ISSUES.json)
- [`PLAN-CHANGELOG.md`](PLAN-CHANGELOG.md)
- [`RUN-MANIFEST.json`](RUN-MANIFEST.json)
""",
    )

    # 5. Seal RUN-MANIFEST.json last (`AUDIT-09`)
    reg_data = json.loads((run_dir / "REGRESSION-RESULTS.json").read_text(encoding="utf-8"))
    source_bindings = json.loads((run_dir / "SOURCE-BINDINGS.json").read_text(encoding="utf-8"))
    auth_hashes = {
        rel_p: entry["sha256"]
        for rel_p, entry in source_bindings.items()
        if isinstance(entry, dict) and entry.get("role") == "authoritative_planning_input"
    }
    parts = run_id.split("-")
    utc_ts = parts[2] if len(parts) >= 4 else datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    seal_run_manifest(
        run_dir,
        metadata={
            "run_id": run_id,
            "utc_timestamp": utc_ts,
            "authorization": AUTHORIZATION_TOKEN,
            "plan_baseline_revision": 4,
            "plan_candidate_revision": readiness["candidate_plan_revision"],
            "authoritative_source_hashes": auth_hashes,
            "total_scenarios": reg_data["scenarios_executed"],
            "total_passed": reg_data["scenarios_passed"],
            "total_failed": reg_data["scenarios_failed"],
            "status": "completed" if readiness["ready"] else "completed_not_ready",
        },
    )
    return run_dir


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Two-stage deterministic full-game simulation orchestrator and evidence sealer."
    )
    parser.add_argument(
        "--stage",
        choices=("simulate", "finalize"),
        required=True,
        help="Execution stage: 'simulate' (pre-review bundle) or 'finalize' (post-review sealing).",
    )
    parser.add_argument(
        "--authorize",
        default="",
        help=f"Authorization token required for --stage simulate ({AUTHORIZATION_TOKEN}).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run_id for simulate; required run_id for finalize.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Base directory for simulation run roots.",
    )
    args = parser.parse_args(argv)
    output_root = Path(args.output_root)

    if args.stage == "simulate":
        run_dir = run_simulation_stage(
            output_root=output_root,
            run_id=args.run_id,
            authorize_token=args.authorize,
        )
        print(f"Stage 'simulate' completed: {run_dir}")
        return 0

    if not args.run_id:
        raise ValueError("--run-id is required when --stage finalize is specified")
    run_dir = run_finalize_stage(output_root=output_root, run_id=args.run_id)
    print(f"Stage 'finalize' completed: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
