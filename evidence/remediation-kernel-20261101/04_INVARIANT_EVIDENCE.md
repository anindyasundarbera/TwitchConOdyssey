# 04_INVARIANT_EVIDENCE — Invariant Catalog and Evaluation Evidence

Recorded: 2026-11-02T00:35:30+05:30  
Bundle: `artifacts/simulations/full-game/full-game-20261101T185524Z-2647e033`  
Result: 24/24 Invariants Evaluated and Passing (18 Scenario Invariants across 99 evaluations + 6 Pipeline Invariants)

## 1. Pipeline Invariant Results (Standalone Validators)

| Invariant ID | Validator Function | Evidence Fields Checked | Observed Output | Verdict |
|---|---|---|---|---|
| `INV-REVIEW-AUTHORSHIP` | `validate_review_authorship` | `INDEPENDENT-REVIEW.md`, `REVIEW-INVOCATION.json`, `author_identity`, `agent_attribution` | Author: `codex_subagent/gpt-6-astra`, conv_id: `2d17a3bb-4dc0-4aab-a523-9808954b5762`, independent subagent | **PASS** |
| `INV-RUN-IMMUTABILITY` | `validate_run_immutability` | `new_run_id`, `old_run_id`, `old_run_tree_sha256`, `seal_state` | Exclusive run ID `full-game-20261101T185524Z-2647e033`; old run `b79455d3...` preserved byte-for-byte | **PASS** |
| `INV-CITATION-HASHES` | `validate_citation_hashes` | `RUN-MANIFEST.json`, `artifact_hashes` | All 169 cited artifacts in manifest exist and match recomputed SHA-256 digests (0 missing, 0 mismatched) | **PASS** |
| `INV-SOURCE-BYTES` | `validate_source_bytes` | `SOURCE-BINDINGS.json`, `recomputed_source_hashes` | All 31 bound files match exact repository SHA-256 bytes at sealing time | **PASS** |
| `INV-EVIDENCE-COVERAGE` | `validate_evidence_coverage` | `SCENARIO-MATRIX.json`, `per_invariant_results`, `COVERAGE.json` | 99 declared properties evaluated across 46 scenarios, 100 evaluations verified, 0 un-evaluated | **PASS** |
| `INV-READINESS-SEPARATION` | `validate_readiness_separation` | `DEVELOPMENT-READINESS.json`, `evidence_passed`, `review_verdict`, `submission_ready` | `ready: true`, `submission_ready: false`, review verdict `READY`; strict separation maintained | **PASS** |

---

## 2. Scenario Invariant Results (Concrete Evidence Evaluated)

| Invariant ID | Total Evals | Status | Evidence Fields Checked | Verification Logic |
|---|---|---|---|---|
| `INV-REPLAY` | 4 | PASS | `final_state_hash`, `boundary_hashes` | Replay matches canonical trace deltas and boundary digests exactly |
| `INV-ENGINE-AUTH` | 8 | PASS | `trace_deltas`, `state_hash` | State mutations originate solely from engine tick advancement |
| `INV-ASYNC-MODEL` | 3 | PASS | `command_log.provenance`, `command_log.status` | AI fixture commands arriving past planning cutoff expire without blocking tick clock |
| `INV-COMMAND-VAL` | 20 | PASS | `command_log.status`, `command_log.kind` | Invalid, duplicate, late, and out-of-phase commands fail closed |
| `INV-ACCOUNT-INFLUENCE` | 7 | PASS | `audience.counter_votes_count`, `command_log` | Each voter contributes at most one influence per turn |
| `INV-BOT-ISOLATION` | 5 | PASS | `command_log.provenance`, `bounty.synthetic_fixture_pool` | Bots and fixtures never increment human pool or affect quorum |
| `INV-HAZARD-BIND` | 6 | PASS | `hazard.committed`, `hazard.warning_active`, `command_log` | Committed hazard ID binds warning window, counters, and bounty increment |
| `INV-HAZARD-DEPEND` | 2 | PASS | `hazard.obstacle_active`, `hazard.hazard_countered` | Uncommitted hazard yields zero warning, zero obstacle, zero pool increase |
| `INV-SAFETY-CAPS` | 6 | PASS | `movement.turn_slowdown_ticks`, `movement.match_slowdown_ticks` | Collision slowdown capped at 40 ticks/turn and 120 ticks/match; zero multi-hit stacking |
| `INV-REACHABILITY` | 1 | PASS | `avatar.lane`, `avatar.lateral_pos` | Steering after warning onset clears obstacle lane prior to resolution tick |
| `INV-EFFECT-ORDER` | 7 | PASS | `trace_deltas`, `final_state.status`, `final_state.tick` | Clear_lane precedes collision; collision precedes delivery; deadline precedes equality delivery |
| `INV-SETTLEMENT-ONCE` | 10 | PASS | `final_state.status`, `terminal_settlement.settled_once` | Settlement occurs at most once, strictly at terminal state; zero payout on wipe |
| `INV-WIPE-CLEAN` | 2 | PASS | `final_state.status`, `terminal_settlement.total_hype` | Wipe settlements produce zero hype and zero streamer share; no residual state |
| `INV-MAX-TURNS` | 4 | PASS | `final_state.turn`, `final_state.tick` | Match terminates at or before tick 1800; turn 4 never instantiates |
| `INV-PAUSE-CLEAN` | 2 | PASS | `final_state.is_paused`, `final_state.tick` | Operator pause halts tick progression without catch-up ticks |
| `INV-FIXTURE-LABEL` | 4 | PASS | `command_log.provenance`, `bounty.synthetic_fixture_pool` | Synthetic fixtures remain visibly partitioned and audited |
| `INV-HOTFIX-SAFETY` | 3 | PASS | `hotfix_rules.slowdown_fraction`, `applied_hotfix_version` | Patches apply only at turn boundaries and obey permitted parameter bounds |
| `INV-CREDIBILITY` | 6 | PASS | `final_state`, `booths_visited` | Claims derived strictly from verified execution traces |
