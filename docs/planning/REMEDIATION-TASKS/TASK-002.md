# TASK-002 — Dual-Consumer Runtime Wiring: Import SDC Primitives into Shipping Game Engine

## Task Identity
- **Task ID:** `TASK-002`
- **Title:** Dual-Consumer Runtime Wiring: Import SDC Primitives into Shipping Game Engine
- **Contract Version:** `2.0.0`
- **Baseline Commit SHA (`BASELINE_SHA`):** `2bb0b538bcfed216590ec49039e9972c5e363f0d` (`plan-baseline/remediation-v2.0`, branch `main`)
- **Planning Status:** `PLANNED`
- **Ship Criticality:** `MUST_SHIP`
- **Risk Classification:** `MEDIUM` (Must preserve legacy `Engine` interface compatibility while sharing SDC primitives and keeping gameplay gate closed)
- **Linked Audit IDs:** `AUDIT-02`, `AUDIT-03`, `AUDIT-05`
- **Linked Decision IDs:** `DECISION-01` (`D-06`), `DECISION-02` (`D-07`), `DECISION-04` (`D-09`)

## Objective
Satisfy the §4 Dual-Consumer Mandate by wiring `server/engine.py` to import and expose the Shared Determinism Core (`FullGameSimulator`, `replay_command_stream`, `evaluate_independent_oracles`, `DISTRICTS`, `HZ`, `canonical_hash`, `validate_command`, `state_diff`) from `coordination/`, providing a unified S1 authoritative engine adapter (`S1EngineAdapter`) in `server/engine.py` without breaking existing `Engine` class signatures or executing forbidden gameplay commands (`server.app`, `server.replay`, `harness.run`).

## Checkpoint Reference
- **Dual-Consumer Mandate (§4) & `AUDIT-03` / `AUDIT-05`:** "Every deterministic primitive introduced by this plan must satisfy... Runtime residence: The primitive lives in code the shipping game build includes, or in a module both the game and the evidence pipeline import... Verification consumption: The evidence pipeline imports the same primitive rather than reimplementing its logic."

## Dependencies
- **Hard Dependencies:** `TASK-001` (`coordination/full_game_simulator.py` SDC primitives).
- **Integration Dependencies:** `coordination/canonical_commands.py`, `coordination/content_cache.py`, `coordination/state_transport.py`.
- **Soft Dependencies:** None.
- **External Prerequisites:** None.

## Preconditions
Run the repository context compiler before editing:
```bash
python3 -m coordination.context_contract --task development --phase plan \
  --owned-path server/engine.py \
  --owned-path tests/test_deterministic_kernel.py
```
Verify that the gameplay gate remains closed: do **not** run `server.app`, `server.replay`, `tests/test_game.py`, `tests/browser_e2e.py`, or `harness.run`.

## Context to Load
- `AGENTS.md:11-13` (Gameplay gate: run only targeted routing, context-contract, rehearsal, and pure deterministic-kernel tests)
- `docs/planning/01_ARCHITECTURE.md` (§2 Shared Determinism Core)
- `server/engine.py:1-90`
- `coordination/full_game_simulator.py` (from `TASK-001`)
- `tests/test_city_setting.py:1-65` (checks `server.engine.DISTRICTS`)

## Input Contracts
- SDC primitives in `coordination/full_game_simulator.py`, `coordination/canonical_commands.py`, `coordination/content_cache.py`, and `coordination/state_transport.py`.

## Output Contracts
- `server/engine.py`:
  - Imports shared constants and primitives (`FullGameSimulator`, `replay_command_stream`, `evaluate_independent_oracles`, `HZ`, `PLANNING_TICKS`, `RESOLUTION_TICKS`, `REWARD_TICKS`, `TURN_TICKS`, `MATCH_DEADLINE_TICKS`) from `coordination.full_game_simulator` and (`make_command`, `validate_command`, `canonical_hash`, `state_diff`, `apply_diff`) from `coordination`.
  - Derives `DISTRICTS` tuple directly from `tuple(d["name"] for d in SDC_DISTRICTS)` so district names have a single source of truth across `coordination/full_game_simulator.py` and `server/engine.py`.
  - Exposes `create_s1_simulator(seed=42, initial_lane=1) -> FullGameSimulator` and `verify_s1_replay(seed, initial_lane, initial_roster, command_log, steps_to_run)` in `server/engine.py` for runtime/replay consumption while preserving the existing `Engine` class intact.
- `tests/test_deterministic_kernel.py`:
  - Adds pure unit test `DualConsumerSdcBindingTests` verifying that `server.engine` and `coordination.full_game_simulator` share the exact same SDC functions/classes (`server.engine.FullGameSimulator is coordination.full_game_simulator.FullGameSimulator`), `DISTRICTS` order, `AUDIT-03` fixture-Hype isolation, and `state_diff` replay determinism.

## Write Scope
- **Permitted Modifications (Exact):**
  - `server/engine.py`
  - `tests/test_deterministic_kernel.py`
- **Permitted New Files:** None.
- **Protected Paths (Must Not Modify):**
  - `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/**` (Preserved rejected run directory)
  - `server/app.py`, `server/replay.py`, `harness/run.py`

## Implementation Requirements
1. In `server/engine.py`, import `DISTRICTS as SDC_DISTRICTS, FullGameSimulator, HZ, TURN_TICKS, MATCH_DEADLINE_TICKS, replay_command_stream, evaluate_independent_oracles` from `coordination.full_game_simulator`, plus `make_command, validate_command` from `coordination.canonical_commands` and `state_diff, apply_diff` from `coordination.state_transport`.
2. Replace the duplicate `DISTRICTS = (...)` literal in `server/engine.py:8-9` with `DISTRICTS = tuple(d["name"] for d in SDC_DISTRICTS)`.
3. Add `create_s1_simulator` and `verify_s1_replay` thin runtime entry points to `server/engine.py`.
4. Ensure `tests/test_deterministic_kernel.py` `test_kernel_static_imports_are_data_only` continues to pass (recall `test_kernel_static_imports_are_data_only` checks imports inside `coordination/canonical_commands.py`, `content_cache.py`, `scenario_inputs.py`, `state_transport.py`, which must NOT import `server`). Importing `coordination` inside `server/engine.py` is the clean one-way dependency `server -> coordination`.

## Determinism Contract
- **Single Source of Truth:** `DISTRICTS`, `FullGameSimulator`, `replay_command_stream`, `evaluate_independent_oracles`, `make_command`, `validate_command`, and `state_diff` are defined once in `coordination/` and imported into `server/engine.py`.
- **Anti-Forgery / Negative Test:** `DualConsumerSdcBindingTests` in `tests/test_deterministic_kernel.py` asserts that submitting a `fixture` or `bot` hazard via `server.engine.create_s1_simulator()` yields `pool == 0` and that tampering with a replayed command stream raises a hash mismatch.

## Execution Guidance
1. Edit `server/engine.py` to import SDC primitives from `coordination.*` and derive `DISTRICTS`.
2. Add `DualConsumerSdcBindingTests` to `tests/test_deterministic_kernel.py`.
3. Run permitted unit tests (`tests.test_deterministic_kernel` and `tests.test_city_setting`).

## Acceptance Criteria
- `server.engine.DISTRICTS` is derived from `coordination.full_game_simulator.DISTRICTS`.
- `server.engine.FullGameSimulator is coordination.full_game_simulator.FullGameSimulator`.
- `python3 -m unittest tests.test_deterministic_kernel tests.test_city_setting -v` passes 100%, including negative test for fixture-Hype isolation and tampered replay rejection.
- Rejected run directory `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/` is untouched.

## Verification
```bash
python3 -m unittest tests.test_deterministic_kernel tests.test_city_setting -v
```

## Integration Contract
- Connects `TASK-001` SDC primitives to `server/engine.py` without violating `AGENTS.md` gameplay gate.

## Completion Evidence
- Updated `server/engine.py` and `tests/test_deterministic_kernel.py` hashes recorded in `docs/planning/REMEDIATION-STATE.md`.

## Failure Handling
- If `tests/test_city_setting.py` inspects AST or string literals in `server/engine.py`, verify `tests/test_city_setting.py` passes; if it checks `engine.DISTRICTS` runtime tuple, `tuple(d["name"] for d in SDC_DISTRICTS)` matches identically.

## Scheduling Metadata
- **Parallelization:** `SERIAL_REQUIRED` after `TASK-001` (depends on `coordination/full_game_simulator.py` exports)
- **Risk:** `MEDIUM`
- **Priority:** `P1`
- **Ship Criticality:** `MUST_SHIP`
- **Amortization:** `NET_NEGATIVE`
- **Estimated Sessions:** `1` bounded session (~15 mins)
- **Complete Before Freeze Point:** `true`
- **Blocks Packaging/Submission:** `true`
- **Blocked Flag:** `false`
