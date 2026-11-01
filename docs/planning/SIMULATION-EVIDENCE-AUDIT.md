# Complete-game simulation evidence audit and next-agent handoff

Recorded: 2026-11-01  
Audit scope: read-only review of simulation run `full-game-20261101T102226Z-a8e33043`  
Audited root: `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/`  
Current verdict: **REJECT READY; evidence pipeline requires remediation before development**

## Purpose and authority

This document is the durable handoff for the next task. It records what was actually inspected, which claims are supported, which are not, and the required repair order. It does not authorize another simulation, gameplay execution, live-service call, development phase, deployment, or publication.

The current authoritative game plan remains `docs/planning/GAMEPLAN-v2.md` revision 4. The simulation bundle describes a revision-5 candidate, but that candidate was not synchronized into the authoritative plan/context/ledger records.

## Executive assessment

The bundle contains a real deterministic Python kernel and some meaningful assertions. Its manifest integrity is internally consistent: all 115 recorded artifact hashes matched the current artifact bytes, and its recorded authoritative-source hashes matched the current source bytes at audit time.

Those byte-integrity checks do **not** validate the bundle's READY conclusion. The independent-review claim, coverage accounting, predeclared-oracle requirement, raw trace evidence, fixture-reward invariant, candidate-plan binding, and development-readiness decision contain material defects. Development must not proceed from this bundle.

## Critical findings

### AUDIT-01 — Independent Astra review is synthetic, not independently evidenced

Severity: **S0 / report gate invalid**

`coordination/run_full_game_simulation.py` writes `INDEPENDENT-REVIEW.md` directly with reviewer `gpt-6-astra` and verdict `READY`. The same generator hard-codes `MODEL-USAGE.json` status `completed`. The bundle contains no independent executor/tool result proving that Astra received the review packet or authored the verdict.

Evidence:

- `coordination/run_full_game_simulation.py:1756-1797`
- `coordination/run_full_game_simulation.py:1870-1887`
- `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/INDEPENDENT-REVIEW.md`
- `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/MODEL-USAGE.json`

Required correction: the generator may create a pending review packet, but it must never generate the reviewer verdict or mark the model call completed. Invoke Astra/high through the configured agent boundary after freezing the evidence bundle, preserve the actual tool/run evidence, and bind its returned artifact hash.

### AUDIT-02 — Scenario oracles are circular and were not frozen before execution

Severity: **S0 / simulation validity invalid**

The runner executes all scenario functions first and creates `SCENARIO-MATRIX.json` afterward. Every scenario receives the same generic expected oracle: `satisfies category specification without invariant violations`. This cannot demonstrate that expected behavior was declared independently before observed results.

Evidence:

- `coordination/run_full_game_simulation.py:1517-1552`
- scenario-matrix generation after execution in `coordination/run_full_game_simulation.py`
- all 46 matrix entries share one expected-oracle string and omit concrete inputs, seed, dependencies, and exact expected outputs

Required correction: generate and hash the complete scenario matrix before any state transition. Each scenario needs explicit inputs, seed, feature bindings, independent oracle, boundary expectations, and execution dependencies. The runtime must consume the frozen matrix rather than construct expectations from results.

### AUDIT-03 — Fixture hazards can create Hype despite a mandatory invariant forbidding it

Severity: **S1 / mechanics invariant violated**

`FullGameSimulator.submit_command` increments the Hype pool for `fixture`-provenance hazards. Revision 4 and `INV-BOT-ISOLATION` require fixtures and bots to contribute zero bounty/Hype. The reported invariant pass is therefore false or inadequately tested.

Evidence:

- `coordination/full_game_simulator.py:216-248`
- `docs/planning/S1-SIMULATION-PROFILE.md` D-04
- report claim in `SIMULATION-REPORT.md`

Required correction: fixture hazards may exercise fictional arithmetic only in an explicitly synthetic ledger that cannot alter the live-participant pool. Add an adversarial fixture-origin test and an independent invariant oracle.

### AUDIT-04 — Reported 100% feature coverage is false

Severity: **S1 / coverage claim invalid**

`FEAT-14-READABILITY-AND-HUD` is marked `passed/covered` before scenario execution but appears in zero scenario result feature lists. No render capture or mobile/compressed-video readability observation exists. The simulation prompt required this feature to be marked unobserved if no render path existed.

Related overclaims:

- adaptive audio validates state labels, not actual sound, voiceover intelligibility, mute/accessibility behavior, or rights;
- the public-demo credibility scenario sets a Boolean/digest without independently auditing claims or a rendered three-minute timeline;
- bullet-time checks tick progression, not the visual overlay or recorded telemetry presentation.

Evidence:

- `coordination/run_full_game_simulation.py:250-286`
- `coordination/run_full_game_simulation.py:1361-1431`
- `FEATURE-INVENTORY.json`
- `results/SCENARIO-RESULTS.jsonl`

Required correction: derive feature status from scenario evidence. Use `not_observed` or `blocked_by_implementation` when no qualifying render/audio/live path exists. Do not convert event-state coverage into visual, audio, accessibility, or live-integration evidence.

### AUDIT-05 — Most command and trace artifacts are placeholders

Severity: **S1 / reproducibility incomplete**

Forty-one of 46 command files contain only `{scenario_id, execution_mode}`. Forty-one of 46 trace files contain only final scenario summary fields. The runner creates these placeholders after execution when substantive artifacts are absent. They are not replayable canonical command streams or raw evidence.

Evidence:

- fallback artifact creation in `coordination/run_full_game_simulation.py` after golden replay execution
- `artifacts/.../commands/`
- `artifacts/.../traces/`

Required correction: fail the scenario if the canonical command stream, state-diff trace, boundary hashes, and oracle evaluations were not captured during execution. Never backfill missing evidence with a passing summary.

### AUDIT-06 — Revision 5 is not an authoritative, synchronized candidate

Severity: **S1 / plan remediation incomplete**

`PLAN-CHANGELOG.md` proposes steering lockout/clamping, nominal speed, and booth placement, but the current plan remains revision 4. No revision-5 machine-readable plan, context, status, directive-ledger update, static gate tests, or genuine candidate hash exists. `DEVELOPMENT-READINESS.json` uses the placeholder string `rev5-candidate-bound` rather than a SHA-256.

The booth placements are also a third design change not represented by either of the two recorded issues.

Evidence:

- `docs/planning/GAMEPLAN-v2.md:1-3`
- `artifacts/.../PLAN-CHANGELOG.md`
- `artifacts/.../DEVELOPMENT-READINESS.json`

Required correction: decide whether each candidate change is a deterministic clarification or human product decision. Record every change as an issue/decision, then synchronize approved changes across all current plan and policy records. Bind the resulting bytes with real hashes before regression or review.

### AUDIT-07 — Development readiness contradicts unresolved gates and evidence

Severity: **S1 / readiness conclusion invalid**

`DEVELOPMENT-READINESS.json` sets `ready: true` and `review_verdict: READY` while listing D-06, D-07, and D-08 as unresolved. `HUMAN-DECISIONS.md` says those choices require approval before product development. The review verdict is synthetic, and the candidate plan hash is a placeholder.

Evidence:

- `DEVELOPMENT-READINESS.json`
- `HUMAN-DECISIONS.md`
- `INDEPENDENT-REVIEW.md`

Required correction: readiness must be false until the evidence defects are repaired, mandatory decisions for the proposed development milestone are resolved, the candidate plan is genuinely bound, regression passes, and a real independent review returns READY.

### AUDIT-08 — Corpus manifest hash is not a SHA-256 digest

Severity: **S2 / reproducibility metadata invalid**

`CORPUS-MANIFEST.json.sha256` is `42-reused-corpus-100k`, not a SHA-256 digest. A 100,000-message corpus appears to have been generated through `generate_viewer_corpus`, but the manifest does not bind it correctly and the corpus itself is not retained as a content-addressed artifact.

Evidence:

- `coordination/run_full_game_simulation.py:1503-1515`
- `CORPUS-MANIFEST.json`

Required correction: record the generator source hash, version, seed, count, canonical corpus digest, and either the content-addressed corpus artifact or a verified deterministic regeneration recipe.

### AUDIT-09 — Immutable-run guarantees were not enforced

Severity: **S2 / provenance risk**

The run ID is a source-code constant and the artifact setup uses existing directories without failing on collision. Files are written with overwrite semantics. The review packet hashes `DEVELOPMENT-READINESS.json` before that file is created in the current code order, so a fresh run should fail unless a stale file already exists; the successful bundle therefore indicates reuse of the same directory or prior residue.

Evidence:

- constant `RUN_ID` and `ARTIFACT_DIR` in `coordination/run_full_game_simulation.py`
- `setup_artifact_dirs` uses `exist_ok=True`
- review packet creation precedes development-readiness creation
- artifact modification timestamps show files were rewritten in one existing run directory

Required correction: derive a unique run ID at invocation, create the root with exclusive semantics, fail if it exists, finalize artifacts in dependency order, and seal the manifest last. A rerun must use a new root.

## Evidence that remains useful

- All 115 manifest artifact hashes matched the current artifact bytes at audit time.
- Recorded authoritative-source hashes matched current source bytes at audit time.
- The fixed-step kernel contains genuine logic and multiple meaningful assertions for clock boundaries, controls, quorum, reward settlement, and deterministic replay.
- `SCENARIO-RESULTS.jsonl` contains 46 result records.
- Two identical executions of the selected golden kernel path appear to have produced the same canonical digest.
- The two identified revision-4 ambiguities—transition admission/clamping and nominal route-speed calibration—are legitimate plan questions, although their proposed resolutions are not yet approved or synchronized.

These facts support further repair work; they do not support the READY verdict or complete-game verification.

## Required next action

Perform a bounded **simulation evidence-pipeline remediation**, not product development:

1. Preserve the existing run directory unchanged as rejected evidence.
2. Correct the simulator's fixture-reward violation.
3. Replace hard-coded feature pass states with evidence-derived statuses.
4. Define and hash exact scenario oracles before execution.
5. Capture substantive canonical commands/traces for every executed scenario.
6. Add explicit negative tests for artifact provenance, fixture rewards, missing feature coverage, placeholder traces, and forged review outputs.
7. Create a real revision-5 candidate only after human approval of meaningful product choices; synchronize every authoritative record and bind a real hash.
8. Produce a new, unique run directory; never overwrite the rejected run.
9. Freeze the new evidence bundle, then invoke one genuine Astra/high independent review through the configured agent boundary.
10. Set development readiness from observed gate results rather than writing it as a constant.

Do not rerun gameplay or the simulation without a new explicit user authorization. Do not silently resolve D-06, D-07, D-08, booth placement, or other product choices.

## Acceptance criteria for the remediation task

- The rejected run remains byte-for-byte unchanged.
- A fresh run cannot start without explicit authorization and a non-existing run root.
- Scenario matrix and concrete oracles are frozen before the first tick.
- Every executed scenario has replayable commands, state-diff trace, boundary hashes, and independent oracle results.
- Fixture/bot provenance cannot create or receive live Hype or affect human quorum.
- Feature coverage is mechanically derived; unobserved visual/audio/live claims remain unobserved.
- The corpus has a valid canonical SHA-256 binding.
- Candidate plan changes have complete issue/decision provenance and synchronized source hashes.
- Independent review output cannot be generated by the simulator.
- A genuine Astra/high result is recorded with invocation evidence and bound inputs/outputs.
- `DEVELOPMENT-READINESS.ready` remains false unless every declared gate actually passes.

## Suggested next-agent instruction

> Read `docs/planning/SIMULATION-EVIDENCE-AUDIT.md` as the authoritative handoff. Repair the simulation evidence pipeline according to its required next action and acceptance criteria. Preserve the rejected run unchanged. Do not rerun the simulation, resolve product decisions, or begin product development without separate explicit authorization. Use codebase-memory first, the configured model-routing policy, bounded owned paths, deterministic scripted actors, and genuine independent review evidence.

## Key artifact links

- Rejected report: `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/SIMULATION-REPORT.md`
- Rejected readiness claim: `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/DEVELOPMENT-READINESS.json`
- Synthetic review artifact: `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/INDEPENDENT-REVIEW.md`
- Simulation generator: `coordination/run_full_game_simulation.py`
- Simulation kernel: `coordination/full_game_simulator.py`
- Current authoritative plan: `docs/planning/GAMEPLAN-v2.md`
