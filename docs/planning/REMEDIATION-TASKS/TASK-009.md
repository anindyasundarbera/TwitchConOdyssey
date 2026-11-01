# TASK-009 — Genuine Independent Review Invocation via Configured Agent Boundary & Bundle Finalization (`AUDIT-01`, `AUDIT-07`, `AUDIT-09`)

## Task Identity
- **Task ID:** `TASK-009`
- **Title:** Genuine Independent Review Invocation via Configured Agent Boundary & Bundle Finalization (`AUDIT-01`, `AUDIT-07`, `AUDIT-09`)
- **Contract Version:** `2.0.0`
- **Baseline Commit SHA (`BASELINE_SHA`):** `2bb0b538bcfed216590ec49039e9972c5e363f0d` (`plan-baseline/remediation-v2.0`, branch `main`)
- **Reviewer Authorization Citation (§8 / §12.4):** Authorized via `config/directive-policy.json` active directive `remediation_rerun_and_decision_delegation` (lines 499–531, provenance `docs/planning/SIMULATION-EVIDENCE-AUDIT.md` locator `"Required next action"` step 9 line 181), `tasks.plan_review` (lines 85–88), `model_allocation` (line 289), `bounded_subagents` (line 313), and `config/model-policy.json` (`principal_review` -> `provider: "codex_subagent", model: "gpt-6-astra", reasoning_effort: "high"`), using the local `invoke_subagent` boundary with fresh narrow context while external network/live-service API calls remain disabled (`live_model_calls_authorized: false`).
- **Planning Status:** `PLANNED`
- **Ship Criticality:** `MUST_SHIP`
- **Risk Classification:** `CRITICAL` (Closes S0 `AUDIT-01`, S1 `AUDIT-07`, and S2 `AUDIT-09`)
- **Linked Audit IDs:** `AUDIT-01`, `AUDIT-07`, `AUDIT-09`
- **Linked Decision IDs:** `DECISION-01..04`

## Objective
Close `AUDIT-01`, `AUDIT-07`, and `AUDIT-09` by:
1. Compiling a fresh narrow `plan_review` context-contract packet binding `artifacts/simulations/full-game/<NEW_RUN_ID>/INDEPENDENT-REVIEW.md` and `REVIEW-INVOCATION.json`.
2. Invoking an independent review subagent (`invoke_subagent`) with a fresh context containing only the compiled packet, `REVIEW-PACKET.md`, and the paths to the frozen evidence bundle in `<NEW_RUN_ID>` (no conversation history, <=250-word return summary plus owned artifact paths).
3. Having the independent reviewer inspect the frozen artifacts and audit criteria (`AUDIT-01..09`), write `INDEPENDENT-REVIEW.md` with its genuine verdict (`READY` or `REVISE`), and record `REVIEW-INVOCATION.json` binding the subagent `conversationId`, `packet_hash`, `prompt_hash`, and `output_hash`.
4. Running `python3 -m coordination.run_full_game_simulation --stage finalize --run-id <NEW_RUN_ID>` to verify the independent review, write `MODEL-USAGE.json`, compute `DEVELOPMENT-READINESS.json` mechanically from observed gate results, write `README.md`, and seal `RUN-MANIFEST.json` last.

## Checkpoint Reference
- **`AUDIT-01` (S0 / report gate invalid):** "Required correction: the generator may create a pending review packet, but it must never generate the reviewer verdict or mark the model call completed. Invoke Astra/high through the configured agent boundary after freezing the evidence bundle, preserve the actual tool/run evidence, and bind its returned artifact hash."
- **`AUDIT-07` (S1 / readiness conclusion invalid):** "Required correction: readiness must be false until the evidence defects are repaired, mandatory decisions for the proposed development milestone are resolved, the candidate plan is genuinely bound, regression passes, and a real independent review returns READY."

## Dependencies
- **Hard Dependencies:** `TASK-008` (Frozen pre-review evidence bundle `<NEW_RUN_ID>` and `REVIEW-PACKET.md`).
- **Integration Dependencies:** `coordination/context_contract.py`, `coordination/model_router.py`, `coordination/run_full_game_simulation.py` (`--stage finalize`).
- **Soft Dependencies:** None.
- **External Prerequisites:** Configured `invoke_subagent` agent boundary (available natively in the execution environment; if unavailable, must set status to `BLOCKED_REVIEW_UNAVAILABLE` and `ready: false` per `S1-SIMULATION-RUN-PROMPT.md:317`).

## Preconditions
Run the repository context compiler before delegating the review:
```bash
python3 -m coordination.context_contract --task plan_review --phase plan \
  --owned-path artifacts/simulations/full-game/<NEW_RUN_ID>/INDEPENDENT-REVIEW.md \
  --owned-path artifacts/simulations/full-game/<NEW_RUN_ID>/REVIEW-INVOCATION.json
```

## Context to Load
- `AGENTS.md:3-8` (Subagent inference boundary: configured route, fresh narrow context, <=250-word return plus owned artifact paths, no full conversation history)
- `docs/planning/SIMULATION-EVIDENCE-AUDIT.md:21-36, 181-199`
- `artifacts/simulations/full-game/<NEW_RUN_ID>/REVIEW-PACKET.md`

## Input Contracts
- Compiled `plan_review` packet (`model: "gpt-6-astra"`, `reasoning_effort: "high"`, `max_input_chars: 40000`).
- Frozen pre-review artifacts in `artifacts/simulations/full-game/<NEW_RUN_ID>/`.

## Output Contracts
- `artifacts/simulations/full-game/<NEW_RUN_ID>/INDEPENDENT-REVIEW.md` and `artifacts/simulations/full-game/<NEW_RUN_ID>/INDEPENDENT-REVIEW.json`: written by the independent reviewer agent, containing bound artifact hashes from `REVIEW-PACKET.md`, independent verification of `AUDIT-01..09` closures, limitations, and exact verdict `READY` or `REVISE`.
- `artifacts/simulations/full-game/<NEW_RUN_ID>/REVIEW-INVOCATION.json`: records `{schema_version, reviewer_role, configured_model, configured_effort, subagent_conversation_id, packet_hash, review_packet_sha256, prompt_sha256, independent_review_sha256, independent_review_json_sha256, verdict, evidence_origin: "independent_subagent_review"}`.
- Finalized post-review artifacts in `<NEW_RUN_ID>/` produced by `--stage finalize`:
  - `MODEL-USAGE.json`
  - `DEVELOPMENT-READINESS.json` (with derived `ready` boolean across all readiness predicates)
  - `README.md`
  - `RUN-MANIFEST.json` (sealing all artifact SHA-256 digests last; manifest entry count derived mechanically from actual emitted files in `<NEW_RUN_ID>/`, never copied from the rejected run's 116 count per §12.5)

## Write Scope
- **Permitted Modifications:** None to existing pre-review files in `<NEW_RUN_ID>/` (verified by `RUN-MANIFEST.json` and `REVIEW-PACKET.md` hashes).
- **Permitted New Files (Exact within `<NEW_RUN_ID>`):**
  - `artifacts/simulations/full-game/<NEW_RUN_ID>/INDEPENDENT-REVIEW.md`
  - `artifacts/simulations/full-game/<NEW_RUN_ID>/INDEPENDENT-REVIEW.json`
  - `artifacts/simulations/full-game/<NEW_RUN_ID>/REVIEW-INVOCATION.json`
  - `artifacts/simulations/full-game/<NEW_RUN_ID>/MODEL-USAGE.json`
  - `artifacts/simulations/full-game/<NEW_RUN_ID>/DEVELOPMENT-READINESS.json`
  - `artifacts/simulations/full-game/<NEW_RUN_ID>/README.md`
  - `artifacts/simulations/full-game/<NEW_RUN_ID>/RUN-MANIFEST.json`
- **Protected Paths (Must Not Modify):**
  - `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/**` (Preserved rejected run directory)
  - All frozen pre-review artifacts in `<NEW_RUN_ID>/` listed in `REVIEW-PACKET.md`.

## Implementation Requirements
1. Compile the `plan_review` packet via `coordination.context_contract`.
2. Invoke the review subagent with a prompt under 40,000 characters containing the compiled packet metadata and the path to `artifacts/simulations/full-game/<NEW_RUN_ID>/REVIEW-PACKET.md`. Instruct the subagent to independently audit the bundle against `docs/planning/SIMULATION-EVIDENCE-AUDIT.md` acceptance criteria (`AUDIT-01..09`), write `INDEPENDENT-REVIEW.md` directly (if using a write-capable subagent) or return the structured review text to be bound with the subagent's `conversationId` in `REVIEW-INVOCATION.json`, and return `<= 250` words.
3. Run `python3 -m coordination.run_full_game_simulation --stage finalize --run-id <NEW_RUN_ID>`.
4. Verify that every hash in `REVIEW-PACKET.md` and `RUN-MANIFEST.json` matches the on-disk bytes.

## Determinism Contract
- Pre-review artifact bytes are immutable before `INDEPENDENT-REVIEW.md` is created; `verify_independent_review_artifact` verifies that none of the hashes listed in `REVIEW-PACKET.md` changed between Stage 1 (`simulate`) and Stage 2 (`finalize`).
- If the independent review returns `REVISE` or is unavailable, `compute_development_readiness` deterministically sets `ready: false`.

## Execution Guidance
1. Run `context_contract --task plan_review`.
2. Launch the independent reviewer via `invoke_subagent` with fresh narrow context.
3. Record `REVIEW-INVOCATION.json` with the subagent `conversationId` and hashes.
4. Run `--stage finalize --run-id <NEW_RUN_ID>`.

## Acceptance Criteria
- `INDEPENDENT-REVIEW.md` is authored through the independent subagent invocation, not by `run_full_game_simulation.py`.
- `REVIEW-INVOCATION.json` binds the subagent `conversationId`, `packet_hash`, `review_packet_sha256`, and `independent_review_sha256`.
- `DEVELOPMENT-READINESS.json` derives `ready` from observed gates and binds the real 64-hex SHA-256 of `GAMEPLAN-v2.md` Revision 5.
- `RUN-MANIFEST.json` seals all files in `<NEW_RUN_ID>` with 100% matching SHA-256 digests.

## Verification
```bash
python3 -m unittest tests.test_full_game_simulation -v
```

## Integration Contract
- Hands off the sealed `<NEW_RUN_ID>` bundle to `TASK-010` for final checkpoint acceptance verification and state logging.

## Completion Evidence
- Subagent `conversationId`, `INDEPENDENT-REVIEW.md` SHA-256, `DEVELOPMENT-READINESS.json` SHA-256, and `RUN-MANIFEST.json` SHA-256 recorded in `docs/planning/REMEDIATION-STATE.md`.

## Failure Handling
- Per `config/model-policy.json` and `S1-SIMULATION-RUN-PROMPT.md`: one review call only; no automatic retry or silent fallback. If the reviewer returns `REVISE`, `DEVELOPMENT-READINESS.json.ready` must be set to `false` and the findings reported transparently.

## Scheduling Metadata
- **Parallelization:** `SERIAL_REQUIRED` after `TASK-008`
- **Risk:** `CRITICAL`
- **Priority:** `P0`
- **Ship Criticality:** `MUST_SHIP`
- **Amortization:** `NET_NEUTRAL`
- **Estimated Sessions:** `1` bounded session (~15 mins)
- **Complete Before Freeze Point:** `false` (Executes in the Review & Packaging window on frozen code)
- **Blocks Packaging/Submission:** `true`
- **Blocked Flag:** `false`
