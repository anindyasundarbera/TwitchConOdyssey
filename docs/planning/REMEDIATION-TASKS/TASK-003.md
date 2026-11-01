# TASK-003 — SDC Evidence Pipeline Primitives: Exclusive Run Root, Derived Coverage, Corpus Binding & Computed Readiness

## Task Identity
- **Task ID:** `TASK-003`
- **Title:** SDC Evidence Pipeline Primitives: Exclusive Run Root, Derived Coverage, Corpus Binding & Computed Readiness
- **Contract Version:** `2.0.0`
- **Baseline Commit SHA (`BASELINE_SHA`):** `2bb0b538bcfed216590ec49039e9972c5e363f0d` (`plan-baseline/remediation-v2.0`, branch `main`)
- **Work Mode (`B-2` / `B-3` Reconciled):** Greenfield creation of `coordination/evidence_pipeline.py` (`B-3`) + converge-existing-to-contract extension of `coordination/scenario_inputs.py` (`B-2`, exists at 74 lines, SHA-256 `1cf6a89939e3927d1b4aafe2ffc999aa3d5089339cfb496ad1510418a0abb9ba`, adding `build_corpus_manifest`).
- **Planning Status:** `READY`
- **Ship Criticality:** `MUST_SHIP`
- **Risk Classification:** `CRITICAL` (Directly governs `AUDIT-01`, `AUDIT-04`, `AUDIT-07`, `AUDIT-08`, `AUDIT-09` anti-forgery gates)
- **Linked Audit IDs:** `AUDIT-01`, `AUDIT-04`, `AUDIT-07`, `AUDIT-08`, `AUDIT-09`
- **Linked Decision IDs:** `DECISION-03` (`D-08`)

## Objective
Create `coordination/evidence_pipeline.py` and extend `coordination/scenario_inputs.py` so that:
1. Run directories are created with exclusive fail-on-collision semantics (`exist_ok=False`) and files are written with exclusive `open("xb")` semantics (`AUDIT-09`).
2. `CORPUS-MANIFEST.json` binds the real 64-hex SHA-256 `corpus_hash`, `generator_hash`, `template_hash`, and `generator_source_sha256` from `generate_viewer_corpus` (`AUDIT-08`).
3. `FEATURE-INVENTORY.json` and `COVERAGE.json` derive feature statuses mechanically from `SCENARIO-RESULTS.jsonl` and observed environment capabilities, marking unrendered visual/audio/live features (`FEAT-14-READABILITY-AND-HUD`, plus visual/acoustic/live sub-claims of `FEAT-12`, `FEAT-13`, `FEAT-15`) as `not_observed` (`AUDIT-04`).
4. The simulation pipeline is structurally prevented from writing `INDEPENDENT-REVIEW.md` (`AUDIT-01`); instead it emits `REVIEW-PACKET.md` in dependency order (`AUDIT-09`) and exposes `verify_independent_review_artifact()` and `compute_development_readiness()` (`AUDIT-07`) for post-review finalization.

## Checkpoint Reference
- **`AUDIT-01` (S0):** "Required correction: the generator may create a pending review packet, but it must never generate the reviewer verdict or mark the model call completed."
- **`AUDIT-04` (S1):** "Required correction: derive feature status from scenario evidence. Use `not_observed` or `blocked_by_implementation` when no qualifying render/audio/live path exists."
- **`AUDIT-07` (S1):** "Required correction: readiness must be false until the evidence defects are repaired, mandatory decisions for the proposed development milestone are resolved, the candidate plan is genuinely bound, regression passes, and a real independent review returns READY."
- **`AUDIT-08` (S2):** "Required correction: record the generator source hash, version, seed, count, canonical corpus digest, and either the content-addressed corpus artifact or a verified deterministic regeneration recipe."
- **`AUDIT-09` (S2):** "Required correction: derive a unique run ID at invocation, create the root with exclusive semantics, fail if it exists, finalize artifacts in dependency order, and seal the manifest last."

## Dependencies
- **Hard Dependencies:** `DECISION-03` (`D-08`) in `docs/planning/DECISIONS.md`.
- **Integration Dependencies:** `coordination/content_cache.py`, `coordination/scenario_inputs.py`.
- **Soft Dependencies:** `TASK-001` (runs in parallel in Wave 1).
- **External Prerequisites:** None.

## Preconditions
Run the repository context compiler before editing:
```bash
python3 -m coordination.context_contract --task development --phase plan \
  --owned-path coordination/scenario_inputs.py \
  --owned-path coordination/evidence_pipeline.py
```

## Context to Load
- `docs/planning/SIMULATION-EVIDENCE-AUDIT.md:21-36, 65-99, 116-157`
- `docs/planning/01_ARCHITECTURE.md` (§2 and §3.3–3.5)
- `coordination/scenario_inputs.py:1-75`
- `coordination/content_cache.py:128-159` (`canonical_bytes`, `canonical_hash`, `bytes_hash`, `require_hash`)

## Input Contracts
- `feature_specs`: list of 16 feature definitions with `feature_id`, `required_evidence_kind` (`"deterministic_state_and_commands"` vs `"render_capture_and_mobile_viewport"`), and `sub_claims`.
- `scenario_results`: list of executed scenario result dicts from `SCENARIO-RESULTS.jsonl`.
- `corpus`: dict returned by `generate_viewer_corpus(seed=42, count=100000)`.

## Output Contracts
- `coordination/scenario_inputs.py`:
  - Adds `build_corpus_manifest(corpus, *, generator_source_path="coordination/scenario_inputs.py", generator_source_sha256=...) -> Dict[str, Any]` validating `corpus` via `validate_corpus(corpus)` and returning a manifest whose `"sha256"` field is `require_hash(corpus["corpus_hash"])` (64 lowercase hex chars).
- `coordination/evidence_pipeline.py` (new module):
  - `PRESERVED_REJECTED_RUN_ID = "full-game-20261101T102226Z-a8e33043"`
  - `derive_run_id(profile_sha256: str, utc_timestamp: Optional[str] = None) -> str`: constructs `full-game-<YYYYMMDDTHHMMSSZ>-<profile_first8>` and raises `ValueError` if it equals `PRESERVED_REJECTED_RUN_ID`.
  - `create_immutable_run_root(base_dir: Path, run_id: str, authorization_token: str) -> Path`: requires `authorization_token == "AUTHORIZE_COMPLETE_GAME_SIMULATION=true"`, rejects `PRESERVED_REJECTED_RUN_ID`, creates `run_dir` and subdirectories (`commands`, `traces`, `state-hashes`, `results`) with `exist_ok=False` (raises `FileExistsError` on collision).
  - `write_exclusive_text(path: Path, text: str)` and `write_exclusive_json(path: Path, data: Any)`: writes using `open(path, "xb")`; raises `FileExistsError` if `path` already exists; explicitly forbids writing `INDEPENDENT-REVIEW.md` from simulator code (`forbid_synthetic_review=True` default).
  - `verify_scenario_trace_Integrity(scenario_id: str, run_dir: Path, expected_contract_hash: str) -> Dict[str, Any]`: verifies `commands/<scenario_id>.json` and `traces/<scenario_id>.jsonl` exist, are non-empty, bind `expected_contract_hash`, contain substantive `state_diff` operations, and are not placeholder dictionaries (`AUDIT-05`).
  - `derive_feature_statuses(feature_specs, scenario_results, *, render_observed=False, audio_observed=False, live_service_observed=False) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]`: mechanically derives `FEATURE-INVENTORY.json` and `COVERAGE.json` (`FEAT-14-READABILITY-AND-HUD` derived as `status="not_observed", coverage_state="not_observed"` when `render_observed=False`; `FEAT-12`, `FEAT-13`, `FEAT-15` state-machine parts marked `passed` while visual/acoustic/rendered-video sub-claims are marked `not_observed`).
  - `verify_independent_review_artifact(run_dir: Path) -> Dict[str, Any]`: reads `REVIEW-PACKET.md`, `INDEPENDENT-REVIEW.md`, and `REVIEW-INVOCATION.json`; verifies that `INDEPENDENT-REVIEW.md` exists, was authored via an external invocation record (`REVIEW-INVOCATION.json` with valid `packet_hash`, `prompt_hash`, `output_hash`, and `evidence_origin != "synthetic_generator"`), binds the exact SHA-256 hashes in `REVIEW-PACKET.md`, and extracts `verdict in ("READY", "REVISE")`.
  - `compute_development_readiness(...) -> Dict[str, Any]`: computes `ready` purely from gate booleans; returns `ready: False` if any gate fails, any blocking decision is unresolved, `candidate_plan_hash` is not a 64-hex SHA-256 matching `GAMEPLAN-v2.md`, or `review_verdict != "READY"`.
  - `seal_run_manifest(run_dir: Path, ...) -> Dict[str, Any]`: hashes all files in `run_dir` after all artifacts exist and writes `RUN-MANIFEST.json` exclusively last.

## Write Scope
- **Permitted Modifications (Exact):** `coordination/scenario_inputs.py`
- **Permitted New Files:** `coordination/evidence_pipeline.py`
- **Protected Paths (Must Not Modify):**
  - `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/**` (Preserved rejected run directory)
  - `config/directive-policy.json`, `coordination/context_contract.py`

## Implementation Requirements
- Enforce `require_hash` on `candidate_plan_hash`, `corpus_manifest["sha256"]`, `scenario_matrix_hash`, and all `REVIEW-PACKET.md` artifact bindings.
- Ensure `write_exclusive_text` / `write_exclusive_json` raises `PermissionError("Simulator may not author INDEPENDENT-REVIEW.md")` if called on `INDEPENDENT-REVIEW.md` without an explicit external review-finalizer token/invocation record.

## Determinism Contract
- **Pure Derivation:** `derive_feature_statuses` and `compute_development_readiness` are deterministic pure functions of their inputs.
- **Dual Consumers:**
  - *Game / Release Consumer:* `server/app.py` / `harness/run.py` health & release-gate evaluators can import `derive_feature_statuses` and `compute_development_readiness`.
  - *Evidence Consumer:* `coordination/run_full_game_simulation.py` and `tests/test_full_game_simulation.py`.
- **Anti-Forgery Check:** Calling `compute_development_readiness` with `"rev5-candidate-bound"`, unresolved `["D-06"]`, or a missing/synthetic `REVIEW-INVOCATION.json` deterministically returns `ready=False` (or raises `ValueError`).

## Execution Guidance
1. Add `build_corpus_manifest` to `coordination/scenario_inputs.py`.
2. Create `coordination/evidence_pipeline.py` implementing all 7 pipeline primitives.
3. Run a self-contained Python smoke check verifying positive and negative cases.

## Acceptance Criteria
- `build_corpus_manifest` produces a 64-char hex SHA-256 in `sha256` and rejects `"42-reused-corpus-100k"`.
- `create_immutable_run_root` fails on existing directory or on `full-game-20261101T102226Z-a8e33043`.
- `derive_feature_statuses` marks `FEAT-14-READABILITY-AND-HUD` as `not_observed` when `render_observed=False` and `0` scenarios exercise it.
- `compute_development_readiness` returns `ready: False` whenever any gate is unmet.

## Verification
```bash
python3 -m unittest tests.test_deterministic_kernel -v
```

## Integration Contract
- Consumed by `TASK-004` (`coordination/run_full_game_simulation.py`), `TASK-006` (`tests/test_full_game_simulation.py`), and `TASK-008`/`TASK-009`.

## Completion Evidence
- `coordination/evidence_pipeline.py` created and `coordination/scenario_inputs.py` updated, with SHA-256 digests recorded in `docs/planning/REMEDIATION-STATE.md`.

## Failure Handling
- Stop and report if any `coordination/content_cache.py` budget is exceeded when hashing the 100,000-message corpus (note: `test_100k_fixture_capability` already verifies 100k corpus fits within `MAX_JSON_NODES = 1,000,000`).

## Scheduling Metadata
- **Parallelization:** `PARALLEL_WITH_ISOLATION` (Wave 1; owns `coordination/evidence_pipeline.py` and `coordination/scenario_inputs.py`, disjoint from `TASK-001`)
- **Risk:** `CRITICAL`
- **Priority:** `P0`
- **Ship Criticality:** `MUST_SHIP`
- **Amortization:** `NET_NEGATIVE`
- **Estimated Sessions:** `1` bounded session (~25 mins)
- **Complete Before Freeze Point:** `true`
- **Blocks Packaging/Submission:** `true`
- **Blocked Flag:** `false`
