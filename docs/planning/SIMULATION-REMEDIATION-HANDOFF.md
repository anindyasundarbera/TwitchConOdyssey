# Simulation Remediation Handoff

Status: implementation handoff for a fresh Codex session  
Recorded: 2026-11-01  
Repository: `/home/anindyasundar-bera/Projects/hackathon/TwitchConOdyssey`  
Current candidate: game plan Revision 5; selected design remains unverified  
Current sealed run: `artifacts/simulations/full-game/full-game-20261101T164201Z-2647e033/`

## Objective

Close the open findings from the sealed Revision-5 deterministic simulation, create fresh evidence without modifying historical runs, and obtain a genuine configured-gate review before declaring the plan ready. This is evidence-pipeline remediation, not product development or live-service validation.

## Mandatory session bootstrap

Do not forward prior chat history. Start from this file and run:

```bash
python3 -m coordination.context_contract \
  --task complex_coding_debugging --phase plan \
  --owned-path <each-file-the-agent-will-edit>
```

Read the emitted directives, gate, hashes, routing decision and unresolved decisions. Stop on conflicts or stale bindings. Use codebase-memory first for code discovery with project `home-anindyasundar-bera-Projects-hackathon-TwitchConOdyssey`.

Configured implementation route: `codex_subagent/gpt-6.1-sol`, effort `high`. Use fresh narrow packets and return no more than 250 words plus owned artifact paths. Do not retry, escalate or substitute models automatically. Reserve `codex_subagent/gpt-6-astra`, effort `high`, for the final independent review gate.

## Authoritative inputs

Read in this order:

1. `AGENTS.md`
2. `config/directive-policy.json`
3. `docs/planning/SIMULATION-HANDOFF-full-game-20261101T164201Z-2647e033.md`
4. `docs/planning/SIMULATION-EVIDENCE-AUDIT-full-game-20261101T164201Z-2647e033.md`
5. Current sealed bundle files: `DEVELOPMENT-READINESS.json`, `INDEPENDENT-REVIEW.md`, `REVIEW-INVOCATION.json`, `REVIEW-PACKET.md`, `RUN-MANIFEST.json`
6. Code/tests discovered through codebase-memory, especially `compute_development_readiness` and the two-stage simulation test.

Identity checks already reproduced by the receiving review:

- Handoff SHA-256: `2f640ff6fcf171b6e0b1a0bd0f4082d51e7c05aebcdfa781073ff05ad29d51db` (171 lines).
- Current bundle: 164 files; 163/163 manifest entries matched.
- Source bindings: 30/30 matched, no drift at review time.
- Review-chain verifier passed with verdict `REVISE` and disclosed substitute `ollama-cloud/kimi-k3/high`.
- Golden replay reproduced `5e7c32e9ec752e2bcf07cacb8345753fda730edfb88e04be4614c31d3f162460`.
- These checks bind bytes and deterministic behavior only; they do not prove live Twitch/OpenAI/AWS behavior, rendering, audio, accessibility, security, latency, fairness or stage reliability.

## Findings to close

### R1 — Fail-open and hard-coded readiness gates (blocking)

`coordination/evidence_pipeline.py::compute_development_readiness` hard-codes Revision 5, 46 scenarios and 18 invariants. Missing evidence defaults three gates to `True`: `corpus_hash_valid`, `all_46_traces_substantive`, and `feature_coverage_honestly_derived`. `blocking_issues_count` and unresolved decisions also have permissive defaults.

Reproduced defect: copy the sealed bundle to a temp directory, remove `CORPUS-MANIFEST.json`, call `compute_development_readiness(temp)`, and it still reports `corpus_hash_valid: true`.

Required result:

- Derive expected scenario/invariant/revision requirements from frozen, hash-bound inputs rather than literals.
- Every unavailable, malformed, inconsistent or unevaluated predicate must fail closed.
- Do not accept caller-supplied `True` without validating bound evidence when `run_dir` is provided.
- Add negative tests for each missing/corrupt prerequisite and for disagreement between aggregates and raw evidence.

### R2 — Regression test assumes every finalized bundle is READY (blocking)

The current targeted suite produced 79 passes and one failure. `tests/test_full_game_simulation.py::test_positive_two_stage_simulation_and_finalization_in_isolated_tempdir` scans every finalized non-rejected bundle, then asserts every review verdict is `READY` and every readiness object is true. The intentionally sealed `REVISE` run therefore fails at the `READY` assertion.

Required result:

- Test the isolated positive fixture as `READY`.
- Validate preserved repository bundles according to their own manifest/status/verdict, not a universal `READY` assumption.
- A valid sealed `REVISE`/`completed_not_ready` bundle must pass integrity checks while remaining not ready.
- Do not weaken verification or exclude the current bundle merely to make the suite green.

### R3 — Audit traceability and invariant completeness

Open: `AUDIT-11`, `AUDIT-12`, `AUDIT-14`.

- The frozen matrix lacks explicit regression coverage mapping for `AUDIT-01..09`.
- `ISSUES.json` contains only `ISSUE-SIM-01..03`, not one closure record per audit finding.
- Six additional invariants required by the prior remediation prompt are not evaluated.

Required result:

- Introduce a machine-readable audit-finding ledger with stable IDs, status, evidence paths and resolution hashes.
- Bind every audit finding to a dedicated scenario or negative/static validator as appropriate; do not pretend pipeline/provenance checks are gameplay scenarios.
- Recover the exact six requirements from the prior audit/prompt records; do not invent replacements.
- Derive readiness from the ledger and evaluated invariant catalog, not fixed counts.

### R4 — Review provenance and packet coverage

Open: `AUDIT-15`, `AUDIT-18`.

- Simulator protection covers `INDEPENDENT-REVIEW.md/.json` but not `REVIEW-INVOCATION.json`.
- The review packet binds only ten aggregates; raw results, remediation results, seeds, commands, traces and state hashes are bound only by the later manifest.

Required result:

- Prevent simulation/finalization code from authoring or overwriting all independent-review provenance artifacts, including invocation evidence.
- Make the external review step create invocation evidence through a separate boundary.
- Pre-review packet must bind a deterministic inventory/Merkle-style root of all review-relevant raw evidence, including scenario results, seeds, commands, traces and state hashes.
- Verification must fail on substitution, mutation, missing raw files, unexpected files or review artifacts authored by the simulation stage.

### R5 — Documentation drift

Open: `AUDIT-19` plus stale stage wording.

- `PLAN-CHANGELOG.md` says directive ledger Revision 8 while the bound ledger is Revision 9.
- The stage-1 `SIMULATION-REPORT.md` says “pending independent Astra review.” A frozen stage-1 report may identify itself as pre-review, but final handoff/readiness must not imply Astra actually reviewed it unless the configured invocation exists.

Required result: generate stage-accurate wording from explicit metadata; never rewrite sealed historical bundles. Correct source templates/current planning records only where authorized, and emit corrections in a fresh run.

### R6 — Configured independent review gate

Open: `AUDIT-10`.

The current run used a disclosed Kimi substitute and correctly remains `ready: false`. After R1–R5 pass, create a fresh, non-existing run root and invoke exactly the configured `codex_subagent/gpt-6-astra`, effort `high`, review gate through the authorized review boundary. Do not alias, substitute or self-author the verdict. If Astra is unavailable or returns `REVISE`, preserve that result and remain not ready.

## Preservation and scope constraints

- Never modify or reseal any directory already under `artifacts/simulations/full-game/`, especially rejected run `full-game-20261101T102226Z-a8e33043` and sealed run `full-game-20261101T164201Z-2647e033`.
- Use a fresh, exclusive run root for new evidence. Seal the manifest last.
- No live Twitch, Extension, OpenAI API, AWS/IVS, browser, server, deployment or publication work.
- Do not claim visual/audio/mobile/demo evidence from headless state tests.
- Preserve deterministic scripted actors, seeded/hash-bound corpora, canonical commands, state diffs and service-independent game authority.
- Gameplay remains gated except for an explicitly compiler-confirmed authorized deterministic simulation. Never infer permission from configuration or this handoff.

## Likely implementation surface

Confirm through codebase-memory before assigning ownership. Expected files include:

- `coordination/evidence_pipeline.py`
- `coordination/run_full_game_simulation.py`
- `coordination/full_game_simulator.py` and/or `coordination/scenario_inputs.py`
- `tests/test_full_game_simulation.py`
- Targeted planning/status/audit templates required for fresh evidence

Do not edit a file until it is included in a fresh context-contract `--owned-path` binding.

## Acceptance checks

The remediation is complete only when all are observed:

1. Missing/corrupt evidence makes every affected readiness predicate false; no fail-open defaults remain.
2. Expected counts and revision are derived from frozen bound contracts/catalogs.
3. Positive isolated finalization, valid sealed `REVISE`, tampering, missing evidence, substituted reviewer and provenance-authorship cases have distinct tests.
4. Every `AUDIT-*` finding and required invariant has machine-readable evidence/closure or remains explicitly open; readiness cannot ignore open S0/S1 findings.
5. Review packet directly binds the complete raw review surface before external review.
6. Existing sealed runs remain byte-identical.
7. Allowed targeted static/context/evidence tests pass. Do not run prohibited gameplay tests unless a new explicit authorization and compiled gate allow them.
8. A fresh run passes manifest/source/replay verification and truthfully reports observed versus unobserved capabilities.
9. Genuine Astra/high review evidence is externally produced and verified. `READY` is accepted only if all derived gates pass; otherwise preserve `REVISE`/not-ready.
10. Produce a new concise handoff containing fresh run ID, tree/manifest hashes, test commands/results, review conversation ID, remaining gaps and exact next action.

## Expected agent return

At most 250 words plus paths. Report:

- files changed;
- tests/checks run and exact results;
- fresh evidence root and hashes, if authorized and produced;
- findings closed versus still open;
- whether configured Astra gate was genuinely satisfied;
- explicit statement that historical sealed bundles were not modified.

