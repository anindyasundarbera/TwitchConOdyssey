# TASK-004 — Simulation Orchestrator Refactor: Pre-Execution Frozen Matrix, 46 Substantive Traces & Two-Stage Review/Finalize CLI

## Task Identity
- **Task ID:** `TASK-004`
- **Title:** Simulation Orchestrator Refactor: Pre-Execution Frozen Matrix, 46 Substantive Traces & Two-Stage Review/Finalize CLI
- **Contract Version:** `2.0.0`
- **Baseline Commit SHA (`BASELINE_SHA`):** `2bb0b538bcfed216590ec49039e9972c5e363f0d` (`plan-baseline/remediation-v2.0`, branch `main`)
- **Work Mode (`B-2` Reconciled):** Converge-existing-to-contract refactor of `coordination/run_full_game_simulation.py` (exists at 1,934 lines, SHA-256 `d436204cf7482919b6ae8602a278587de461b6ceb5203b07920eca5722e86cb4`) to pre-execution frozen `SCENARIO-MATRIX.json`, 46 substantive command/trace emissions, and two-stage `--stage simulate` / `--stage finalize` CLI without synthetic review generation.
- **Planning Status:** `PLANNED`
- **Ship Criticality:** `MUST_SHIP`
- **Risk Classification:** `CRITICAL` (Refactors `coordination/run_full_game_simulation.py` to close S0 `AUDIT-01`, S0 `AUDIT-02`, and S1 `AUDIT-04..09`)
- **Linked Audit IDs:** `AUDIT-01`, `AUDIT-02`, `AUDIT-03`, `AUDIT-04`, `AUDIT-05`, `AUDIT-07`, `AUDIT-08`, `AUDIT-09`
- **Linked Decision IDs:** `DECISION-01` (`D-06`), `DECISION-02` (`D-07`), `DECISION-03` (`D-08`), `DECISION-04` (`D-09`)

## Objective
Refactor `coordination/run_full_game_simulation.py` to consume `TASK-001` (`FullGameSimulator`, `execute_frozen_scenario`, `evaluate_independent_oracles`) and `TASK-003` (`coordination/evidence_pipeline.py`, `build_corpus_manifest`) so that:
1. All 46 scenarios are defined as declarative `SCENARIO_CONTRACTS` with concrete inputs, seeds, feature bindings, and exact expected oracles, and written/hashed to `SCENARIO-MATRIX.json` **before** tick 0 (`AUDIT-02`).
2. All 46 scenarios emit substantive `commands/<id>.json`, `traces/<id>.jsonl` (with `state_diff` records), and `state-hashes/<id>.json` during execution; the placeholder fallback loop at lines `1588-1596` is completely removed (`AUDIT-05`).
3. `run_full_game_simulation.py` operates in two explicit CLI stages:
   - `--stage simulate --authorize AUTHORIZE_COMPLETE_GAME_SIMULATION=true [--run-id <new_id>]`: creates the exclusive new run root, freezes `SCENARIO-MATRIX.json` and `CORPUS-MANIFEST.json` before tick 0, runs all 46 scenarios + golden replay, writes `ISSUES.json` (including `ISSUE-SIM-01`, `ISSUE-SIM-02`, and `ISSUE-SIM-03` booth placement), derives `FEATURE-INVENTORY.json` and `COVERAGE.json`, and writes the pending `REVIEW-PACKET.md` **without** generating `INDEPENDENT-REVIEW.md`, `DEVELOPMENT-READINESS.json`, or `RUN-MANIFEST.json` (`AUDIT-01`, `AUDIT-09`).
   - `--stage finalize --run-id <new_id>`: invoked only *after* the independent Astra review agent writes `INDEPENDENT-REVIEW.md` and `REVIEW-INVOCATION.json`; verifies the review artifact, records `MODEL-USAGE.json`, computes `DEVELOPMENT-READINESS.json` via `compute_development_readiness()`, writes `README.md`, and seals `RUN-MANIFEST.json` last (`AUDIT-01`, `AUDIT-07`, `AUDIT-09`).

## Checkpoint Reference
- **`AUDIT-01` (S0):** "`coordination/run_full_game_simulation.py` writes `INDEPENDENT-REVIEW.md` directly with reviewer `gpt-6-astra` and verdict `READY`. The same generator hard-codes `MODEL-USAGE.json` status `completed`."
- **`AUDIT-02` (S0):** "The runner executes all scenario functions first and creates `SCENARIO-MATRIX.json` afterward. Every scenario receives the same generic expected oracle: `satisfies category specification without invariant violations`."
- **`AUDIT-05` (S1):** "Forty-one of 46 command files contain only `{scenario_id, execution_mode}`. Forty-one of 46 trace files contain only final scenario summary fields."
- **`AUDIT-09` (S2):** "The review packet hashes `DEVELOPMENT-READINESS.json` before that file is created in the current code order... derive a unique run ID at invocation, create the root with exclusive semantics, fail if it exists, finalize artifacts in dependency order, and seal the manifest last."

## Dependencies
- **Hard Dependencies:** `TASK-001` and `TASK-003`.
- **Integration Dependencies:** `coordination/full_game_simulator.py`, `coordination/evidence_pipeline.py`, `coordination/scenario_inputs.py`.
- **Soft Dependencies:** `TASK-005` (Plan Revision 5 synchronization — needed before the final official simulation run in `TASK-008`, though `TASK-004` code can be tested in a temporary directory first).
- **External Prerequisites:** None.

## Preconditions
Run the repository context compiler before editing:
```bash
python3 -m coordination.context_contract --task development --phase plan \
  --owned-path coordination/run_full_game_simulation.py
```

## Context to Load
- `docs/planning/SIMULATION-EVIDENCE-AUDIT.md:21-157`
- `docs/planning/01_ARCHITECTURE.md` (§3.1–3.5)
- `coordination/run_full_game_simulation.py:1-1934`
- `coordination/full_game_simulator.py` (updated in `TASK-001`)
- `coordination/evidence_pipeline.py` (created in `TASK-003`)

## Input Contracts
- CLI arguments:
  - `--stage {simulate,finalize}`
  - `--authorize AUTHORIZE_COMPLETE_GAME_SIMULATION=true` (required for `simulate`)
  - `--run-id <str>` (optional for `simulate`, required for `finalize`; never `full-game-20261101T102226Z-a8e33043`)
  - `--output-root <path>` (defaults to `ROOT / "artifacts/simulations/full-game"`, overridable in unit tests with `tempfile.TemporaryDirectory`)

## Output Contracts
- Refactored `coordination/run_full_game_simulation.py` containing:
  - `build_frozen_scenario_contracts() -> List[Dict[str, Any]]`: returns all 46 scenario contracts across the 9 categories (`SCEN-E2E-01..05`, `SCEN-CTRL-01..09`, `SCEN-CLK-01..06`, `SCEN-AUD-01..06`, `SCEN-REW-01..06`, `SCEN-MDL-01..04`, `SCEN-OFF-01..03`, `SCEN-HOT-01..04`, `SCEN-PRS-01..03` plus the remaining 13 sub-scenarios so all 46 scenario IDs from the baseline matrix have explicit pre-execution contracts, seeds, inputs, and concrete expected oracle dictionaries).
  - `run_simulation_stage(output_root, run_id, authorize_token) -> Path`: executes Phase A & Phase B (`01_ARCHITECTURE.md` §3.5), verifying that `SCENARIO-MATRIX.json` is written and hashed *before* scenario 1 executes, and verifying via `verify_scenario_trace_integrity` that all 46 scenarios produced substantive `commands/<id>.json` and `traces/<id>.jsonl` files.
  - `run_finalize_stage(output_root, run_id) -> Path`: executes Phase D (`01_ARCHITECTURE.md` §3.5), verifying `INDEPENDENT-REVIEW.md` and `REVIEW-INVOCATION.json`, writing `MODEL-USAGE.json`, computing `DEVELOPMENT-READINESS.json`, writing `README.md`, and sealing `RUN-MANIFEST.json`.

## Write Scope
- **Permitted Modifications (Exact):** `coordination/run_full_game_simulation.py`
- **Permitted New Files:** None (do NOT run against `artifacts/simulations/full-game/` until `TASK-008`; use `tempfile.TemporaryDirectory()` during `TASK-004` verification).
- **Protected Paths (Must Not Modify):**
  - `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/**` (Preserved rejected run directory)

## Implementation Requirements
1. **All 46 Scenarios Must Use `FullGameSimulator` & Emit Real Commands/Traces (`AUDIT-05`):**
   - Notice in the baseline `run_full_game_simulation.py` that only 5 scenarios (`SCEN-E2E-01..05`) called `record_trace`, and several scenarios (`SCEN-REW-06`, `SCEN-OFF-03`, `SCEN-PRS-03`) only hashed static dictionaries without stepping a `FullGameSimulator` or recording commands!
   - Every single one of the 46 scenarios must execute against `FullGameSimulator` (or `execute_frozen_scenario`), submit its canonical commands, record its `state_diff` trace in `traces/<scenario_id>.jsonl`, and record its command log in `commands/<scenario_id>.json`.
   - Specifically:
     - `SCEN-REW-06` (exact rational division): run two `FullGameSimulator` deliveries (one with 3 eligible voters, one with 7 eligible voters) and verify `per_voter_rational == "10"` and `"30/7"` from the actual simulator settlements!
     - `SCEN-OFF-03` (recovery health check mismatch): run a `FullGameSimulator` to tick 400, submit `operator.failover`, then submit `operator.recover` with a mismatched `expected_state_hash` and verify status `"rejected"`!
     - `SCEN-PRS-03` (truthful claims & provenance audit): run a `FullGameSimulator` scenario exercising fixture hazard + booth triggers and verify in the independent oracle that `live_participant_minted_from_fixture == False` and all `CLAIMS-AND-PROVENANCE.json` entries match observed vs fixture status.
     - Ensure the exact 46 scenario count from the baseline is preserved (verify all 46 `scenario_id`s).
2. **Three Issues in `ISSUES.json` (`AUDIT-06`):**
   - Include `ISSUE-SIM-01` (steering transition lockout & edge clamping), `ISSUE-SIM-02` (nominal route speed calibration `100/88`), and `ISSUE-SIM-03` (diegetic booth placement at progress `35.0%`, `60.0%`, `80.0%`, `100.0%`), each with real SHA-256 `resolution_hash` binding `docs/planning/GAMEPLAN-v2.md` and `docs/planning/DECISIONS.md`.
3. **No Self-Authored Review (`AUDIT-01`):**
   - Delete lines `1870-1887` (`(ARTIFACT_DIR / "INDEPENDENT-REVIEW.md").write_text(...)`) completely from `coordination/run_full_game_simulation.py`.

## Determinism Contract
- **Pre-Execution Oracle Freeze:** `SCENARIO-MATRIX.json` is written to disk and hashed before any `FullGameSimulator` runs. Each result in `SCENARIO-RESULTS.jsonl` records `contract_hash` matching the frozen entry in `SCENARIO-MATRIX.json`.
- **Anti-Forgery Check:** Running `--stage finalize` before `INDEPENDENT-REVIEW.md` and `REVIEW-INVOCATION.json` exist raises `FileNotFoundError` / `ValueError`.

## Execution Guidance
1. Inspect all scenario IDs in `coordination/run_full_game_simulation.py` (check how many scenarios were in `SCENARIO-RESULTS.jsonl` of the rejected run to ensure all 46 IDs are accounted for).
2. Refactor `coordination/run_full_game_simulation.py` to use `build_frozen_scenario_contracts()`, `execute_frozen_scenario()`, and `coordination/evidence_pipeline.py`.
3. Test `--stage simulate` in a `tempfile.TemporaryDirectory()` to confirm all 46 command/trace files and `REVIEW-PACKET.md` are created cleanly without touching `artifacts/simulations/full-game/`.

## Acceptance Criteria
- `SCENARIO-MATRIX.json` has 46 entries, each with concrete `seed`, `initial_lane`, `scheduled_commands`, `features_exercised`, and non-generic `expected_oracle` dict, written before tick 0.
- 46/46 scenarios produce substantive `commands/<id>.json` and `traces/<id>.jsonl` with `state_diff` operations.
- `run_full_game_simulation.py` contains zero code capable of writing `INDEPENDENT-REVIEW.md`.
- Rejected run directory `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/` is untouched.

## Verification
```bash
python3 -c '
import tempfile
from pathlib import Path
from coordination.run_full_game_simulation import run_simulation_stage
with tempfile.TemporaryDirectory() as tmp:
    run_dir = run_simulation_stage(Path(tmp), "full-game-20261101T180000Z-test0001", "AUTHORIZE_COMPLETE_GAME_SIMULATION=true")
    assert (run_dir / "SCENARIO-MATRIX.json").exists()
    assert (run_dir / "REVIEW-PACKET.md").exists()
    assert not (run_dir / "INDEPENDENT-REVIEW.md").exists()
    assert not (run_dir / "DEVELOPMENT-READINESS.json").exists()
    assert len(list((run_dir / "commands").glob("*.json"))) == 46
    assert len(list((run_dir / "traces").glob("*.jsonl"))) == 46
print("TASK-004 smoke check passed.")
'
```

## Integration Contract
- Consumes `TASK-001` and `TASK-003`; consumed by `TASK-006` (unit tests) and `TASK-008` (authorized fresh simulation execution).

## Completion Evidence
- Updated `coordination/run_full_game_simulation.py` SHA-256 recorded in `docs/planning/REMEDIATION-STATE.md`.

## Failure Handling
- If any scenario oracle fails during temporary-directory smoke testing, inspect the oracle vs `FullGameSimulator` state transition and fix the defect before proceeding. Never weaken an oracle to a generic string.

## Scheduling Metadata
- **Parallelization:** `SERIAL_REQUIRED` after `TASK-001` and `TASK-003`
- **Risk:** `CRITICAL`
- **Priority:** `P0`
- **Ship Criticality:** `MUST_SHIP`
- **Amortization:** `NET_NEGATIVE`
- **Estimated Sessions:** `1` bounded session (~30 mins)
- **Complete Before Freeze Point:** `true`
- **Blocks Packaging/Submission:** `true`
- **Blocked Flag:** `false`
