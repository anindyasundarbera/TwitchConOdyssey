# TASK-005 — Authoritative Revision 5 Plan, Context, Directive Ledger & Static Rule Synchronization

## Task Identity
- **Task ID:** `TASK-005`
- **Title:** Authoritative Revision 5 Plan, Context, Directive Ledger & Static Rule Synchronization
- **Contract Version:** `1.0.0`
- **Planning Status:** `READY`
- **Ship Criticality:** `MUST_SHIP`
- **Risk Classification:** `HIGH` (Touches pinned required sources in `config/directive-policy.json` and static test contracts in `tests/test_gameplan_rules.py` and `tests/test_context_contract.py`)
- **Linked Audit IDs:** `AUDIT-06`, `AUDIT-07`
- **Linked Decision IDs:** `DECISION-01` (`D-06`), `DECISION-02` (`D-07`), `DECISION-03` (`D-08`), `DECISION-04` (`D-09` / `ISSUE-SIM-01..03`)

## Objective
Close `AUDIT-06` and unblock `AUDIT-07` by synchronizing the recorded decisions in `docs/planning/DECISIONS.md` (`DECISION-01..04`: `D-06` phase-boundary failover, `D-07` 2-key signed hotfix allowlist, `D-08` simulation vs live submission readiness split, and `D-09` steering lockout/clamping, `100/88` nominal speed calibration, and `35.0/60.0/80.0/100.0` diegetic booth placement) across all authoritative planning records (`docs/planning/GAMEPLAN-v2.md` Revision 5, `docs/planning/gameplan-v2.json` Revision 5, `docs/planning/S1-SIMULATION-PROFILE.md`, `docs/planning/CONTEXT-v2.md`, `docs/planning/STATUS.md`, `docs/planning/USER-DIRECTIVE-AUDIT.md`, `config/directive-policy.json` Revision 8) and updating static contract tests (`tests/test_gameplan_rules.py`, `tests/test_context_contract.py`).

## Checkpoint Reference
- **`AUDIT-06` (S1 / plan remediation incomplete):** "`PLAN-CHANGELOG.md` proposes steering lockout/clamping, nominal speed, and booth placement, but the current plan remains revision 4. No revision-5 machine-readable plan, context, status, directive-ledger update, static gate tests, or genuine candidate hash exists. `DEVELOPMENT-READINESS.json` uses the placeholder string `rev5-candidate-bound` rather than a SHA-256."

## Dependencies
- **Hard Dependencies:** Recorded `DECISION-01..04` in `docs/planning/DECISIONS.md` (completed at planning baseline).
- **Integration Dependencies:** `coordination/context_contract.py` (validates `config/directive-policy.json` schema and `required_paths` hashes).
- **Soft Dependencies:** `TASK-001`..`TASK-004` (can run in parallel with Wave 1 code tasks since file write scopes are completely disjoint).
- **External Prerequisites:** None.

## Preconditions
Run the repository context compiler before editing:
```bash
python3 -m coordination.context_contract --task planner_orchestrator --phase plan \
  --owned-path docs/planning/GAMEPLAN-v2.md \
  --owned-path docs/planning/gameplan-v2.json \
  --owned-path docs/planning/S1-SIMULATION-PROFILE.md \
  --owned-path docs/planning/CONTEXT-v2.md \
  --owned-path docs/planning/STATUS.md \
  --owned-path docs/planning/USER-DIRECTIVE-AUDIT.md \
  --owned-path config/directive-policy.json \
  --owned-path tests/test_gameplan_rules.py \
  --owned-path tests/test_context_contract.py
```

## Context to Load
- `docs/planning/SIMULATION-EVIDENCE-AUDIT.md:100-129` (`AUDIT-06`, `AUDIT-07`)
- `docs/planning/DECISIONS.md` (`DECISION-01` through `DECISION-04`)
- `docs/planning/GAMEPLAN-v2.md:1-109`
- `docs/planning/gameplan-v2.json:1-643`
- `docs/planning/S1-SIMULATION-PROFILE.md:1-63`
- `docs/planning/CONTEXT-v2.md:1-33`
- `config/directive-policy.json:505-680`
- `tests/test_gameplan_rules.py:1-212`
- `tests/test_context_contract.py:102-136`

## Input Contracts
- Delegated decision records `DECISION-01..04` in `docs/planning/DECISIONS.md`.
- Validation rules in `coordination/context_contract.py:211-247` (note: `context_contract._validate` checks `selected_decisions` for `D-01..D-05` and requires `unresolved_decisions` to be a non-empty list of `{id, status: "unresolved", rule, gate, source_path}` — e.g., `live_submission_and_external_service_gate` for `before_submission` while `D-06`, `D-07`, `D-08` simulation/development rules are recorded in `GAMEPLAN-v2.md`, `gameplan-v2.json`, and `DECISIONS.md`).

## Output Contracts
1. `docs/planning/S1-SIMULATION-PROFILE.md`:
   - Updated with the Revision 5 deterministic clarifications and delegated simulation-profile rules:
     - `D-01`: discrete lanes `0, 1, 2`, `0.5s` (`10`-tick) linear interpolation, edge clamping (`rejected`), in-flight transition lockout (`rejected`), lateral collision overlap `|x - 1.0| < 0.4`.
     - `D-02` / `D-05`: `100.0`-unit route across the 5 San Diego segments (`[0,25), [25,50), [50,75), [75,95), [95,100]`), nominal free speed `100/88` units/s (`88.0s` nominal completion, `89.2s` with max 3 collisions < `90.0s` deadline), diegetic booth waypoints at `35.0%` (`twitch_booth`), `60.0%` (`codex_booth`), `80.0%` (`aws_booth`), and `100.0%` (`fictional_main_stage`).
     - `D-06` (`failover_contract`), `D-07` (`hotfix_contract`), `D-08` (`submission_and_coverage_honesty`) recorded as `delegated_for_s1_remediation_provisional` in [`docs/planning/DECISIONS.md`](DECISIONS.md).
2. `docs/planning/GAMEPLAN-v2.md` & `docs/planning/gameplan-v2.json`:
   - Incremented to **Revision 5** (`"number": 5`), recording the exact baseline Revision 4 SHA-256 (`1b43be51add9d6c5e1cc2b6378e66a7f48fb76985435693b3dcf303ad6234937` for JSON / `a6967a24601f259be027ed7fbebed5ad6e0784d4a7f7b7f6c0a2c3967e47e6ed` for MD).
   - `D-01` and `D-05` parameters in `gameplan-v2.json` include the transition lockout/edge clamping, `100/88` nominal speed, district progress ranges, and booth progress waypoints (`35.0, 60.0, 80.0, 100.0`).
   - `delegated_remediation_decisions` section in `gameplan-v2.json` records `D-06`, `D-07`, `D-08`, and `D-09` (`ISSUE-SIM-01..03`) bound to `docs/planning/DECISIONS.md`, leaving zero unresolved product decisions blocking S1 simulation or bounded offline-slice development while keeping live external Twitch/video submission gated under `live_submission_gate`.
3. `docs/planning/CONTEXT-v2.md`, `docs/planning/STATUS.md`, `docs/planning/USER-DIRECTIVE-AUDIT.md`:
   - Synchronized to describe Revision 5 and Ledger Revision 8.
4. `config/directive-policy.json`:
   - Incremented to **Revision 8** (`"revision": 8`).
   - Moves Revision 7 `D-01..D-05` entries into `superseded_decisions` (`"superseded_in_revision": 8`, `"prior_source_sha256": "a8e3304309fd81eb795f5b7e5b609b66a65f5a3dae4f32ef0c4ded369049d2a4"`) and updates active `selected_decisions` `D-01..D-05` with the Revision 5 clarifications.
   - Updates `unresolved_decisions` so `failover_and_hotfix_trust` is superseded by recorded `DECISION-01..03` in `docs/planning/DECISIONS.md` and replaced by `live_submission_external_capture` (`gate: "before_live_submission"`, `source_path: "docs/planning/CONTEXT-v2.md"`), satisfying `context_contract._validate` while clearing the development-readiness blocker (`AUDIT-07`).
   - Reconciles all SHA-256 hashes in `required_paths`.
5. `tests/test_gameplan_rules.py` & `tests/test_context_contract.py`:
   - Updated to assert `plan["revision"]["number"] == 5`, `policy["revision"] == 8`, preserved Revision 7 superseded decision history, and the new Revision 5 parameters (`transition_lockout`, `edge_clamping`, `nominal_route_seconds: 88`, `booth_waypoints`, `delegated_remediation_decisions`).

## Write Scope
- **Permitted Modifications (Exact):**
  - `docs/planning/GAMEPLAN-v2.md`
  - `docs/planning/gameplan-v2.json`
  - `docs/planning/S1-SIMULATION-PROFILE.md`
  - `docs/planning/CONTEXT-v2.md`
  - `docs/planning/STATUS.md`
  - `docs/planning/USER-DIRECTIVE-AUDIT.md`
  - `config/directive-policy.json`
  - `tests/test_gameplan_rules.py`
  - `tests/test_context_contract.py`
- **Permitted New Files:** None.
- **Protected Paths (Must Not Modify):**
  - `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/**` (Preserved rejected run directory)
  - `docs/planning/S1-ASTRA-REVIEW.md`, `docs/planning/S1-ASTRA-REVIEW-RESPONSE.md` (Historical review records must keep their exact SHA-256 digests!)

## Implementation Requirements
- Preserve `docs/planning/S1-ASTRA-REVIEW.md` (`29280f55a0d69fd4f8cb06d70f22e7daa23cf0d511c1e0b8eb8a82614c71e530`) and `docs/planning/S1-ASTRA-REVIEW-RESPONSE.md` (`4cf48c7fcc2492529b2b7b13c68cce251c7a6356453aa5582c37499cd8bf15a3`) byte-for-byte unchanged.
- In `gameplan-v2.json` and `config/directive-policy.json`, ensure every `selected_decisions[i]["rule"]` in `directive-policy.json` equals `" ".join(record["selected_constraints"])` in `gameplan-v2.json` (enforced by `tests/test_gameplan_rules.py:38`).

## Determinism Contract
- **Byte-Bound Synchronization:** `context_contract.py` verifies that every file in `required_paths` matches its exact SHA-256 digest in `config/directive-policy.json` and fails closed on any drift.
- **Anti-Forgery Check:** `tests/test_gameplan_rules.py` and `tests/test_context_contract.py` verify that mutating any Revision 5 parameter or breaking `selected_constraints` synchronization raises an assertion/validation error.

## Execution Guidance
1. Update `S1-SIMULATION-PROFILE.md`, `GAMEPLAN-v2.md`, `gameplan-v2.json`, `CONTEXT-v2.md`, `STATUS.md`, and `USER-DIRECTIVE-AUDIT.md` to Revision 5.
2. Update `tests/test_gameplan_rules.py` and `tests/test_context_contract.py` for Revision 5 / Ledger Revision 8.
3. Recompute SHA-256 hashes of all `required_paths` and update `config/directive-policy.json` to Revision 8.
4. Run `context_contract --validate-only` and the static unit test suites.

## Acceptance Criteria
- `GAMEPLAN-v2.md` and `gameplan-v2.json` are at Revision 5 with complete issue/decision provenance (`ISSUE-SIM-01..03`, `DECISION-01..04`).
- `config/directive-policy.json` is at Revision 8, retaining Revision 6 and Revision 7 `superseded_decisions` with their exact `prior_source_sha256`.
- `python3 -m coordination.context_contract --task development --phase plan --validate-only` exits 0.
- `python3 -m unittest tests.test_gameplan_rules tests.test_context_contract tests.test_city_setting -v` passes 100%.

## Verification
```bash
python3 -m coordination.context_contract --task development --phase plan --validate-only && \
python3 -m unittest tests.test_gameplan_rules tests.test_context_contract tests.test_city_setting -v
```

## Integration Contract
- Provides the real Revision 5 SHA-256 digest of `docs/planning/GAMEPLAN-v2.md` and `docs/planning/gameplan-v2.json` consumed by `TASK-004` / `TASK-008` in `ISSUES.json`, `PLAN-CHANGELOG.md`, `DEVELOPMENT-READINESS.json`, and `RUN-MANIFEST.json`.

## Completion Evidence
- Updated plan/ledger files and passing static test suite output recorded in `docs/planning/REMEDIATION-STATE.md`.

## Failure Handling
- If `tests/test_gameplan_rules.py` fails on `ledger["rule"] == " ".join(record["selected_constraints"])`, copy the exact joined string from `gameplan-v2.json` into `config/directive-policy.json` and refresh hashes.

## Scheduling Metadata
- **Parallelization:** `PARALLEL_WITH_ISOLATION` (Can run in Wave 1/2 parallel with `TASK-001..004` as write scopes do not overlap)
- **Risk:** `HIGH`
- **Priority:** `P0`
- **Ship Criticality:** `MUST_SHIP`
- **Amortization:** `NET_NEUTRAL`
- **Estimated Sessions:** `1` bounded session (~20 mins)
- **Complete Before Freeze Point:** `true`
- **Blocks Packaging/Submission:** `true`
- **Blocked Flag:** `false`
