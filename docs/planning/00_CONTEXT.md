# 00_CONTEXT — Checkpoint Binding, Accepted Remediation Set & Determinism Surface Inventory

## 0. Authorization Record

```
AUTHORIZATION: rerun + decision delegation
Granted by: requester (direct instruction)
Granted at: 2026-11-01T17:36:28+05:30
Scope: one or more fresh simulation runs under new, non-existing run roots;
       and resolution of D-06, D-07, D-08, booth placement and other blocking
       product choices by recorded decision.
Explicitly excluded: modification of the rejected run; product development;
       gameplay execution beyond the authorized simulation; publication.
Supersedes: the checkpoint's "do not rerun without new explicit authorization" clause.
```

- **Versioned Directive Ledger Entry:** Recorded in [`config/directive-policy.json`](../../config/directive-policy.json) under directive ID `remediation_rerun_and_decision_delegation` (topic: `remediation_authorization`, status: `active`).
- **Written Decision Records:** Recorded in [`docs/planning/DECISIONS.md`](DECISIONS.md) (`DECISION-01` through `DECISION-04`, covering `D-06`, `D-07`, `D-08`, and `D-09` / `ISSUE-SIM-01..03`).

---

## 1. Checkpoint Binding

- **Repository Root:** `/home/anindyasundar-bera/Projects/hackathon/TwitchConOdyssey` (verified current working directory).
- **Authoritative Audit Document Path:** `docs/planning/SIMULATION-EVIDENCE-AUDIT.md`
- **Recorded Date (verbatim):** `Recorded: 2026-11-01`
- **Current Verdict (verbatim):** `Current verdict: **REJECT READY; evidence pipeline requires remediation before development**`
- **Audit Document Git Blob Hash (`git hash-object`):** `7e51ed746e19fd21dc9c4333e7187c1165e5d9fc`
- **Audit Document SHA-256 Digest:** `adcc2692789d29aae24b35acb522ea494c96748c5a20a04605461dcc52f3a798`
- **Git Repository & `HEAD` State:** Branch `master` has no commits yet (`git rev-parse HEAD` reports unborn `HEAD` with staged/untracked working tree; recorded in `EVIDENCE.md:7`). Exact file SHA-256 digests are bound below in §4.
- **Preserved Rejected Evidence Directory (Read-Only Baseline):**
  - Path: `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/`
  - File Count: `116` files (`115` audited artifacts + `RUN-MANIFEST.json`)
  - `RUN-MANIFEST.json` SHA-256: `bf34da0ef4764dfd86857aafa3ea9f864cfb98a34f7dadf0af7cad07f1904cf6`
  - Aggregate Sorted Tree SHA-256 (`<rel_path>:<sha256>\n`): `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d`
  - **Non-Modification Mandate:** No task in this plan may modify, rewrite, move, clean, or delete any file under `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/`.
- **Checkpoint Scope Limits Carried Forward Unchanged:**
  - Read-only review of simulation run `full-game-20261101T102226Z-a8e33043`.
  - Current authoritative game plan at baseline is `docs/planning/GAMEPLAN-v2.md` revision 4 (`a6967a24601f259be027ed7fbebed5ad6e0784d4a7f7b7f6c0a2c3967e47e6ed`); revision 5 was proposed in `PLAN-CHANGELOG.md` but not yet synchronized into authoritative plan/context/ledger records.
  - Perform a bounded **simulation evidence-pipeline remediation**, not product development, live-service calls, deployment, or publication.

---

## 2. Accepted Remediation Set (`AUDIT-01` .. `AUDIT-09`)

| ID | Severity | Subject (from checkpoint) | Default class | Assigned class | Planning status | Owning Task(s) | Class rationale |
|---|---|---|---|---|---|---|---|
| `AUDIT-01` | S0 / report gate invalid | Independent review is synthetic; generator writes the verdict | `MUST_SHIP` | `MUST_SHIP` | `PLANNED` | `TASK-006`, `TASK-008`, `TASK-009` | S0 finding; generator must emit pending review packet only, and Astra/high must be invoked via configured agent boundary after bundle freeze. |
| `AUDIT-02` | S0 / simulation validity invalid | Scenario oracles are circular and not frozen before execution | `MUST_SHIP` | `MUST_SHIP` | `PLANNED` | `TASK-001`, `TASK-004`, `TASK-006` | S0 finding; 46 concrete scenario contracts with explicit inputs, seeds, feature bindings, and independent expectations must be frozen and hashed before tick 0. |
| `AUDIT-03` | S1 / mechanics invariant violated | Fixture hazards create Hype despite a mandatory invariant | `MUST_SHIP` | `MUST_SHIP` | `PLANNED` | `TASK-001`, `TASK-002`, `TASK-006` | Violates `INV-BOT-ISOLATION` and `D-04`; `fixture` provenance must route to `synthetic_fixture_pool` only and never alter live `self.pool`. |
| `AUDIT-04` | S1 / coverage claim invalid | Reported 100% feature coverage is false | `MUST_SHIP` | `MUST_SHIP` | `PLANNED` | `TASK-003`, `TASK-006` | False coverage overclaims (`FEAT-14-READABILITY-AND-HUD`, acoustic audio, rendered video, visual bullet-time overlay) invalidate report credibility; status must be mechanically derived (`passed`, `failed`, `not_observed`, `blocked_by_implementation`). |
| `AUDIT-05` | S1 / reproducibility incomplete | Most command and trace artifacts are placeholders | `MUST_SHIP` | `MUST_SHIP` | `PLANNED` | `TASK-001`, `TASK-004`, `TASK-006` | 41 of 46 scenarios lacked real command/trace files and fell back to post-execution placeholders; every scenario must emit real canonical commands, `state_diff` traces, boundary hashes, and oracle evaluations or fail closed. |
| `AUDIT-06` | S1 / plan remediation incomplete | Revision 5 is not an authoritative, synchronized candidate | `MUST_SHIP` | `MUST_SHIP` | `PLANNED` | `TASK-005` | Consumes delegated decisions `DECISION-01..04` (`D-06`, `D-07`, `D-08`, `ISSUE-SIM-01..03`) to synchronize `GAMEPLAN-v2.md` rev 5, `gameplan-v2.json` rev 5, `S1-SIMULATION-PROFILE.md`, `CONTEXT-v2.md`, `STATUS.md`, and `config/directive-policy.json` rev 8 with real SHA-256 bindings. |
| `AUDIT-07` | S1 / readiness conclusion invalid | Readiness contradicts unresolved gates and evidence | `MUST_SHIP` | `MUST_SHIP` | `PLANNED` | `TASK-003`, `TASK-006`, `TASK-008`, `TASK-010` | `DEVELOPMENT-READINESS.json.ready` must be computed mechanically from observed gate results (0 open blocking issues, real rev-5 SHA-256, resolved decisions, regression pass, and verified independent Astra `READY` verdict). |
| `AUDIT-08` | S2 / reproducibility metadata invalid | Corpus manifest hash is not a SHA-256 digest | `SHOULD_SHIP` | `MUST_SHIP` (promoted) | `PLANNED` | `TASK-003`, `TASK-006` | Promoted to `MUST_SHIP`: `generate_viewer_corpus(seed=42, count=100000)` already computes a real SHA-256 `corpus_hash` and `generator_hash` in `coordination/scenario_inputs.py:54-61`; binding those real hashes into `CORPUS-MANIFEST.json` takes <10 lines in `TASK-003` and closes an explicit checkpoint acceptance criterion. |
| `AUDIT-09` | S2 / provenance risk | Immutable-run guarantees were not enforced | `MUST_SHIP` | `MUST_SHIP` | `PLANNED` | `TASK-003`, `TASK-006`, `TASK-008` | Dynamic `RUN_ID` derivation, `mkdir(exist_ok=False)`, write-exclusive `open("xb")` / no-overwrite semantics, strict artifact dependency ordering, and two-stage manifest sealing (pre-review bundle seal + post-review readiness/manifest seal). |

---

## 3. Evidence That Remains Useful (Carried Forward Verbatim)

Per `docs/planning/SIMULATION-EVIDENCE-AUDIT.md:158-167`, the following assets are preserved and reused—never rebuilt from scratch:

- All 115 manifest artifact hashes matched the current artifact bytes at audit time.
- Recorded authoritative-source hashes matched current source bytes at audit time.
- The fixed-step kernel contains genuine logic and multiple meaningful assertions for clock boundaries, controls, quorum, reward settlement, and deterministic replay.
- `SCENARIO-RESULTS.jsonl` contains 46 result records.
- Two identical executions of the selected golden kernel path appear to have produced the same canonical digest.
- The two identified revision-4 ambiguities—transition admission/clamping and nominal route-speed calibration—are legitimate plan questions, although their proposed resolutions are not yet approved or synchronized.

---

## 4. Determinism Surface Inventory & Baseline File Hashes

| Surface Item | File & Symbol | Current Consumer(s) | Checkpoint Flagged? | Classification |
|---|---|---|---|---|
| Fixed-step 20 Hz simulation kernel & state machine | `coordination/full_game_simulator.py` (`FullGameSimulator`, `HZ`, `STEP`, `DISTRICTS`) | `coordination/run_full_game_simulation.py`, `tests/test_full_game_simulation.py` | **Yes (`AUDIT-03` at lines 246–248)**; kernel logic otherwise validated as genuine asset | `VERIFIED` |
| Legacy prototype 20 Hz engine (pre-S1 rules) | `server/engine.py` (`Engine`, `cohort`, `DISTRICTS`) | `server/app.py`, `server/replay.py`, `tests/test_game.py` | Flagged in `PRODUCT.md:30` & `STATUS.md:28` as legacy `100+25/voter` prototype; needs SDC adapter/import so shipping runtime & simulation share one kernel | `VERIFIED` |
| Canonical command envelope & admission budget | `coordination/canonical_commands.py` (`make_command`, `validate_command`) | `coordination/full_game_simulator.py`, `coordination/run_full_game_simulation.py`, `tests/test_deterministic_kernel.py` | No (clean stdlib primitive) | `VERIFIED` |
| Deterministic JSON fingerprinting & content cache | `coordination/content_cache.py` (`canonical_bytes`, `canonical_hash`, `bytes_hash`, `validate_json`, `detached`, `ContentCache`) | All `coordination/*.py` modules and tests | No (clean stdlib primitive) | `VERIFIED` |
| Recursive JSON state diff, apply & summary | `coordination/state_transport.py` (`state_diff`, `apply_diff`, `summarize_diff`) | `tests/test_deterministic_kernel.py` (**not** yet wired into `FullGameSimulator` or `run_full_game_simulation.py` traces!) | **Yes (`AUDIT-05`)** — `state_diff` exists in `coordination/state_transport.py` but was unused by the simulation runner | `VERIFIED` |
| Seeded hash-counter viewer corpus generator | `coordination/scenario_inputs.py` (`generate_viewer_corpus`, `validate_corpus`, `GENERATOR_HASH`) | `coordination/run_full_game_simulation.py:897`, `tests/test_deterministic_kernel.py` | **Yes (`AUDIT-08`)** — generator computes valid `corpus_hash`/`generator_hash`, but runner wrote `"42-reused-corpus-100k"` to `CORPUS-MANIFEST.json` | `VERIFIED` |
| Scenario oracle definitions & matrix construction | `coordination/run_full_game_simulation.py:1598-1607` | `coordination/run_full_game_simulation.py` | **Yes (`AUDIT-02`)** — constructed *after* scenario execution with generic string | `VERIFIED` |
| Trace and command stream emission | `coordination/run_full_game_simulation.py:303-308, 1587-1596` (`record_trace` & fallback loop) | `coordination/run_full_game_simulation.py` | **Yes (`AUDIT-05`)** — only 5 of 46 scenarios called `record_trace`; 41 used post-hoc fallback placeholders | `VERIFIED` |
| Feature inventory & coverage accounting | `coordination/run_full_game_simulation.py:121-300, 1635-1644` (`build_feature_inventory`) | `coordination/run_full_game_simulation.py` | **Yes (`AUDIT-04`)** — hard-coded `"status": "passed"` and `"coverage_state": "covered"` for all 16 features | `VERIFIED` |
| Run root creation, manifest sealing & readiness | `coordination/run_full_game_simulation.py:31-32, 75-78, 1756-1930` | `coordination/run_full_game_simulation.py` | **Yes (`AUDIT-01`, `AUDIT-07`, `AUDIT-09`)** — constant `RUN_ID`, `exist_ok=True`, out-of-order `REVIEW-PACKET.md` hashing, synthetic `INDEPENDENT-REVIEW.md`, hardcoded `ready: True` | `VERIFIED` |

### Baseline SHA-256 Digests of Existing Files

| File Path | Baseline SHA-256 (Pre-Remediation) | Current SHA-256 (After Authorization & Decision Recording) |
|---|---|---|
| `AGENTS.md` | `4b7b04be8b6c14b2744c5f2f74638bd6a95081b60f7b11cd169a6c26ef351b6a` | `4b7b04be8b6c14b2744c5f2f74638bd6a95081b60f7b11cd169a6c26ef351b6a` |
| `docs/planning/SIMULATION-EVIDENCE-AUDIT.md` | `adcc2692789d29aae24b35acb522ea494c96748c5a20a04605461dcc52f3a798` | `adcc2692789d29aae24b35acb522ea494c96748c5a20a04605461dcc52f3a798` |
| `config/directive-policy.json` | `b1a8fc9c6dd221c3f35f2d02f7137ce49e5f7bcf3a9c861ce411785871445e28` | Updated with `remediation_rerun_and_decision_delegation` |
| `config/model-policy.json` | `7cfe130f28ff0c02f270320560e4a27cb6ca99edd88d39fbf8afe7127e6a289d` | `7cfe130f28ff0c02f270320560e4a27cb6ca99edd88d39fbf8afe7127e6a289d` |
| `docs/planning/STATUS.md` | `3c8568b11e9355c0b129dfddbe9792b61cc97edc21711e4f89fd2ae13224f62b` | `8f7ef0698e937a2fd97652c62943889dccead8c7802222749049fac889a9f476` |
| `docs/planning/USER-DIRECTIVE-AUDIT.md` | `2c2eb363c10b36f084fa7fafed01c68eb47970d3f399ad183bb53ee7519fe7a6` | `c3c7739de09e15c9000eade99160a27736267d6fac8041b5eccb1534124cf3f5` |
| `docs/planning/CONTEXT-v2.md` | `83be7ce8097c6400fb7b16d1a19dc2441f192cf2e39af5774c5e6901fd425c7e` | `83be7ce8097c6400fb7b16d1a19dc2441f192cf2e39af5774c5e6901fd425c7e` |
| `docs/planning/GAMEPLAN-v2.md` | `a6967a24601f259be027ed7fbebed5ad6e0784d4a7f7b7f6c0a2c3967e47e6ed` | `a6967a24601f259be027ed7fbebed5ad6e0784d4a7f7b7f6c0a2c3967e47e6ed` |
| `docs/planning/gameplan-v2.json` | `1b43be51add9d6c5e1cc2b6378e66a7f48fb76985435693b3dcf303ad6234937` | `1b43be51add9d6c5e1cc2b6378e66a7f48fb76985435693b3dcf303ad6234937` |
| `docs/planning/S1-SIMULATION-PROFILE.md` | `a8e3304309fd81eb795f5b7e5b609b66a65f5a3dae4f32ef0c4ded369049d2a4` | `a8e3304309fd81eb795f5b7e5b609b66a65f5a3dae4f32ef0c4ded369049d2a4` |
| `coordination/full_game_simulator.py` | `0badf1347ccedb7592fd582586c95331c7b723acb2b42842a5886302f711fc02` | `0badf1347ccedb7592fd582586c95331c7b723acb2b42842a5886302f711fc02` |
| `coordination/run_full_game_simulation.py` | `d436204cf7482919b6ae8602a278587de461b6ceb5203b07920eca5722e86cb4` | `d436204cf7482919b6ae8602a278587de461b6ceb5203b07920eca5722e86cb4` |
| `coordination/canonical_commands.py` | `ac33eca9f890b0b2eb78888f7592135e8d14fa17247dfddaddb24927095ae34e` | `ac33eca9f890b0b2eb78888f7592135e8d14fa17247dfddaddb24927095ae34e` |
| `coordination/scenario_inputs.py` | `1cf6a89939e3927d1b4aafe2ffc999aa3d5089339cfb496ad1510418a0abb9ba` | `1cf6a89939e3927d1b4aafe2ffc999aa3d5089339cfb496ad1510418a0abb9ba` |
| `coordination/state_transport.py` | `05a7168d82807819a4e4c1637ee60a7d27942966f1eeccb16a6e4d100d5bad76` | `05a7168d82807819a4e4c1637ee60a7d27942966f1eeccb16a6e4d100d5bad76` |
| `coordination/content_cache.py` | `c70694c893540d80a50498a0ba700a7a9599cdc7290524c5a98e63004be12a95` | `c70694c893540d80a50498a0ba700a7a9599cdc7290524c5a98e63004be12a95` |
| `coordination/context_contract.py` | `6998844f22691df022a3f76cae155b818a83aa398e4e2eef278e600b69dc0c5f` | `6998844f22691df022a3f76cae155b818a83aa398e4e2eef278e600b69dc0c5f` |
| `server/engine.py` | `f61fcf007254add796719f547ac008e0cf59dc4f4b79366ef24b8f4791e1052d` | `f61fcf007254add796719f547ac008e0cf59dc4f4b79366ef24b8f4791e1052d` |
| `tests/test_full_game_simulation.py` | `b43637b8cd20cdc3f5bc1adfef5c13878a1b78d68b5853bbfcb5fb6fd45e1c1a` | `b43637b8cd20cdc3f5bc1adfef5c13878a1b78d68b5853bbfcb5fb6fd45e1c1a` |
| `tests/test_gameplan_rules.py` | `85006bd0741f1ff876febdaea0a2b300a6563dd9beb690e1993b9148ebf68925` | `85006bd0741f1ff876febdaea0a2b300a6563dd9beb690e1993b9148ebf68925` |
| `tests/test_context_contract.py` | `9e267eaa11d54871fa8d891d41631b3b0514f0ee3ac3d8161044985af3ababe4` | `9e267eaa11d54871fa8d891d41631b3b0514f0ee3ac3d8161044985af3ababe4` |
