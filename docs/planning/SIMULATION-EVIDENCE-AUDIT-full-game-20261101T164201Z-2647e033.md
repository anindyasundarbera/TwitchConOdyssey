# Simulation evidence audit — sealed, substitute-reviewed run

Recorded: 2026-11-01
Audit scope: read-only audit of the sealed run `full-game-20261101T164201Z-2647e033`
Audited root: `artifacts/simulations/full-game/full-game-20261101T164201Z-2647e033/`
Supersedes, for the sealed bundle only: `SIMULATION-EVIDENCE-AUDIT-full-game-20261101T161936Z-2647e033.md` (the blocked-review attempt, retained unchanged as evidence of that attempt) and `SIMULATION-EVIDENCE-AUDIT.md` (`adcc2692…2f3a798`, the pre-change baseline, retained unchanged).
Methodology: identical to the pre-change audit — recompute every digest from bytes; treat the bundle's self-report as a claim to test.

## Executive assessment

This bundle is the first one under the remediation grant that is both **sealed** and **independently reviewed**. The deterministic evidence is unchanged in substance from the earlier rerun and survives independent replay. What is new is provenance discipline:

- the review is a **genuine subagent invocation** (`ses_e68026c21ffepFXZHltDsqDuum`) that returned `REVISE`;
- it is recorded as a **disclosed substitute** (`ollama-cloud/kimi-k3`, `high`) for the configured gate (`codex_subagent/gpt-6-astra`, `high`, unavailable);
- `MODEL-USAGE.json` records `reviewer_model` and `configured_model` separately, with `configured_model_available: false` and `configured_gate_satisfied: false`;
- readiness is therefore computed as `ready: false` / `submission_ready: false`, with `independent_review_uses_configured_gate` and `review_verdict_is_ready` as the two failed gates.

No artifact claims that GPT-6-Astra reviewed this bundle. No alias or router was created.

## 1. Integrity and seal

| Check | Result |
| --- | --- |
| Manifest entries vs actual bytes | 163/163 match, 0 mismatches |
| File count | 164 (163 sealed + `RUN-MANIFEST.json`) |
| Tree SHA-256 | `9c6670af87c8ca711da67b7d3122dde5ba9b25cec5c3894732a4b4792dd3c830` |
| `RUN-MANIFEST.json` | `e498656c53cd9d4c871849da224cfa249215bfb74e046b49fa5b3c73db76b0eb`, sealed last, `status: completed_not_ready` |
| Seal ordering | `REVIEW-PACKET.md` binds 10 pre-review aggregates and neither `DEVELOPMENT-READINESS.json` nor `RUN-MANIFEST.json`; both exist only post-review |
| Source bindings at audit time | 30/30 match the working tree, including `coordination/evidence_pipeline.py` `f364697d…` and `config/directive-policy.json` (revision 9) |
| Preserved rejected run | 116 files, `411de7291dd8db03…` — unchanged |
| Prior remediated run | 164 files, `7b52636fc394a695…` — unchanged |

## 2. Review provenance (the part that changed)

| Field | Value |
| --- | --- |
| Reviewer actually served | `ollama-cloud/kimi-k3`, effort `high`, provider `ollama-cloud` |
| Configured gate | `codex_subagent/gpt-6-astra`, effort `high` — unavailable in this environment |
| Subagent conversation | `ses_e68026c21ffepFXZHltDsqDuum` |
| `REVIEW-PACKET.md` | `a84e6b5302d8586a386390f38439ecf297794914298386efc8b217b7d24d30fb` |
| `INDEPENDENT-REVIEW.md` | `268dcabeca8beef5b64686150a246f106e74a65c1c70186dea775ba6a5d47ae6` |
| `INDEPENDENT-REVIEW.json` | `2326beff88d677f0764a732a06c127680e041d53b2cee3c68a3acf2e432a2902` |
| `REVIEW-INVOCATION.json` | `c7a082efd88506da7ffa29242c52072149de235f1c2edf9fb1a8023536a05893` |
| Verdict | `REVISE` (consistent across `.md`, `.json`, invocation) |
| `DEVELOPMENT-READINESS.json` | `073a81b4339ae8d36a148510d8e4e5b668366b89844bfa8a256bf169fcce2582` — `ready: false`, `submission_ready: false` |

`prompt_sha256` equals the review-packet digest and is labelled `prompt_sha256_basis: review_packet_bytes`; the invocation does not pretend a longer prompt body was hashed.

## 3. Closure table (`AUDIT-01`..`AUDIT-09`)

| Finding | Status | Basis |
| --- | --- | --- |
| `AUDIT-01` genuine independent review | **PARTIAL** | A real, hash-bound subagent review now exists and the simulator still cannot author `INDEPENDENT-REVIEW.md`/`.json`. The *configured* gate is unsatisfied by design (substitute), so the S0 condition "Astra/high READY" is not met. |
| `AUDIT-02` pre-frozen oracles | **CLOSED** | 46 concrete oracles; `contract_hash` recomputation matches; code order + exclusive writes + mtime ordering place the freeze before tick 0. |
| `AUDIT-03` fixture Hype isolation | **CLOSED** | Fixture hazard → live `pool 0` / synthetic `20`; nine bot counters → `0` quorum; fixture-only match settles zero live Hype (three independent probes). |
| `AUDIT-04` fabricated coverage | **CLOSED** | `derive_feature_statuses` reproduces inventory/COVERAGE identically; `FEAT-14` `not_observed`; `FEAT-12/13/15` sub-claims split. |
| `AUDIT-05` placeholder evidence | **CLOSED** | 46/46 substantive command streams and `state_diff` traces; reviewer and this audit both replayed golden and offline scenarios to identical hashes. |
| `AUDIT-06` unsynchronised candidate | **CLOSED** | Revision 5 bound across plan/machine plan/profile/decisions/ledger; static suites pass. |
| `AUDIT-07` premature `ready` | **PARTIAL** | `ready: false` is now correct and `submission_ready` is separate, but the gate set is still hardcoded and partly fail-open (`AUDIT-13`). |
| `AUDIT-08` invalid corpus digest | **CLOSED** | 64-hex payload digest, generator/version/seed/recipe bound, regeneration verified. |
| `AUDIT-09` run-root reuse / seal order | **CLOSED** | Exclusive root, `exist_ok=False`, preserved-run guard, manifest sealed last, packet cannot pre-hash post-review artifacts. `REVIEW-INVOCATION.json` authorship remains unprotected (`AUDIT-15`). |

## 4. Carried and new findings

- **AUDIT-10 (S0, open)** — no configured-gate review. `gpt-6-astra` is unavailable; the bundle records a disclosed substitute and `ready: false`. Blocks: the `READY` acceptance criterion only.
- **AUDIT-11 (S1, open)** — no per-`AUDIT-*` regression scenarios in the frozen matrix; audit properties live in unit tests and validators instead.
- **AUDIT-12 (S1, open)** — `ISSUES.json` still carries only `ISSUE-SIM-01..03`; no per-`AUDIT-01..09` entries with resolution hashes. Independently confirmed by the reviewer (its `F2`).
- **AUDIT-13 (S1, open — aggravated)** — readiness gates hardcode revision 5 / 46 scenarios / 18 invariants, and three predicates (`corpus_hash_valid`, `all_46_traces_substantive`, `feature_coverage_honestly_derived`) default to `True` when their inputs are unavailable, i.e. they **fail open**. Independently found by the reviewer (`F3`) and reproduced in this audit: with `CORPUS-MANIFEST.json` absent from a copied bundle, `compute_development_readiness` still returns `corpus_hash_valid: true`.
- **AUDIT-14 (S2, open)** — the six extra invariants required by the rerun prompt are still not evaluated.
- **AUDIT-15 (S2, open)** — `REVIEW-INVOCATION.json` is writable by the simulator (`_PROTECTED_REVIEW_FILENAMES` covers only the two `INDEPENDENT-REVIEW.*` files).
- **AUDIT-16 (S3, hygiene)** — the prior run's `READY` remains unverifiable here; it names a model absent from the catalog and carries no provider receipt.
- **AUDIT-17 (S3, hygiene)** — `SCENARIO-MATRIX.json` still embeds no self-digest or freeze timestamp; pre-freeze rests on code order and mtimes.
- **AUDIT-18 (S2, new — reviewer `F1`)** — `REVIEW-PACKET.md` binds only 10 aggregate artifacts; `results/SCENARIO-RESULTS.jsonl`, `REMEDIATION-RESULTS.json`, `seeds.json` and the 138 raw command/trace/state-hash files are bound only by the post-review manifest.
- **AUDIT-19 (S3, new — reviewer `F4`)** — `PLAN-CHANGELOG.md` says the ledger is "Revision 8"; the bound ledger is revision 9. Textual staleness only; hashes match.

Reproduction for `AUDIT-13`'s fail-open behaviour:

```bash
python3 -c "import json,shutil,tempfile;from pathlib import Path;from coordination.evidence_pipeline import compute_development_readiness as c;t=Path(tempfile.mkdtemp())/'r';shutil.copytree('artifacts/simulations/full-game/full-game-20261101T164201Z-2647e033',t);(t/'CORPUS-MANIFEST.json').unlink();print(c(t)['gates']['corpus_hash_valid'])"
```

## 5. Comparison with the other same-day runs

| Run | Files | Tree | State |
| --- | --- | --- | --- |
| `…102226Z-a8e33043` | 116 | `411de7291dd8db03…` | preserved rejected baseline, untouched |
| `…132816Z-2647e033` | 164 | `7b52636fc394a695…` | prior remediated, `READY` from an unverifiable Astra claim, untouched |
| `…161936Z-2647e033` | 158 | `0cfc45005e6ed170…` | blocked-review attempt, `REVIEW-BLOCKED.json`, unsealed |
| `…164026Z-2647e033` | 157 | `6c4b87f1dc848858…` | superseded stage-1 bundle (pre-ledger-reconciliation), unsealed |
| `…164201Z-2647e033` | 164 | `9c6670af87c8ca71…` | **this run** — sealed, substitute-reviewed, `ready: false` |

Stage-1 artifacts are byte-identical across `…161936Z`, `…164026Z` and `…164201Z` except `AUTHORIZATION.md`, `SIMULATION-REPORT.md`, `SOURCE-BINDINGS.json` and `REVIEW-PACKET.md`, which embed the run id or the current ledger hash. No gameplay or product code changed.

## 6. Verification performed by this audit

```bash
python3 -m unittest tests.test_full_game_simulation tests.test_gameplan_rules \
  tests.test_context_contract tests.test_city_setting tests.test_deterministic_kernel \
  tests.test_model_router tests.test_plan_rehearsal -v   # 80 tests, OK
python3 -m coordination.context_contract --task simulation_preparation --phase plan --validate-only
```

Independent replays of `SCEN-E2E-01`, `SCEN-AUD-06` and `SCEN-CTRL-03` reproduce stored final and boundary hashes. No run directory was modified; no re-seal occurred; no gameplay, server, browser, harness or network call was made.

## 7. What a human must decide

1. Accept the disclosed substitute review as advisory input, or restore `gpt-6-astra` access and re-run the gate — only the latter can make `ready` true.
2. Decide whether `AUDIT-11`..`AUDIT-14`, `AUDIT-18` are mandatory before development (the reviewer's `REVISE` rests mainly on `F3`, the fail-open readiness gates).
3. Confirm or veto `DECISION-01`..`DECISION-04` (`DELEGATED_ACCEPTED`, `PROVISIONAL`).
4. Keep `live_submission_external_capture` closed; `submission_ready` remains false.

Deterministic simulation is not live-service, latency, accessibility, security or stage-reliability evidence.

VERDICT: REVISE
