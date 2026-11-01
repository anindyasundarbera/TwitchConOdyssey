# TASK-007 — Pre-Rerun Directive Ledger Binding & Context-Contract Verification Gate

## Task Identity
- **Task ID:** `TASK-007`
- **Title:** Pre-Rerun Directive Ledger Binding & Context-Contract Verification Gate
- **Contract Version:** `2.0.0`
- **Baseline Commit SHA (`BASELINE_SHA`):** `2bb0b538bcfed216590ec49039e9972c5e363f0d` (`plan-baseline/remediation-v2.0`, branch `main`)
- **Planning Status:** `PLANNED`
- **Ship Criticality:** `MUST_SHIP`
- **Risk Classification:** `MEDIUM` (Ensures zero stale source bindings before the authorized simulation run and independent Astra review)
- **Linked Audit IDs:** `AUDIT-06`, `AUDIT-09`
- **Linked Decision IDs:** `DECISION-01..04`

## Objective
Bind all updated remediation source and test files (`coordination/full_game_simulator.py`, `coordination/run_full_game_simulation.py`, `coordination/evidence_pipeline.py`, `coordination/scenario_inputs.py`, `server/engine.py`, `tests/test_full_game_simulation.py`, `tests/test_deterministic_kernel.py`, `tests/test_gameplan_rules.py`, `tests/test_context_contract.py`) into `config/directive-policy.json` `required_paths` and verify that `coordination.context_contract` compiles cleanly for both `simulation_preparation` and `plan_review` tasks.

## Checkpoint Reference
- **`AUDIT-06` (S1):** "Record every change as an issue/decision, then synchronize approved changes across all current plan and policy records. Bind the resulting bytes with real hashes before regression or review."

## Dependencies
- **Hard Dependencies:** `TASK-001`, `TASK-002`, `TASK-003`, `TASK-004`, `TASK-005`, `TASK-006`.
- **Integration Dependencies:** `config/directive-policy.json`, `coordination/context_contract.py`.
- **Soft Dependencies:** None.
- **External Prerequisites:** None.

## Preconditions
Run the repository context compiler before editing:
```bash
python3 -m coordination.context_contract --task planner_orchestrator --phase plan \
  --owned-path config/directive-policy.json
```

## Context to Load
- `config/directive-policy.json:139-160` (`required_paths`)
- `coordination/context_contract.py:27-36` (`REQUIRED_SOURCES`)

## Input Contracts
- Finalized bytes of all code, plan, decision, and test files from `TASK-001` through `TASK-006`.

## Output Contracts
- `config/directive-policy.json` with exact SHA-256 bindings in `required_paths` for all required sources plus the remediated simulation/SDC modules and tests.
- Verified `context_contract` packets for `--task simulation_preparation` and `--task plan_review`.

## Write Scope
- **Permitted Modifications (Exact):** `config/directive-policy.json`
- **Permitted New Files:** None.
- **Protected Paths (Must Not Modify):**
  - `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/**` (Preserved rejected run directory)

## Implementation Requirements
- Recompute SHA-256 digests of every path in `config/directive-policy.json["required_paths"]` and add `coordination/evidence_pipeline.py`, `coordination/full_game_simulator.py`, `coordination/run_full_game_simulation.py`, `coordination/scenario_inputs.py`, `tests/test_full_game_simulation.py`, and `tests/test_deterministic_kernel.py` to `required_paths`.
- Verify all unit tests pass without any hash mismatch.

## Determinism Contract
- `compile_packet` produces identical canonical packet bytes and `packet_hash` across repeated runs.

## Execution Guidance
1. Compute SHA-256 hashes for all bound paths and update `config/directive-policy.json`.
2. Run `python3 -m coordination.context_contract --task simulation_preparation --phase plan --validate-only` and `python3 -m coordination.context_contract --task plan_review --phase plan --validate-only`.
3. Re-run the full unit test suite.

## Acceptance Criteria
- `context_contract --validate-only` exits 0 for `simulation_preparation`, `development`, and `plan_review`.
- All unit tests pass 100%.
- Preserved rejected run directory remains byte-for-byte unchanged.

## Verification
```bash
python3 -m coordination.context_contract --task simulation_preparation --phase plan --validate-only && \
python3 -m coordination.context_contract --task plan_review --phase plan --validate-only && \
python3 -m unittest tests.test_full_game_simulation tests.test_gameplan_rules tests.test_context_contract tests.test_city_setting tests.test_deterministic_kernel tests.test_model_router tests.test_plan_rehearsal -v
```

## Integration Contract
- Freezes all repository source and plan hashes immediately before `TASK-008` executes the fresh simulation run so `SOURCE-BINDINGS.json` in the new run bundle matches `config/directive-policy.json` 100%.

## Completion Evidence
- Updated `config/directive-policy.json` SHA-256 and packet hashes recorded in `docs/planning/REMEDIATION-STATE.md`.

## Failure Handling
- If any file hash changes after `TASK-007`, `context_contract` will fail closed; do not modify code files during `TASK-008` or `TASK-009`.

## Scheduling Metadata
- **Parallelization:** `SERIAL_REQUIRED` after `TASK-006`
- **Risk:** `MEDIUM`
- **Priority:** `P0`
- **Ship Criticality:** `MUST_SHIP`
- **Amortization:** `NET_NEUTRAL`
- **Estimated Sessions:** `0.5` bounded session (~10 mins)
- **Complete Before Freeze Point:** `true` (Marks the **Hard Code Freeze Point**)
- **Blocks Packaging/Submission:** `true`
- **Blocked Flag:** `false`
