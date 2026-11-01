# Simulation report handoff — evidence bundle `full-game-20261101T164201Z-2647e033`

Prepared: 2026-11-01
Audience: a receiving agent or reviewer that has not seen this work. This document is self-contained.
Bundle root: `artifacts/simulations/full-game/full-game-20261101T164201Z-2647e033/`

## 0. Read this first

This bundle is a **sealed, independently reviewed deterministic simulation** of the TwitchCon Odyssey game plan (Revision 5), produced by a two-stage pipeline:

- **Stage 1 (`--stage simulate`)** froze the scenario matrix and corpus, executed 46 scenarios, emitted raw evidence, and wrote a review packet. It is forbidden from writing a review verdict, from writing `DEVELOPMENT-READINESS.json`, and from sealing the manifest.
- **Stage 2 (`--stage finalize`)** ran only after an external review artifact existed, verified its bindings, computed readiness from observed gate predicates, and sealed `RUN-MANIFEST.json` **last**.

**Status you must not overstate:**

| Field | Value |
| --- | --- |
| Independent review verdict | `REVISE` |
| Reviewer actually served | `ollama-cloud/kimi-k3`, effort `high` (disclosed substitute) |
| Configured gate | `codex_subagent/gpt-6-astra`, `high` — **unavailable** in the environment |
| `configured_gate_satisfied` | `false` |
| `ready` | **`false`** |
| `submission_ready` | **`false`** |
| Scenarios | 46 executed / 46 passed / 0 failed / 0 blocked |
| Invariants | 18 / 18 passed |

No artifact claims GPT-6-Astra reviewed this bundle. There is no alias, no router, and no model-policy change.

## 1. Identity and integrity

| Property | Value |
| --- | --- |
| Run ID | `full-game-20261101T164201Z-2647e033` |
| Profile SHA-256 (first 8 = `2647e033`) | `2647e033fca26875916446d2b9d45419fcd1d3dcde09b5cb03a5f576ff9bc4a6` (`docs/planning/S1-SIMULATION-PROFILE.md`) |
| Candidate plan | Revision 5 — `docs/planning/GAMEPLAN-v2.md` `d7da3bc1d390a7f1ec37412c9b8d9c455eb54f43e9eefc26b95dc76b43df6752`, `docs/planning/gameplan-v2.json` `6e20481549e188472a8369041760495a15d033a97fa3aa8898bf7d04f3b13147` |
| Files | 164 (163 sealed artifacts + `RUN-MANIFEST.json`) |
| Tree SHA-256 | `9c6670af87c8ca711da67b7d3122dde5ba9b25cec5c3894732a4b4792dd3c830` |
| Manifest | `RUN-MANIFEST.json` `e498656c53cd9d4c871849da224cfa249215bfb74e046b49fa5b3c73db76b0eb`, `status: completed_not_ready` |
| Manifest verification | 163/163 recorded hashes match the current bytes |
| Source bindings | 30/30 match the working tree at audit time |

## 2. File map — what lives where

### 2.1 Governance and framing (root markdown)

| File | SHA-256 | What lives there |
| --- | --- | --- |
| `README.md` | `66adf8cc…e9bf6` | Entry point; run id, verdict, `ready`/`submission_ready`, index of key artifacts. |
| `SIMULATION-REPORT.md` | `0053fffb…021b` | Human-readable narrative report: coverage, scenario/invariant summary, mapping of `AUDIT-01..09` to remediations, corpus and golden-replay digests. **Start here for prose.** |
| `AUTHORIZATION.md` | `84fa8d90…847622` | Authorization token and provenance (directive ledger + `DECISIONS.md`), plan revision hashes, explicit scope exclusions. |
| `ASSUMPTIONS-AND-GAPS.md` | `618f1b8a…31c827` | Pre-tick-0 classification: deterministic clarifications, delegated decisions (`DECISION-01..04`), capabilities left `not_observed`. |
| `HUMAN-DECISIONS.md` | `66e15804…7c3dffb` | Delegated product decisions with `DELEGATED_ACCEPTED` / `PROVISIONAL` status and the still-open `live_submission_external_capture` gate. |
| `PLAN-CHANGELOG.md` | `a1f59612…f9644c9f` | What changed from Revision 4 to Revision 5, with rationale and bound hashes. |

### 2.2 Frozen inputs (must predate tick 0)

| File | SHA-256 | What lives there |
| --- | --- | --- |
| `SCENARIO-MATRIX.json` | `cd71e8651972e175d7b50bd255ecada4128f26508988617cb0bfbd84de4541eb` | 46 frozen contracts: id, category, seed, initial lane/roster, `scheduled_commands` (tick, sequence, provenance), `features_exercised`, `invariants_tested`, concrete `expected_oracle`, `contract_hash`. The single most important file. |
| `CORPUS-MANIFEST.json` | `06641bf1f15b572f5ecd7912eddbd8e3e52ba5548b9836fb335bc14784558225` | 100 000-message viewer corpus binding: seed 42, generator id/version/source hash, template hash, payload digest `03c2ca9c…2b2e3d`, regeneration recipe, `verified_regeneration_match: true`. |
| `seeds.json` | `9646e880…b568d6a` | Master/corpus seeds and the per-scenario seed map. |
| `SOURCE-BINDINGS.json` | `9fc264c6715986c84f8f33dc054af6e90dd7cb30072f6595e9be036213675106` | 30 pinned inputs (13 authoritative planning docs, 17 codebase sources) with size and SHA-256, split by role. |

### 2.3 Execution evidence (the raw material)

| Path | Count | What lives there |
| --- | --- | --- |
| `commands/<SCENARIO-ID>.json` | 46 files, 200 KB | Canonical command envelopes actually submitted: `command_id`, `kind`, `logical_tick`, `sequence`, `actor_id`, `provenance` (`human`/`bot`/`fixture`/`operator`), resulting `status`, `valid_envelope`, per-command `state_hash`. |
| `traces/<SCENARIO-ID>.jsonl` | 46 files, 340 KB | One JSON object per line: `event_kind`, `tick`, trigger, and a `state_diff` delta with `base_hash` → `operations` → `result_hash`. This is the hash-chained audit trail. |
| `state-hashes/<SCENARIO-ID>.json` | 46 files | Per-scenario `initial_state_hash`, `final_state_hash`, labelled `boundary_hashes` (init, turn starts, resolution/reward starts, terminal), plus the oracle evaluation (`checks`, `failures`, `invariants_verified`). |
| `state-hashes/scenario_hashes.json` | 1 file | Flat map of scenario id → final state hash. |
| `results/SCENARIO-RESULTS.jsonl` | 1 file, 44 KB, 46 lines | One line per scenario: verdict, final tick/turn/phase/status, initial/final hash, `commands_count`, `trace_records_count`, `commands_sha256`, `trace_sha256`, features exercised, invariants passed. **The index into the raw evidence.** |

### 2.4 Derived conclusions (everything here is computed from 2.3, not asserted)

| File | SHA-256 | What lives there |
| --- | --- | --- |
| `FEATURE-INVENTORY.json` | `89cbccdf949a65128db259cc236bb635844bda7207c8e15cc3c0397843320891` | 16 features with stable IDs, source paths, authority owner, simulation method, oracle, coverage state, justifying scenarios, and per-claim `sub_claims` for `FEAT-12/13/15`. |
| `COVERAGE.json` | `055dcd2650d982089d1a8f6b63767d18414fef14dbdf85fe78ac355b47c0699c` | Roll-up: 16 active, 12 fully covered, 3 partially observed (state only), 1 `not_observed` (`FEAT-14`), 0 failed, environment capabilities all `false`. |
| `INVARIANT-RESULTS.json` | `0900b5e88d9614993ef4f616caff70656479afc6e1107b97723d16f5f8abf52f` | 18 invariants with evaluation counts and pass/fail. |
| `REGRESSION-RESULTS.json` | `973f410ec28601a87b348e6e0788291934414e8c9fbd90fda553b0c4d728d359` | 46/46 passed, golden and offline replay hashes, matrix hash, corpus hash. |
| `REMEDIATION-RESULTS.json` | `3806f96bee868277184f0e66fca7b52f04534e1cebb38e946abf5889feb2e26b` | Issue counts, candidate plan hashes, companion static checks. |
| `ISSUES.json` | `d4ebb3d51bdf3ce964754b0b0388bfea272b7812a589cb02c3b1943d0209338a` | Three triaged issues (`ISSUE-SIM-01..03`), severity S2, root cause `plan`, all `closed` with real 64-hex resolution hashes. |
| `CLAIMS-AND-PROVENANCE.json` | `534192972a65d1b9f071aeb31cb79b652095af893718ee9a28e4feccbc4f837e` | Every user-facing claim with `status` (`observed_in_deterministic_state` / `fixture` / `fictional_diegetic_metaphor` / `not_observed`) and basis. |

> Known gap: `ISSUES.json` does **not** carry one entry per `AUDIT-01..09`, and the matrix has no per-`AUDIT-*` regression scenarios. Audit traceability lives in `SIMULATION-REPORT.md` §3, the validators, and the negative tests.

### 2.5 Review provenance (this is what makes the bundle more than self-report)

| File | SHA-256 | What lives there |
| --- | --- | --- |
| `REVIEW-PACKET.md` | `a84e6b5302d8586a386390f38439ecf297794914298386efc8b217b7d24d30fb` | The frozen request: hashes of 10 pre-review artifacts only. Deliberately does **not** bind `DEVELOPMENT-READINESS.json` or `RUN-MANIFEST.json`. |
| `INDEPENDENT-REVIEW.md` | `268dcabeca8beef5b64686150a246f106e74a65c1c70186dea775ba6a5d47ae6` | The reviewer's own text: verdict `REVISE`, identity disclosure, recomputed hashes, per-item `AUDIT-01..09` findings, new findings `F1`–`F4`, limitations. |
| `INDEPENDENT-REVIEW.json` | `2326beff88d677f0764a732a06c127680e041d53b2cee3c68a3acf2e432a2902` | Machine-readable form of the same verdict and findings. |
| `REVIEW-INVOCATION.json` | `c7a082efd88506da7ffa29242c52072149de235f1c2edf9fb1a8023536a05893` | The call record: configured vs. actual reviewer, availability, gate binding, substitution authorization text, subagent conversation id `ses_e68026c21ffepFXZHltDsqDuum`, packet/prompt/output hashes. |
| `MODEL-USAGE.json` | (in manifest) | Two entries: deterministic kernel (no model), and the review with `model: ollama-cloud/kimi-k3`, `configured_model: gpt-6-astra`, `configured_model_available: false`, `configured_gate_satisfied: false`. |

### 2.6 Readiness and seal

| File | SHA-256 | What lives there |
| --- | --- | --- |
| `DEVELOPMENT-READINESS.json` | `073a81b4339ae8d36a148510d8e4e5b668366b89844bfa8a256bf169fcce2582` | `ready: false`, `submission_ready: false`, 13 gates with booleans, `failed_gates: ["independent_review_uses_configured_gate", "review_verdict_is_ready"]`, required work-package order. |
| `RUN-MANIFEST.json` | `e498656c53cd9d4c871849da224cfa249215bfb74e046b49fa5b3c73db76b0eb` | Every artifact path → SHA-256 (163 entries), run metadata, scenario totals, `status: completed_not_ready`. Sealed last. |

## 3. Suggested reading order for a receiving agent

1. `README.md` → `DEVELOPMENT-READINESS.json` (what the status actually is, and why).
2. `SIMULATION-REPORT.md` → `COVERAGE.json` → `FEATURE-INVENTORY.json` (what is claimed).
3. `results/SCENARIO-RESULTS.jsonl` → pick one scenario → `commands/` → `traces/` → `state-hashes/` (what actually happened).
4. `REVIEW-PACKET.md` → `INDEPENDENT-REVIEW.md` → `REVIEW-INVOCATION.json` (who checked it, and how it is bound).
5. `RUN-MANIFEST.json` (integrity of everything above).

## 4. How to verify it yourself (read-only)

```bash
cd <repo-root>

# 1. Manifest integrity: every recorded hash vs actual bytes
python3 -c "import json;from pathlib import Path;from coordination.evidence_pipeline import file_sha256 as h;\
d=Path('artifacts/simulations/full-game/full-game-20261101T164201Z-2647e033');\
m=json.loads((d/'RUN-MANIFEST.json').read_text());\
print(sum(1 for r,x in m['artifact_hashes'].items() if (d/r).is_file() and h(d/r)==x), len(m['artifact_hashes']))"

# 2. Source bindings vs working tree
python3 -c "import json;from pathlib import Path;from coordination.evidence_pipeline import file_sha256 as h;\
d=Path('artifacts/simulations/full-game/full-game-20261101T164201Z-2647e033');\
sb=json.loads((d/'SOURCE-BINDINGS.json').read_text());\
print([r for r,e in sb.items() if not Path(r).is_file() or h(Path(r))!=e['sha256']])"

# 3. Review chain
python3 -c "from coordination.evidence_pipeline import verify_independent_review_artifact as v;\
from pathlib import Path;print(v(Path('artifacts/simulations/full-game/full-game-20261101T164201Z-2647e033')))"

# 4. Replay one scenario from its bound command stream
python3 -c "import json;from pathlib import Path;from coordination.full_game_simulator import replay_command_stream as r;\
d=Path('artifacts/simulations/full-game/full-game-20261101T164201Z-2647e033');\
m={e['scenario_id']:e for e in json.loads((d/'SCENARIO-MATRIX.json').read_text())}['SCEN-E2E-01'];\
c=[x['cmd'] for x in json.loads((d/'commands/SCEN-E2E-01.json').read_text())['commands']];\
print(r(seed=m['seed'],initial_lane=m['initial_lane'],initial_roster=m['initial_roster'],command_log=c,steps_to_run=m['steps_to_run'])['final_state_hash'])"
# expected: 5e7c32e9ec752e2bcf07cacb8345753fda730edfb88e04be4614c31d3f162460
```

Reference digests: golden replay `5e7c32e9…162460` (`SCEN-E2E-01`), offline replay `77bec6e8cb5827c5be55d024a80defba23847f95a7b712b234222f309b09ed00` (`SCEN-OFF-01`), corpus payload `03c2ca9c12e89f7215a7918dbadcfa6ad6a36e78b9d74258033fb4d2626b2e3d`.

## 5. Limits — do not conclude more than this supports

- No live Twitch, Twitch Extension, OpenAI/Codex/AWS/IVS call was made. Latency, sponsorship, route accuracy, accessibility, fairness, security and stage reliability are **not evidenced**.
- `FEAT-14` (browser/mobile readability) is `not_observed`. `FEAT-12/13/15` satisfy only the state-machine claim; the visual overlay, acoustic output and rendered 3-minute video are `not_observed`.
- Bots and fixtures were exercised, but they never created live Hype, affected human quorum, or received settlement — verified empirically, not just declared.
- The review is a **substitute** review. It cannot satisfy the configured `gpt-6-astra` gate, which is why `ready` is false.
- Hashes bind bytes, not truth or authorization.

## 6. Open items (from the review and the audit)

| ID | Severity | Summary |
| --- | --- | --- |
| `AUDIT-10` | S0 | Configured reviewer (`gpt-6-astra`) unavailable; only a disclosed substitute review exists. |
| `AUDIT-11` | S1 | No per-`AUDIT-01..09` regression scenarios in the frozen matrix. |
| `AUDIT-12` | S1 | `ISSUES.json` lacks per-`AUDIT-*` closure records. |
| `AUDIT-13` | S1 | Readiness gates hardcode revision 5 / 46 / 18 and three predicates **fail open**. |
| `AUDIT-14` | S2 | Six additional required invariants are not evaluated. |
| `AUDIT-15` | S2 | `REVIEW-INVOCATION.json` is not protected against simulator authorship. |
| `AUDIT-18` | S2 | Review packet binds only 10 aggregates; raw traces bind only via the final manifest. |
| `AUDIT-16/17/19` | S3 | Prior run's review unverifiable here; matrix has no self-digest freeze receipt; changelog says "Revision 8" vs ledger revision 9. |

## 7. Related documents outside the bundle

- `docs/planning/SIMULATION-EVIDENCE-AUDIT-full-game-20261101T164201Z-2647e033.md` — read-only audit of this bundle (`78429e325de75208b5c9bcfd99e9a28eaa9b021d5bebeaea4fc491236b91c018`), verdict `REVISE`.
- `docs/planning/SIMULATION-EVIDENCE-AUDIT-full-game-20261101T161936Z-2647e033.md` — the earlier blocked-review attempt.
- `docs/planning/SIMULATION-EVIDENCE-AUDIT.md` — pre-change baseline (`adcc2692…2f3a798`), retained unchanged.
- Other same-day runs preserved under `artifacts/simulations/full-game/`: `…102226Z-a8e33043` (rejected baseline, untouched), `…132816Z-2647e033` (prior remediated), `…161936Z-2647e033` (blocked review), `…164026Z-2647e033` (superseded stage-1 bundle).
