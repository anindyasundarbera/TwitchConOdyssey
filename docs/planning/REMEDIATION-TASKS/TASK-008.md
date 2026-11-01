# TASK-008 — Authorized Fresh Simulation Run (Stage 1: Pre-Review Bundle Generation & Freeze)

## Task Identity
- **Task ID:** `TASK-008`
- **Title:** Authorized Fresh Simulation Run (Stage 1: Pre-Review Bundle Generation & Freeze)
- **Contract Version:** `1.0.0`
- **Planning Status:** `PLANNED`
- **Ship Criticality:** `MUST_SHIP`
- **Risk Classification:** `HIGH` (Generates the immutable evidence bundle under a new unique run root)
- **Linked Audit IDs:** `AUDIT-02`, `AUDIT-03`, `AUDIT-04`, `AUDIT-05`, `AUDIT-06`, `AUDIT-08`, `AUDIT-09`
- **Linked Decision IDs:** `DECISION-01..04`

## Objective
Execute the authorized fresh deterministic simulation run (`python3 -m coordination.run_full_game_simulation --stage simulate --authorize AUTHORIZE_COMPLETE_GAME_SIMULATION=true`) to create a new, uniquely rooted evidence bundle `artifacts/simulations/full-game/<NEW_RUN_ID>/` containing the pre-execution frozen `SCENARIO-MATRIX.json`, valid SHA-256 `CORPUS-MANIFEST.json`, all 46 substantive command/trace/state-hash files, mechanically derived `FEATURE-INVENTORY.json` and `COVERAGE.json`, synchronized Revision-5 `ISSUES.json` and `PLAN-CHANGELOG.md`, and the frozen `REVIEW-PACKET.md` ready for independent Astra review.

## Checkpoint Reference
- **Checkpoint Steps 8 & 9 (`SIMULATION-EVIDENCE-AUDIT.md:180-181`):** "Produce a new, unique run directory; never overwrite the rejected run. Freeze the new evidence bundle, then invoke one genuine Astra/high independent review through the configured agent boundary."

## Dependencies
- **Hard Dependencies:** `TASK-007` (All code, plan, decision, and ledger hashes frozen and verified).
- **Integration Dependencies:** `coordination/run_full_game_simulation.py`, `coordination/evidence_pipeline.py`, `coordination/full_game_simulator.py`.
- **Soft Dependencies:** None.
- **External Prerequisites:** None (Rerun authorization is already granted and recorded in `config/directive-policy.json` under `remediation_rerun_and_decision_delegation`).

## Preconditions
Run the repository context compiler before execution:
```bash
python3 -m coordination.context_contract --task simulation_preparation --phase plan
```
Verify that `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/` has tree SHA-256 `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d` before and after running the simulation.

## Context to Load
- `docs/planning/00_CONTEXT.md` (§0 Authorization Record)
- `docs/planning/01_ARCHITECTURE.md` (§3.5 Phase A & Phase B)
- `coordination/run_full_game_simulation.py`

## Input Contracts
- Frozen repository sources bound in `config/directive-policy.json`.
- Authorization token `AUTHORIZE_COMPLETE_GAME_SIMULATION=true`.

## Output Contracts
- New immutable directory `artifacts/simulations/full-game/<NEW_RUN_ID>/` where `<NEW_RUN_ID>` matches `full-game-<UTC-YYYYMMDDTHHMMSSZ>-<rev5-profile-sha256-first8>` and does not equal `full-game-20261101T102226Z-a8e33043`.
- Frozen pre-review artifacts inside `<NEW_RUN_ID>/`:
  - `AUTHORIZATION.md`, `SOURCE-BINDINGS.json`, `ASSUMPTIONS-AND-GAPS.md`, `HUMAN-DECISIONS.md`
  - `seeds.json`, `CORPUS-MANIFEST.json` (with 64-hex SHA-256 `sha256`)
  - `SCENARIO-MATRIX.json` (46 concrete pre-execution scenario contracts)
  - `commands/SCEN-*.json` (46 files), `traces/SCEN-*.jsonl` (46 files with `state_diff` operations), `state-hashes/SCEN-*.json` (46 files), `state-hashes/scenario_hashes.json`
  - `results/SCENARIO-RESULTS.jsonl` (46 records), `INVARIANT-RESULTS.json` (18 invariants passed)
  - `FEATURE-INVENTORY.json` & `COVERAGE.json` (derived; `FEAT-14-READABILITY-AND-HUD` marked `not_observed`)
  - `ISSUES.json` (3 closed issues with real SHA-256 `resolution_hash`), `PLAN-CHANGELOG.md`, `REMEDIATION-RESULTS.json`, `REGRESSION-RESULTS.json`, `CLAIMS-AND-PROVENANCE.json`, `SIMULATION-REPORT.md`
  - `REVIEW-PACKET.md` (binding exact SHA-256 digests of the frozen pre-review artifacts)
- Explicitly absent at the end of `TASK-008`: `INDEPENDENT-REVIEW.md`, `DEVELOPMENT-READINESS.json`, `RUN-MANIFEST.json`.

## Write Scope
- **Permitted Modifications:** None to existing files.
- **Permitted New Files (Pattern-Based):** `artifacts/simulations/full-game/full-game-<NEW_UTC>-<NEW_FIRST8>/**`
- **Protected Paths (Must Not Modify):**
  - `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/**` (Preserved rejected run directory)
  - All source and planning files bound in `TASK-007`.

## Implementation Requirements
- Run `python3 -m coordination.run_full_game_simulation --stage simulate --authorize AUTHORIZE_COMPLETE_GAME_SIMULATION=true`.
- Verify that all 46 scenarios and 18 invariants pass and that `REVIEW-PACKET.md` is under the 40,000-character Astra packet cap.

## Determinism Contract
- Golden replay verification executes `SCEN-E2E-01` twice independently and confirms identical canonical state hashes and boundary hashes.

## Execution Guidance
1. Execute `python3 -m coordination.run_full_game_simulation --stage simulate --authorize AUTHORIZE_COMPLETE_GAME_SIMULATION=true`.
2. Capture the emitted `<NEW_RUN_ID>`.
3. Verify the preserved rejected run's tree hash is unchanged.

## Acceptance Criteria
- `<NEW_RUN_ID>` directory is created exclusively and populated with all pre-review artifacts.
- `INDEPENDENT-REVIEW.md` does not exist yet in `<NEW_RUN_ID>`.
- Preserved rejected run tree SHA-256 remains `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d`.

## Verification
```bash
python3 -c '
import json
from pathlib import Path
from coordination.evidence_pipeline import verify_scenario_trace_integrity
from coordination.content_cache import require_hash
# Verify new run directory pre-review state
runs = sorted(p for p in Path("artifacts/simulations/full-game").iterdir() if p.is_dir() and p.name != "full-game-20261101T102226Z-a8e33043")
assert len(runs) >= 1
run_dir = runs[-1]
assert (run_dir / "REVIEW-PACKET.md").exists()
assert not (run_dir / "INDEPENDENT-REVIEW.md").exists()
corpus = json.loads((run_dir / "CORPUS-MANIFEST.json").read_text())
require_hash(corpus["sha256"])
matrix = json.loads((run_dir / "SCENARIO-MATRIX.json").read_text())
assert len(matrix) == 46
print("Pre-review bundle verified:", run_dir.name)
'
```

## Integration Contract
- Hands off the frozen `<NEW_RUN_ID>` directory and `REVIEW-PACKET.md` to `TASK-009` (Independent Review Invocation).

## Completion Evidence
- `<NEW_RUN_ID>` path and `REVIEW-PACKET.md` SHA-256 recorded in `docs/planning/REMEDIATION-STATE.md`.

## Failure Handling
- If any scenario or invariant fails, do not proceed to `TASK-009`; diagnose and fix in a new uniquely rooted run.

## Scheduling Metadata
- **Parallelization:** `SERIAL_REQUIRED` after `TASK-007`
- **Risk:** `HIGH`
- **Priority:** `P0`
- **Ship Criticality:** `MUST_SHIP`
- **Amortization:** `NET_NEUTRAL`
- **Estimated Sessions:** `0.5` bounded session (~10 mins)
- **Complete Before Freeze Point:** `false` (Executes immediately after code freeze in the Verification & Packaging window)
- **Blocks Packaging/Submission:** `true`
- **Blocked Flag:** `false`
