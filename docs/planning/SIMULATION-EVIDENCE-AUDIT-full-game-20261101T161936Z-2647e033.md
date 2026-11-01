# Complete-game simulation evidence audit — post-remediation rerun

Recorded: 2026-11-01
Audit scope: read-only audit of the post-remediation simulation run `full-game-20261101T161936Z-2647e033`
Audited root: `artifacts/simulations/full-game/full-game-20261101T161936Z-2647e033/`
Supersedes: [`SIMULATION-EVIDENCE-AUDIT.md`](SIMULATION-EVIDENCE-AUDIT.md) (`adcc2692789d29aae24b35acb522ea494c96748c5a20a04605461dcc52f3a798`, unchanged) **only by explicit reference**; the earlier document remains the pre-change baseline.
Audit methodology: identical to the pre-change audit — recompute every digest from bytes, treat the bundle's self-report as a claim to test, never as evidence.

## Purpose and authority

This document is the durable handoff for the next task. It records what was actually inspected and which claims are supported. It authorizes no gameplay, no live-service call, no product development, no deployment and no publication. No file inside any run directory was modified by this audit, and no run was re-sealed.

The authoritative plan is `docs/planning/GAMEPLAN-v2.md` **revision 5** (`d7da3bc1d390a7f1ec37412c9b8d9c455eb54f43e9eefc26b95dc76b43df6752`, machine plan `6e20481549e188472a8369041760495a15d033a97fa3aa8898bf7d04f3b13147`), confirmed from the records rather than from the rerun prompt. No revision-6 repair was needed or performed during this run, so `PLAN-CHANGELOG.md` correctly carries no new revision.

## Executive assessment

The remediation materially repaired the mechanics of the evidence pipeline. The stage-1 bundle is real: 46 pre-frozen scenario contracts with concrete expected oracles, substantive canonical command streams, hash-chained state-diff traces, boundary hashes, 18 evaluated invariants, a content-addressed 100 000-message corpus, and mechanically derived feature coverage. Independent re-execution reproduced the stored digests exactly. Fixture and bot isolation survives an adversarial probe that is not part of the frozen matrix.

The bundle nevertheless **cannot** support a readiness conclusion, for two independent reasons:

1. **The review gate did not run.** The configured `plan_review` model (`codex_subagent` / `gpt-6-astra` / `high`) does not resolve in the execution environment. The dispatch was rejected before inference. No substitute reviewer was used, no verdict was authored, `--stage finalize` was not run, and the bundle is unsealed. This is recorded in `REVIEW-BLOCKED.json` (`43504ca180428372e10d4239f2e53f843fb2d7a3850ad1578d58fe8ead414be6`).
2. **Several explicit rerun-prompt requirements are not implemented** in the current pipeline: audit-regression scenarios, the added invariants, per-`AUDIT-*` issue closure records, and non-constant readiness gates. These are reported below as new findings rather than silently waived.

Neither defect is a plan defect. Nothing in this audit was "fixed" to make the bundle pass.

## 1. Byte integrity, sealing and immutability

| Item | Expected | Observed |
| --- | --- | --- |
| Run root created exclusively | fail if exists | `create_immutable_run_root` raises `FileExistsError` on reuse and `PermissionError` without the authorization token (probed in a temp dir) |
| `RUN-MANIFEST.json` | sealed last, binds every artifact | **absent** — stage 2 never ran; manifest and seal ordering cannot be verified |
| Artifact set | as specified in §10 | 157 stage-1 files; `RUN-MANIFEST.json`, `DEVELOPMENT-READINESS.json`, `MODEL-USAGE.json`, `INDEPENDENT-REVIEW.*` absent as required pre-review, and still absent because finalization is blocked |
| File count / tree digest at audit time | — | 158 files; tree SHA-256 `0cfc45005e6ed170e49b34cc91e5622bd2e66afe4b646d4138e078e0fd1625bf` (157 stage-1 files + `REVIEW-BLOCKED.json`) |
| Byte hash of every stage-1 artifact | recomputable | recomputed; see the hash table in §6 |
| Preserved rejected run `full-game-20261101T102226Z-a8e33043` | untouched | 116 files, tree `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d` before **and** after the run |
| Prior remediated run `full-game-20261101T132816Z-2647e033` | untouched | 164 files, tree `7b52636fc394a69553ecc615bfd4e623a8cc873d924e9b621cda948b79768e8f` before **and** after the run |

Reproduction:

```bash
python3 -c "from pathlib import Path; from coordination.evidence_pipeline import compute_tree_sha256 as t; \
[print(r, len([p for p in (Path('artifacts/simulations/full-game')/r).rglob('*') if p.is_file()]), \
t(Path('artifacts/simulations/full-game')/r)) for r in \
['full-game-20261101T102226Z-a8e33043','full-game-20261101T132816Z-2647e033','full-game-20261101T161936Z-2647e033']]"
```

## 2. Source binding at audit time

`SOURCE-BINDINGS.json` (`c41a065fc591ee9c912eea3a008af2344258102784338704b940650662568cba`) binds 30 entries (13 authoritative planning inputs, 17 codebase sources). **All 30 recomputed hashes still match the current working tree — zero drift**, including `config/directive-policy.json` (`c6bd7bd1…d4852`), `docs/planning/STATUS.md` (`7d8b760e…b9683`), `GAMEPLAN-v2.md`, `gameplan-v2.json`, `DECISIONS.md`, `S1-SIMULATION-PROFILE.md`, `evidence_pipeline.py`, `full_game_simulator.py`, `run_full_game_simulation.py`, `scenario_inputs.py` and `server/engine.py`.

Two entries differ from the *previous* run's bindings — `config/directive-policy.json` (`969349cf…` → `c6bd7bd1…`) and `docs/planning/STATUS.md` (`7d57f43c…` → `7d8b760e…`) — because the ledger and status were updated after run `…132816Z` to record that run. That drift is legitimate and is the only source-level difference.

## 3. Oracle pre-freeze and concreteness

`SCENARIO-MATRIX.json` (`cd71e8651972e175d7b50bd255ecada4128f26508988617cb0bfbd84de4541eb`) is a 46-entry list. Each entry carries `scenario_id`, `category`, `seed`, `initial_lane`, `initial_roster`, `scheduled_commands` (with `submit_at_tick`, `logical_tick`, sequence and provenance), `features_exercised`, `invariants_tested`, `expected_oracle` and a canonical `contract_hash`. Oracles are concrete literals, not category strings — e.g. `SCEN-E2E-01` declares `expected_final_tick: 1759`, `expected_final_status: delivered`, `expected_settlement.per_voter_rational: "30/7"`, `expected_pool: 60`, `expected_collisions_total: 0`.

Evidence that the matrix predates tick 0:

- Orchestration order writes `seeds.json`, then `CORPUS-MANIFEST.json`, then `freeze_scenario_matrix(...)`, and only then executes any scenario.
- Modification times at nanosecond resolution: corpus manifest `21:49:47.865`, matrix `21:49:47.878`, first command stream `21:49:47.924`, first trace `21:49:47.925`.
- Every `state-hashes/<id>.json` binds the matrix `contract_hash`, and `verify_scenario_trace_integrity` rejects a mismatch, so results demonstrably consume the frozen matrix rather than a reconstructed expectation.

Residual weakness (see `AUDIT-17`): the matrix carries no embedded freeze timestamp or self-digest receipt, so pre-freeze is evidenced by code order plus file mtimes, not by a signed record.

## 4. Substantive evidence and independent replay

All 46 scenarios emitted non-placeholder artifacts: `commands/<id>.json` contains real canonical command envelopes with `command_id`, `logical_tick`, `sequence`, `provenance` and per-command status/state hash; `traces/<id>.jsonl` contains hash-chained `state_diff` records with `base_hash`/`result_hash`/operations; `state-hashes/<id>.json` binds initial hash, boundary hashes and the oracle evaluation. `results/SCENARIO-RESULTS.jsonl` has 46 records.

Five scenarios were sampled (`SCEN-E2E-01` golden, `SCEN-AUD-06` adversarial audience, `SCEN-CTRL-03` steering lockout, `SCEN-E2E-05` fixture hazard, `SCEN-PRS-03` credibility). Three were **re-executed independently by this audit** from the frozen contract plus the stored command stream:

| Scenario | Stored final hash | Re-executed | Independent replay | Boundaries match |
| --- | --- | --- | --- | --- |
| `SCEN-E2E-01` | `5e7c32e9…162460` | identical | identical | yes |
| `SCEN-AUD-06` | `1882f471…c101128` | identical | identical | yes |
| `SCEN-CTRL-03` | `b9c08c6e…e1812fa2` | identical | identical | yes |

Reproduction:

```bash
python3 -c "import json,sys; from pathlib import Path; \
from coordination.full_game_simulator import execute_frozen_scenario, replay_command_stream; \
run=Path('artifacts/simulations/full-game/full-game-20261101T161936Z-2647e033'); \
m={e['scenario_id']:e for e in json.loads((run/'SCENARIO-MATRIX.json').read_text())}['SCEN-E2E-01']; \
b=execute_frozen_scenario(m); \
c=[x['cmd'] for x in json.loads((run/'commands/SCEN-E2E-01.json').read_text())['commands']]; \
r=replay_command_stream(seed=m['seed'],initial_lane=m['initial_lane'],initial_roster=m['initial_roster'],command_log=c,steps_to_run=m['steps_to_run']); \
print(b['final_state_hash'], r['final_state_hash'])"
```

## 5. Coverage, claims and fixture isolation

- `derive_feature_statuses` re-run over `results/SCENARIO-RESULTS.jsonl` reproduced `FEATURE-INVENTORY.json` (`89cbccdf…20891`) and `COVERAGE.json` (`055dcd26…0699c`) **byte-identically**: 16 active features, 12 fully covered, 3 `partially_observed_state_only` (`FEAT-12`, `FEAT-13`, `FEAT-15`), 1 `not_observed` (`FEAT-14-READABILITY-AND-HUD`), 0 `failed`, 0 `blocked`.
- The partial features expose per-claim splits with truthful `not_observed` sub-claims: `visual_interpolation_overlay_capture`, `acoustic_output_and_voiceover_intelligibility`, `rendered_three_minute_video_and_live_session`. A deterministic state/command result satisfies only the state-machine claim. `AUDIT-04` does not recur.
- `CLAIMS-AND-PROVENANCE.json` (`53419297…f837e`) labels the Twitch participation claim `fixture` (100 000-message seeded corpus, zero live connection), the booth moments `fictional_diegetic_metaphor` (non-sponsor), and the HUD/acoustic/video claims `not_observed`. No claim asserts measured latency, sponsorship, accessibility or live-service behaviour.
- Fixture/bot isolation was tested empirically, outside the frozen matrix, with a fresh `FullGameSimulator`:
  - fixture-provenance hazard → `pool = 0`, `synthetic_fixture_pool = 20`;
  - nine bot `viewer.counter` votes against a human hazard → `counter_votes_count = 0`, hazard not countered, warning stays active;
  - fixture-only match driven to terminal delivery at tick 1767 → live `pool = 0`, synthetic `20`, so the settlement would be zero live Hype.

Reproduction:

```bash
python3 -c "from coordination.canonical_commands import make_command; from coordination.full_game_simulator import FullGameSimulator; \
s=FullGameSimulator(seed=42,initial_lane=1,initial_roster=[f'user_{i}' for i in range(10)]); \
s.submit_command(make_command(actor_id='fixture_actor',kind='hazard.propose',logical_tick=10,sequence=1,payload={'hazard_id':'fx','lane':1},provenance='fixture')); \
[s.step() for _ in range(320)]; st=s.get_canonical_state(); print(st['bounty']['pool'], st['bounty']['synthetic_fixture_pool'])"
```

## 6. Hash table (artifacts cited above)

| Artifact | SHA-256 |
| --- | --- |
| `REVIEW-PACKET.md` | `215092df0ee68dfdd2a3c4eef095c7313c0274a7300812797033af644e3919c5` |
| `SCENARIO-MATRIX.json` | `cd71e8651972e175d7b50bd255ecada4128f26508988617cb0bfbd84de4541eb` |
| `CORPUS-MANIFEST.json` | `06641bf1f15b572f5ecd7912eddbd8e3e52ba5548b9836fb335bc14784558225` |
| `FEATURE-INVENTORY.json` | `89cbccdf949a65128db259cc236bb635844bda7207c8e15cc3c0397843320891` |
| `COVERAGE.json` | `055dcd2650d982089d1a8f6b63767d18414fef14dbdf85fe78ac355b47c0699c` |
| `INVARIANT-RESULTS.json` | `0900b5e88d9614993ef4f616caff70656479afc6e1107b97723d16f5f8abf52f` |
| `ISSUES.json` | `d4ebb3d51bdf3ce964754b0b0388bfea272b7812a589cb02c3b1943d0209338a` |
| `REGRESSION-RESULTS.json` | `973f410ec28601a87b348e6e0788291934414e8c9fbd90fda553b0c4d728d359` |
| `CLAIMS-AND-PROVENANCE.json` | `534192972a65d1b9f071aeb31cb79b652095af893718ee9a28e4feccbc4f837e` |
| `SIMULATION-REPORT.md` | `8d0cd6350cff4c58ae1387c0fa7dd305a3f6a902c063f126dcf8a83fe81bd56d` |
| `SOURCE-BINDINGS.json` | `c41a065fc591ee9c912eea3a008af2344258102784338704b940650662568cba` |
| `REVIEW-BLOCKED.json` | `43504ca180428372e10d4239f2e53f843fb2d7a3850ad1578d58fe8ead414be6` |

The corpus payload digest is `03c2ca9c12e89f7215a7918dbadcfa6ad6a36e78b9d74258033fb4d2626b2e3d`; regenerating `generate_viewer_corpus(seed=42, count=100000)` and `build_corpus_manifest` reproduced the stored manifest exactly (`verified_regeneration_match: true`).

## 7. Closure table for the nine pre-change findings

| Finding | Status | Evidence |
| --- | --- | --- |
| `AUDIT-01` genuine independent review | **OPEN (blocked)** | Simulator cannot author `INDEPENDENT-REVIEW.md`/`.json` (guard probed), but no review exists for this run because the configured model is unavailable; `REVIEW-BLOCKED.json`. Prior run's review is not re-verifiable here (`AUDIT-16`). |
| `AUDIT-02` pre-frozen concrete oracles | **CLOSED** | 46 concrete oracles, frozen before tick 0; `contract_hash` binding enforced by `verify_scenario_trace_integrity`; §3 above. |
| `AUDIT-03` fixture Hype isolation | **CLOSED** | Empirical probe: fixture hazard → live `pool 0`, synthetic `20`; bot votes → `0` quorum; fixture-only delivery settles zero live Hype. |
| `AUDIT-04` fabricated coverage | **CLOSED** | `derive_feature_statuses` reproduces inventory/coverage byte-identically; `FEAT-14` `not_observed`; `FEAT-12/13/15` sub-claims split. |
| `AUDIT-05` placeholder commands/traces | **CLOSED** | 46/46 substantive command streams and `state_diff` traces; three independent re-executions reproduce final and boundary hashes. |
| `AUDIT-06` unsynchronised candidate | **CLOSED** | Revision 5 synchronized across plan, machine plan, profile, decisions, ledger rev 8; static rule/context/city tests pass (80 tests). |
| `AUDIT-07` premature `ready` | **PARTIAL** | Readiness is no longer written by stage 1 and `submission_ready` is separated, but the gates remain hardcoded counts (`AUDIT-13`) and no readiness was computed for this run. |
| `AUDIT-08` invalid corpus digest | **CLOSED** | Manifest binds a real 64-hex payload digest, generator source hash, version, seed, count and a verified regeneration recipe. |
| `AUDIT-09` run-root reuse / seal order | **PARTIAL** | Exclusive root creation and preserved-run immutability verified; but the manifest was never sealed (blocked), and `REVIEW-INVOCATION.json` is not protected against simulator authorship (`AUDIT-15`). |

## 8. New findings

### AUDIT-10 — No independent review exists for this run; the bundle is unsealed

Severity: **S0 — blocks review and development**

Expected: one genuine `plan_review` (`gpt-6-astra` / `high`) verdict bound to `REVIEW-PACKET.md`, then a manifest sealed last.
Observed: dispatch rejected before inference — `Model "codex_subagent/gpt-6-astra" is not available`; the model is absent from the 75-model catalog across `ollama-cloud`, `anthropic`, `google`, `opencode`. No retry, no substitution, no verdict, no `DEVELOPMENT-READINESS.json`, no `RUN-MANIFEST.json`.
Evidence: `REVIEW-BLOCKED.json` `43504ca1…14be6`; `REVIEW-PACKET.md` `215092df…19c5`.
Reproduction: `python3 -c "from coordination.model_router import choose_model; print(choose_model('plan_review'))"` then dispatch that model through the configured agent boundary.
Root cause: `external_dependency` (reviewer availability), confidence high; alternatives: environment misconfiguration vs. model retirement.
Blocks: review gate, development readiness. Does **not** block the deterministic evidence itself.

### AUDIT-11 — No audit-regression scenarios (one per finding) exist

Severity: **S1 — blocks review**

Expected (rerun prompt §7): one scenario per finding `AUDIT-01`..`AUDIT-09`.
Observed: the 46 scenarios fall into `nominal_e2e`, `control_and_safety`, `phase_and_clock`, `audience_scale`, `incentive_attacks`, `model_failures`, `offline_and_failover`, `hotfix_and_booth`, `presentation_and_audio`. No scenario exercises review authorship, oracle pre-freeze, fixture Hype, fabricated coverage, placeholder traces, candidate synchronisation, premature readiness, corpus digest or run-root reuse. Several of those properties are covered only by unit tests outside the frozen matrix.
Evidence: `SCENARIO-MATRIX.json` `cd71e865…541eb`.
Reproduction: `python3 -c "import json;print(sorted({e['category'] for e in json.load(open('artifacts/simulations/full-game/full-game-20261101T161936Z-2647e033/SCENARIO-MATRIX.json'))}))"`
Root cause: `harness`, confidence high.
Blocks: review (claimed audit-regression coverage is not evidenced by scenario results).

### AUDIT-12 — `ISSUES.json` carries no per-`AUDIT-*` closure records

Severity: **S1 — blocks development**

Expected (rerun prompt §9): one entry per `AUDIT-01`..`AUDIT-09` with `status`, a real 64-hex `resolution_hash`, and the remediation plus regression evidence.
Observed: three entries only (`ISSUE-SIM-01..03`), all `closed`, all bound to the same `GAMEPLAN-v2.md` hash. The nine audit findings appear only as prose in `SIMULATION-REPORT.md` §3, with no machine-readable status or resolution hash.
Evidence: `ISSUES.json` `d4ebb3d5…9338a`.
Reproduction: `python3 -c "import json;print([(i['issue_id'],i['status']) for i in json.load(open('artifacts/simulations/full-game/full-game-20261101T161936Z-2647e033/ISSUES.json'))])"`
Root cause: `harness`, confidence high.
Blocks: development (the closure loop is asserted, not recorded).

### AUDIT-13 — Readiness gates are still hardcoded constants

Severity: **S1 — blocks development**

Expected (rerun prompt §6): gates derived from the frozen matrix, the frozen invariant set and the bound candidate plan, with a negative test proving a revision-6 candidate and a 47-scenario matrix cannot silently pass **or silently fail for the wrong reason**.
Observed: `compute_development_readiness` still hardcodes `candidate_plan_revision == 5`, `len(invs) == 18`, `scenarios_executed == 46`, `scenarios_passed == 46`, and `all_traces_substantive` returns `False` whenever `len(matrix) != 46`. A 47-scenario matrix would therefore be reported as "traces not substantive" — a silent failure with the wrong reason. No revision-6 / 47-scenario test exists; `tests/test_full_game_simulation.py` only asserts `candidate_plan_revision == 5` and per-gate falsehoods.
Evidence: `coordination/evidence_pipeline.py:812-830, 884-905`; `tests/test_full_game_simulation.py:366-470, 562`.
Reproduction: `python3 -m unittest tests.test_full_game_simulation.FullGameSimulationTests.test_negative_readiness_is_false_when_any_gate_fails -v`
Root cause: `harness`, confidence high.
Blocks: development (readiness would be pinned to one scenario count rather than the frozen matrix).

### AUDIT-14 — Required additional invariants are absent

Severity: **S2 — blocks review**

Expected (rerun prompt §8): the 18 existing invariants plus review-artifact authorship, run-root non-reuse/re-seal, cited-artifact hash existence, seal-time source-byte match, coverage-as-a-function-of-evidence, and `ready ⇒ submission_ready` separation.
Observed: `INVARIANT-RESULTS.json` contains exactly the original 18; none of the six required additions exists as an evaluated invariant (run-root exclusivity exists only as a unit test; the `ready`/`submission_ready` split exists only as a code field).
Evidence: `INVARIANT-RESULTS.json` `0900b5e8…bf52f`.
Reproduction: `python3 -c "import json;print(len(json.load(open('artifacts/simulations/full-game/full-game-20261101T161936Z-2647e033/INVARIANT-RESULTS.json'))))"`
Root cause: `harness`, confidence high.
Blocks: review (invariant set does not cover the properties the run claims).

### AUDIT-15 — `REVIEW-INVOCATION.json` is not protected against simulator authorship

Severity: **S2 — blocks review**

Expected: no review artifact can be authored by the simulator.
Observed: `_PROTECTED_REVIEW_FILENAMES` contains only `INDEPENDENT-REVIEW.md` and `INDEPENDENT-REVIEW.json`. A direct probe shows `write_exclusive_text(..., "REVIEW-INVOCATION.json")` succeeds while the other two raise `PermissionError`. Because the invocation record supplies `packet_hash`, `prompt_sha256`, `subagent_conversation_id` and `evidence_origin`, leaving it writable weakens the anti-forgery boundary.
Evidence: `coordination/evidence_pipeline.py:25-28, 133-150`; probe output.
Reproduction: `python3 -c "import tempfile;from pathlib import Path;from coordination.evidence_pipeline import write_exclusive_text;write_exclusive_text(Path(tempfile.mkdtemp())/'REVIEW-INVOCATION.json','x');print('writable')"`
Root cause: `implementation`, confidence high.
Blocks: review (forgery surface), does not invalidate any existing evidence.

### AUDIT-16 — Prior run's review is not independently re-verifiable in this environment

Severity: **S3 — hygiene / provenance**

Expected: a genuine review can be evidenced by more than a conversation identifier.
Observed: `full-game-20261101T132816Z-2647e033` records `evidence_origin: independent_subagent_review`, model `gpt-6-astra`, and conversation `9714e19d-0457-4175-bf93-197a9a4c4fd5`. That model does not resolve in the current environment, and the invocation record carries no provider- or tool-level receipt (no dispatch record, no model-returned token). The review text is substantive and internally consistent, so this is reported as unverifiable provenance, not as demonstrated fabrication.
Evidence: `full-game-20261101T132816Z-2647e033/REVIEW-INVOCATION.json`, `INDEPENDENT-REVIEW.md`.
Reproduction: list available models, then attempt dispatch of `codex_subagent/gpt-6-astra`.
Root cause: `evidence`, confidence medium.
Blocks: hygiene only.

### AUDIT-17 — Pre-freeze ordering lacks an embedded receipt

Severity: **S3 — hygiene**

Expected: the frozen matrix proves its own freeze point.
Observed: ordering is evidenced by orchestration order and nanosecond mtimes only; `SCENARIO-MATRIX.json` is a bare list with no `frozen_at`, no self-digest and no run-id binding.
Evidence: `SCENARIO-MATRIX.json`; artifact mtimes `21:49:47.865` → `.878` → `.924`.
Reproduction: `stat -c '%y %n' artifacts/simulations/full-game/full-game-20261101T161936Z-2647e033/{CORPUS-MANIFEST.json,SCENARIO-MATRIX.json,commands/SCEN-E2E-01.json}`
Root cause: `evidence`, confidence high.
Blocks: hygiene only.

## 9. Comparison with the two prior runs

Bytes are identical to `full-game-20261101T132816Z-2647e033` for 153 of 157 stage-1 files. Every difference is explained:

| Path | Reason for difference |
| --- | --- |
| `AUTHORIZATION.md`, `SIMULATION-REPORT.md` | embed the new run id (`…161936Z…`) |
| `SOURCE-BINDINGS.json` | `config/directive-policy.json` and `docs/planning/STATUS.md` legitimately changed after the previous run to record it |
| `REVIEW-PACKET.md` | binds the new `SOURCE-BINDINGS.json` and report hashes |

The previous run additionally contains seven post-review artifacts (`INDEPENDENT-REVIEW.md`, `INDEPENDENT-REVIEW.json`, `REVIEW-INVOCATION.json`, `DEVELOPMENT-READINESS.json`, `MODEL-USAGE.json`, `README.md`, `RUN-MANIFEST.json`) that this run cannot produce while the review gate is blocked.

`full-game-20261101T102226Z-a8e33043` is untouched: 116 files, tree `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d`, manifest `bf34da0e…1904cf6`, before and after.

## 10. Verification runs performed by this audit

```bash
python3 -m unittest tests.test_full_game_simulation tests.test_gameplan_rules \
  tests.test_context_contract tests.test_city_setting tests.test_deterministic_kernel \
  tests.test_model_router tests.test_plan_rehearsal -v
# Ran 80 tests — OK
```

Read-only: no gameplay, no server, no replay binary, no browser, no harness, no network, no run-directory writes other than the append-only `REVIEW-BLOCKED.json` recorded during the blocked review stage.

## 11. What a human must decide before development

1. **Reviewer availability or authorization.** Restore access to `plan_review` → `gpt-6-astra` / `high`, or explicitly authorize a named substitute reviewer and accept in writing that the substitute is not the configured gate. Until then `ready` must remain false.
2. **Scope decision on `AUDIT-11`..`AUDIT-14`.** Decide whether the audit-regression scenarios, the six additional invariants, per-`AUDIT-*` issue records and matrix-derived readiness gates are mandatory before any bundle is accepted, or explicitly waive them.
3. **Confirm the delegated decisions.** `DECISION-01`..`DECISION-04` remain `DELEGATED_ACCEPTED` / `PROVISIONAL` with requester veto at freeze; confirm or veto before development.
4. **Keep the live gate closed.** `live_submission_external_capture` remains unresolved and outside every readiness computation; `submission_ready` stays false.

Deterministic simulation is not live-service, latency, accessibility, security or stage-reliability evidence.

VERDICT: REJECT READY
