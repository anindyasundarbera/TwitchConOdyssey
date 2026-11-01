# TASK-001 — SDC Simulator Core: Fixture Hype Isolation, State-Diff Trace Emission & D-06/D-07/Booth Mechanics

## Task Identity
- **Task ID:** `TASK-001`
- **Title:** SDC Simulator Core: Fixture Hype Isolation, State-Diff Trace Emission & D-06/D-07/Booth Mechanics
- **Contract Version:** `1.0.0`
- **Planning Status:** `READY`
- **Ship Criticality:** `MUST_SHIP`
- **Risk Classification:** `HIGH` (Evidence-integrity & core state-machine invariants)
- **Linked Audit IDs:** `AUDIT-02`, `AUDIT-03`, `AUDIT-05`, `AUDIT-06`
- **Linked Decision IDs:** `DECISION-01` (`D-06`), `DECISION-02` (`D-07`), `DECISION-04` (`D-09` / `ISSUE-SIM-01..03`)

## Objective
Repair `FullGameSimulator` in `coordination/full_game_simulator.py` so that:
1. `fixture` and `bot` provenance hazards never increment the live participant Hype `pool` (`AUDIT-03`), routing `fixture` arithmetic exclusively to `synthetic_fixture_pool`.
2. Every command submission, phase boundary, and tick state transition emits a canonical `state_diff` delta record using `coordination/state_transport.py` (`AUDIT-05`).
3. `ScenarioContract`, `execute_frozen_scenario()`, `replay_command_stream()`, and `evaluate_independent_oracles()` are provided in `coordination/full_game_simulator.py` (`AUDIT-02`, `AUDIT-05`).
4. Delegated decisions `D-06` (`operator.failover` / `operator.recover` at phase boundaries), `D-07` (`booth.hotfix` 2-key allowlist, version/expiry/signature check, turn-boundary rollback), and `D-09` (exact rational speed `Fraction(100, 88)`, steering lockout/clamping, diegetic booth triggers at `35.0/60.0/80.0`) are enforced deterministically (`AUDIT-06`).

## Checkpoint Reference
- **`AUDIT-03` (S1 / mechanics invariant violated):** "`FullGameSimulator.submit_command` increments the Hype pool for `fixture`-provenance hazards. Revision 4 and `INV-BOT-ISOLATION` require fixtures and bots to contribute zero bounty/Hype."
- **`AUDIT-02` (S0 / simulation validity invalid):** "The runtime must consume the frozen matrix rather than construct expectations from results."
- **`AUDIT-05` (S1 / reproducibility incomplete):** "Fail the scenario if the canonical command stream, state-diff trace, boundary hashes, and oracle evaluations were not captured during execution."

## Dependencies
- **Hard Dependencies:** Recorded `DECISION-01..04` in `docs/planning/DECISIONS.md` (already completed at planning baseline).
- **Integration Dependencies:** `coordination/canonical_commands.py`, `coordination/content_cache.py`, `coordination/state_transport.py`.
- **Soft Dependencies:** None.
- **External Prerequisites:** None.

## Preconditions
Run the repository context compiler before editing:
```bash
python3 -m coordination.context_contract --task development --phase plan \
  --owned-path coordination/full_game_simulator.py
```
Verify that the preserved rejected run directory `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/` has tree SHA-256 `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d`.

## Context to Load
- `docs/planning/SIMULATION-EVIDENCE-AUDIT.md:21-99` (`AUDIT-02`, `AUDIT-03`, `AUDIT-05`)
- `docs/planning/DECISIONS.md` (`DECISION-01`, `DECISION-02`, `DECISION-04`)
- `docs/planning/01_ARCHITECTURE.md` (§2 and §3.1–3.2)
- `coordination/full_game_simulator.py:59-562` (especially lines `216-252` for `hazard.propose` and `464-502` for `_handle_delivery`)
- `coordination/state_transport.py:19-108` (`state_diff`, `apply_diff`)

## Input Contracts
- Canonical command envelopes validated by `coordination.canonical_commands.validate_command`.
- `ScenarioContract` dictionary specifying:
  `{scenario_id, category, seed, initial_lane, base_speed_override, initial_roster, scheduled_commands, steps_to_run, features_exercised, invariants_tested, expected_oracle}`.

## Output Contracts
- Updated `coordination/full_game_simulator.py` exporting:
  - `FullGameSimulator` with:
    - `self.pool` (human-only Hype, cap 60) and `self.synthetic_fixture_pool` (synthetic fixture Hype, cap 60, never paid out).
    - `self.trace_deltas: List[Dict[str, Any]]` recording `{tick, trigger, event_kind, delta, state_hash}` via `state_diff(prev_state, new_state)` whenever state changes or a boundary/command occurs.
    - `operator.failover` and `operator.recover` commands enforcing `DECISION-01` (`D-06` safe phase boundaries `turn_tick in {0, 400, 500}` and state-hash recovery verification).
    - `booth.hotfix` and `operator.rollback_hotfix` commands enforcing `DECISION-02` (`D-07` 2-key allowlist `{"slowdown_fraction", "slowdown_duration_ticks"}`, bounds `[0.0, 0.20]` and `[0, 40]`, monotonic `patch_version`, `expiry_tick`, and turn-boundary activation/rollback).
  - `execute_frozen_scenario(contract: Dict[str, Any]) -> Dict[str, Any]` returning `{scenario_id, contract_hash, initial_state_hash, final_state_hash, final_tick, final_status, command_log, trace_deltas, boundary_hashes, oracle_evaluation, passed}`.
  - `evaluate_independent_oracles(contract: Dict[str, Any], execution_bundle: Dict[str, Any]) -> Dict[str, Any]` independently verifying both `contract["expected_oracle"]` and all applicable invariants (`INV-BOT-ISOLATION`, `INV-SETTLEMENT-ONCE`, `INV-EFFECT-ORDER`, `INV-SAFETY-CAPS`, etc.) from `command_log`, `trace_deltas`, and `final_state` without trusting simulator boolean flags.
  - `replay_command_stream(seed, initial_lane, initial_roster, command_log, steps_to_run, base_speed_override=None) -> Dict[str, Any]` for deterministic replay verification by both the game engine and evidence pipeline.

## Write Scope
- **Permitted Modifications (Exact):** `coordination/full_game_simulator.py`
- **Permitted New Files:** None.
- **Protected Paths (Must Not Modify):**
  - `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/**` (Preserved rejected run directory — strictly outside all write scopes)
  - `coordination/canonical_commands.py`, `coordination/content_cache.py`, `coordination/state_transport.py`

## Implementation Requirements
1. **Fix `AUDIT-03` (`FullGameSimulator.submit_command` lines 243–249):**
   - When `kind == "hazard.propose"`:
     - Reject `provenance == "bot"` with `"rejected"`.
     - If `provenance == "human"`, increment `self.pool = min(60, self.pool + 20)`.
     - If `provenance == "fixture"`, increment `self.synthetic_fixture_pool = min(60, self.synthetic_fixture_pool + 20)` and leave `self.pool` untouched (`+0`).
   - Include `"synthetic_fixture_pool": self.synthetic_fixture_pool` in `get_canonical_state()["bounty"]`.
   - In `_handle_delivery()`, compute `total_pool`, `streamer_share`, and `audience_share_total` strictly from `self.pool`. Record `"synthetic_fixture_hype_illustrated": self.synthetic_fixture_pool` and `"live_participant_minted_from_fixture": False`.
2. **State-Diff Trace Capture (`AUDIT-05`):**
   - Import `state_diff` from `coordination.state_transport`.
   - Maintain `self._last_traced_state = self.get_canonical_state()` at `__init__` and append an initial trace entry `{"tick": 0, "trigger": "init", "delta": state_diff(self._last_traced_state, self._last_traced_state), "state_hash": self.boundary_hashes["tick_0_init"]}`.
   - Record a trace delta entry on every `submit_command` invocation, every phase boundary, every event (`collision`, `clear_lane_success`, `clear_lane_failed`, `booth_visited`, `delivery_settlement`, `wipe`), and at final scenario completion so `self.trace_deltas` is never empty and its chain of `base_hash -> result_hash` is verifiable via `apply_diff`.
3. **`D-06` & `D-07` Command Handlers (`AUDIT-06`):**
   - Add `self.execution_mode = "live_fixture"` (`"live_fixture"` or `"offline_fixture"`), `self.applied_hotfix_version = 0`, and `self.previous_hotfix_rules = copy.deepcopy(self.hotfix_rules)`.
   - Support `operator.failover` (valid only when `self.turn_tick in (0, PLANNING_TICKS, PLANNING_TICKS + RESOLUTION_TICKS)`; switches `self.execution_mode = "offline_fixture"`).
   - Support `operator.recover` (valid only at safe phase boundary AND when `payload.get("expected_state_hash") == canonical_hash(self.get_canonical_state())`; switches `self.execution_mode = "live_fixture"`).
   - Harden `booth.hotfix`: require `signature in ("TRUSTED_CODEX_KEY", "CODEX_BOOTH_TRUSTED_V1")`, `patch_version > self.applied_hotfix_version`, `expiry_tick >= self.tick`, and `set(patch_data).issubset({"slowdown_fraction", "slowdown_duration_ticks"})` with `0.0 <= slowdown_fraction <= 0.20` and `0 <= slowdown_duration_ticks <= 40`. Support `operator.rollback_hotfix` at turn boundary.

## Determinism Contract
- **Controlled Nondeterminism:** Zero wall-clock (`time.time()`), zero `random` module state, zero hash-seed iteration order dependency (all sets sorted before serialization).
- **Fixed-Step Discipline:** `20 Hz` (`TICK_DURATION_SEC = Fraction(1, 20)`), `BASE_SPEED = 100.0 / 88.0`.
- **Core Invariant:** Identical `(seed, initial_lane, initial_roster, scheduled_commands)` produce byte-identical `command_log`, `trace_deltas`, `boundary_hashes`, and `final_state_hash`.
- **Dual Consumers:**
  - *Game Consumer:* `server/engine.py` (wired in `TASK-002`).
  - *Evidence Consumer:* `coordination/run_full_game_simulation.py` and `tests/test_full_game_simulation.py`.
- **Anti-Forgery Check:** `evaluate_independent_oracles` recomputes expected human Hype from `command_log` and verifies `apply_diff` chain continuity across `trace_deltas`.

## Execution Guidance
1. Read `coordination/full_game_simulator.py` and `coordination/state_transport.py`.
2. Update `FullGameSimulator` with `synthetic_fixture_pool`, `trace_deltas`, `D-06` failover/recover commands, and `D-07` hardened hotfix/rollback rules.
3. Implement `execute_frozen_scenario`, `replay_command_stream`, and `evaluate_independent_oracles`.
4. Run unit verification to confirm zero regressions.

## Acceptance Criteria
- Fixture/bot provenance cannot create or receive live Hype (`self.pool == 0` when only `fixture` or `bot` hazards are submitted) or affect human quorum.
- `self.trace_deltas` captures `state_diff` records whose sequential application via `apply_diff` from the initial state reproduces the final canonical state hash.
- `evaluate_independent_oracles` fails closed if `expected_oracle` fields mismatch observed state or if `INV-BOT-ISOLATION` is violated.
- The rejected run directory `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/` remains byte-for-byte unchanged.

## Verification
```bash
python3 -c '
from coordination.full_game_simulator import FullGameSimulator
from coordination.canonical_commands import make_command
from coordination.state_transport import apply_diff
from coordination.content_cache import canonical_hash

sim = FullGameSimulator(seed=42, initial_lane=1)
# Negative test: fixture hazard must NOT increment live pool
res = sim.submit_command(make_command("hazard.propose", "fix_actor", "fixture", 10, 1, {"hazard_id": "h_fix"}))
assert res == "applied"
assert sim.pool == 0, f"Expected live pool 0, got {sim.pool}"
assert sim.synthetic_fixture_pool == 20
# Negative test: bot hazard must be rejected
res_bot = sim.submit_command(make_command("hazard.propose", "bot_actor", "bot", 12, 2, {"hazard_id": "h_bot"}))
assert res_bot == "rejected"
assert sim.pool == 0
print("AUDIT-03 negative and positive verification passed.")
'
```

## Integration Contract
- Exports `FullGameSimulator`, `execute_frozen_scenario`, `replay_command_stream`, `evaluate_independent_oracles`, `HZ`, `PLANNING_TICKS`, `RESOLUTION_TICKS`, `REWARD_TICKS`, `TURN_TICKS`, `MATCH_DEADLINE_TICKS`, `HAZARD_ADMISSION_CLOSE_TICKS`, `GENERAL_INPUT_CLOSE_TICKS`, `BASE_SPEED`, `DISTRICTS`.
- Consumed directly by `TASK-002` (`server/engine.py`), `TASK-004` (`coordination/run_full_game_simulation.py`), and `TASK-006` (`tests/test_full_game_simulation.py`).

## Completion Evidence
- Updated `coordination/full_game_simulator.py` with SHA-256 recorded in `docs/planning/REMEDIATION-STATE.md`.
- Passing verification command output.

## Failure Handling
- If `state_diff` exceeds `MAX_DELTA_OPERATIONS` on long runs, emit delta checkpoints only when canonical state changes (`prev_hash != curr_hash`) on command receipts, phase boundaries, and simulation events (`collision`, `clear_lane_*`, `booth_visited`, `delivery_settlement`, `wipe`). Never fabricate or skip boundary hashes.

## Scheduling Metadata
- **Parallelization:** `PARALLEL_WITH_ISOLATION` (Wave 1; owns only `coordination/full_game_simulator.py`)
- **Risk:** `HIGH`
- **Priority:** `P0`
- **Ship Criticality:** `MUST_SHIP`
- **Amortization:** `NET_NEGATIVE`
- **Estimated Sessions:** `1` bounded session (~25 mins)
- **Complete Before Freeze Point:** `true`
- **Blocks Packaging/Submission:** `true`
- **Blocked Flag:** `false`
