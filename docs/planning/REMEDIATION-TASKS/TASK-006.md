# TASK-006 — Comprehensive Positive & Anti-Forgery Negative Test Suite (`tests/test_full_game_simulation.py`)

## Task Identity
- **Task ID:** `TASK-006`
- **Title:** Comprehensive Positive & Anti-Forgery Negative Test Suite (`tests/test_full_game_simulation.py`)
- **Contract Version:** `1.0.0`
- **Planning Status:** `PLANNED`
- **Ship Criticality:** `MUST_SHIP`
- **Risk Classification:** `HIGH` (Enforces the §12 Anti-Forgery Requirement and Checkpoint Step 6 across `AUDIT-01..09`)
- **Linked Audit IDs:** `AUDIT-01`, `AUDIT-02`, `AUDIT-03`, `AUDIT-04`, `AUDIT-05`, `AUDIT-06`, `AUDIT-07`, `AUDIT-08`, `AUDIT-09`
- **Linked Decision IDs:** `DECISION-01`, `DECISION-02`, `DECISION-03`, `DECISION-04`

## Objective
Rewrite and expand `tests/test_full_game_simulation.py` to include both positive deterministic verification and explicit **negative anti-forgery tests** proving that the evidence pipeline fails closed on:
1. Preserved rejected run tampering (`full-game-20261101T102226Z-a8e33043` tree hash check).
2. Fixture or bot provenance attempting to create live Hype or affect human quorum (`AUDIT-03`).
3. Missing or unrendered feature coverage attempting to pass as `"covered"` (`FEAT-14-READABILITY-AND-HUD` must be `"not_observed"` when `render_observed=False`) (`AUDIT-04`).
4. Placeholder command streams (`[{"scenario_id": ..., "execution_mode": "deterministic"}]`) or summary-only trace JSONL files (`AUDIT-05`).
5. Circular or un-frozen scenario oracles (`AUDIT-02`).
6. Non-SHA-256 corpus manifest hashes (`"42-reused-corpus-100k"`) or non-SHA-256 candidate plan hashes (`"rev5-candidate-bound"`) (`AUDIT-06`, `AUDIT-08`).
7. Run root collision / file overwrite attempts (`AUDIT-09`).
8. Self-authored / synthetic `INDEPENDENT-REVIEW.md` or `ready: True` when any gate or review is missing, `REVISE`, or synthetic (`AUDIT-01`, `AUDIT-07`).

## Checkpoint Reference
- **Checkpoint Step 6 (`SIMULATION-EVIDENCE-AUDIT.md:178`):** "Add explicit negative tests for artifact provenance, fixture rewards, missing feature coverage, placeholder traces, and forged review outputs."
- **§12 Anti-Forgery Requirement:** "Every task in this plan that touches readiness, review, or evidence sealing must include a negative test proving that the pipeline **cannot** manufacture: a review verdict, a `ready: true` value, a feature `passed` status, a canonical command stream, a state-diff trace, a manifest hash."

## Dependencies
- **Hard Dependencies:** `TASK-001`, `TASK-002`, `TASK-003`, `TASK-004`, `TASK-005`.
- **Integration Dependencies:** `coordination/full_game_simulator.py`, `coordination/evidence_pipeline.py`, `coordination/run_full_game_simulation.py`, `coordination/scenario_inputs.py`.
- **Soft Dependencies:** None.
- **External Prerequisites:** None.

## Preconditions
Run the repository context compiler before editing:
```bash
python3 -m coordination.context_contract --task complex_coding_debugging --phase plan \
  --owned-path tests/test_full_game_simulation.py
```

## Context to Load
- `docs/planning/SIMULATION-EVIDENCE-AUDIT.md:170-199`
- `tests/test_full_game_simulation.py:1-128`
- `coordination/full_game_simulator.py`
- `coordination/evidence_pipeline.py`
- `coordination/run_full_game_simulation.py`

## Input Contracts
- SDC and evidence pipeline functions from `TASK-001..005`.
- Preserved rejected run baseline in `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/` (used both to verify its own byte-for-byte preservation AND as a real-world negative-test specimen proving the new validators reject the old defective bundle!).

## Output Contracts
- `tests/test_full_game_simulation.py` containing:
  1. `test_preserved_rejected_run_ remains_byte_for_byte_unchanged`: verifies all 116 files in `full-game-20261101T102226Z-a8e33043` match tree SHA-256 `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d` and `RUN-MANIFEST.json` SHA-256 `bf34da0ef4764dfd86857aafa3ea9f864cfb98a34f7dadf0af7cad07f1904cf6`.
  2. `test_negative_validators_reject_defective_baseline_artifacts`: runs the new `evidence_pipeline` validators against the read-only rejected bundle `full-game-20261101T102226Z-a8e33043` and proves that:
     - `verify_scenario_trace_integrity("SCEN-CTRL-01", REJECTED_DIR, ...)` raises `ValueError` (catches placeholder trace/command `AUDIT-05`).
     - `require_hash(rejected_corpus_manifest["sha256"])` raises `ValueError` on `"42-reused-corpus-100k"` (`AUDIT-08`).
     - `require_hash(rejected_readiness["candidate_plan_hash"])` raises `ValueError` on `"rev5-candidate-bound"` (`AUDIT-06`).
     - `verify_independent_review_artifact(REJECTED_DIR)` raises `ValueError` because `REVIEW-INVOCATION.json` is absent and `REVIEW-PACKET.md` hashed a pre-existing `DEVELOPMENT-READINESS.json` (`AUDIT-01`, `AUDIT-09`).
  3. `test_negative_fixture_and_bot_provenance_cannot_mint_live_hype_or_quorum`: proves `fixture` and `bot` commands cannot increase `sim.pool` or affect `clear_lane` quorum, and that `evaluate_independent_oracles` rejects a synthetic state with inflated `pool` (`AUDIT-03`).
  4. `test_negative_feature_coverage_cannot_fabricate_passed_for_unobserved_render`: proves `derive_feature_statuses` marks `FEAT-14-READABILITY-AND-HUD` as `not_observed` when `render_observed=False` and rejects any inventory claiming 16/16 `covered` without render/audio/live evidence (`AUDIT-04`).
  5. `test_negative_simulator_cannot_author_independent_review_or_overwrite_run_root`: proves `create_immutable_run_root` rejects existing directories and `PRESERVED_REJECTED_RUN_ID`, and `write_exclusive_text` rejects writing `INDEPENDENT-REVIEW.md` from simulator mode (`AUDIT-01`, `AUDIT-09`).
  6. `test_negative_readiness_is_false_when_any_gate_fails`: tests each gate input to `compute_development_readiness` (open issue, unresolved decision, placeholder plan hash, failed invariant, missing/REVISE review) and proves `ready` is `False` in every case (`AUDIT-07`).
  7. `test_positive_two_stage_simulation_and_finalization_in_isolated_tempdir`: executes `run_simulation_stage`, simulates a valid external review invocation receipt + `INDEPENDENT-REVIEW.md` in a temporary directory, runs `run_finalize_stage`, and verifies all 46 substantive traces, frozen matrix binding, corpus SHA-256, derived coverage, and manifest sealing.

## Write Scope
- **Permitted Modifications (Exact):** `tests/test_full_game_simulation.py`
- **Permitted New Files:** None.
- **Protected Paths (Must Not Modify):**
  - `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/**` (Read-only inspection allowed; zero writes permitted)

## Implementation Requirements
- Keep test execution fast (<15 seconds total) by reusing the 100k corpus or running full two-stage end-to-end verification once in `setUpClass` using `tempfile.TemporaryDirectory()`.
- Ensure tests also verify the latest finalized run bundle in `artifacts/simulations/full-game/` once `TASK-008`/`TASK-009` have produced it (or dynamically check any finalized run directory alongside the isolated tempdir run).

## Determinism Contract
- All tests use fixed seeds and isolated `tempfile.TemporaryDirectory` workspaces.
- Zero network, socket, subprocess, or wall-clock sleep calls.

## Execution Guidance
1. Implement the 7 positive and negative test methods in `tests/test_full_game_simulation.py`.
2. Run the full permitted unit test suite across the repository.

## Acceptance Criteria
- All negative tests (`AUDIT-01..09`) and positive tests pass in `tests/test_full_game_simulation.py`.
- Full permitted suite (`tests.test_full_game_simulation`, `tests.test_gameplan_rules`, `tests.test_context_contract`, `tests.test_city_setting`, `tests.test_deterministic_kernel`, `tests.test_model_router`, `tests.test_plan_rehearsal`) passes with 0 errors.

## Verification
```bash
python3 -m unittest tests.test_full_game_simulation tests.test_gameplan_rules tests.test_context_contract tests.test_city_setting tests.test_deterministic_kernel tests.test_model_router tests.test_plan_rehearsal -v
```

## Integration Contract
- Gates `TASK-007` (`config/directive-policy.json` code hash reconciliation) and `TASK-008` (authorized fresh simulation run).

## Completion Evidence
- Updated `tests/test_full_game_simulation.py` SHA-256 and full test runner output recorded in `docs/planning/REMEDIATION-STATE.md`.

## Failure Handling
- If any negative test fails to reject a forged input, tighten the corresponding validator in `coordination/evidence_pipeline.py` or `coordination/full_game_simulator.py` before marking `TASK-006` complete.

## Scheduling Metadata
- **Parallelization:** `SERIAL_REQUIRED` after `TASK-001..005`
- **Risk:** `HIGH`
- **Priority:** `P0`
- **Ship Criticality:** `MUST_SHIP`
- **Amortization:** `NET_NEUTRAL`
- **Estimated Sessions:** `1` bounded session (~20 mins)
- **Complete Before Freeze Point:** `true`
- **Blocks Packaging/Submission:** `true`
- **Blocked Flag:** `false`
