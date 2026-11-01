# 03_TEST_EVIDENCE — Test Execution and Anti-Forgery Matrix

Recorded: 2026-11-02T00:35:00+05:30  
Status: ALL TESTS PASSING (53/53 tests across deterministic kernel and full simulation; 46/46 static plan/context tests)

## 1. Test Suite Summary

| Test Module | Tests Ran | Status | Execution Time | Coverage / Purpose |
|---|---|---|---|---|
| `tests.test_deterministic_kernel` | 40 | PASS | ~10.2s | TST-01..TST-20, SDC bindings, purity, 100k corpus, state transport |
| `tests.test_full_game_simulation` | 13 | PASS | ~185.4s | Two-stage simulation, anti-forgery, replay parity, manifest sealing |
| `tests.test_gameplan_rules` | 8 | PASS | ~0.2s | Revision 5 rules, clock oracles, total ordering |
| `tests.test_context_contract` | 24 | PASS | ~0.4s | Context contract compiler, policy hashes, budget bounds |
| `tests.test_city_setting` | 3 | PASS | ~0.1s | San Diego route setting |
| `tests.test_model_router` | 6 | PASS | ~0.1s | Model router, token caps, budget enforcement |
| `tests.test_plan_rehearsal` | 5 | PASS | ~0.1s | Plan rehearsal, provenance, review completeness |
| **Total Permitted Suite** | **99** | **PASS** | **~196.4s** | Zero failures, zero errors |

---

## 2. Deterministic Kernel Test Matrix (TST-01 through TST-20)

| ID | Test Method | Scope / Invariant | Status | Evidence Field / Property Observed |
|---|---|---|---|---|
| `TST-01` | `test_tst01_delivery_at_1799` | Delivery eligibility | PASS | Step starting at 1798 with delivery at tick 1799 settles delivered with full payout |
| `TST-02` | `test_tst02_delivery_at_1800` | Deadline wipe equality | PASS | Step starting at 1799 ending at tick 1800 triggers deadline wipe; settlement is exactly zero |
| `TST-03` | `test_tst03_delivery_at_1801` | Post-deadline delivery | PASS | Delivery attempt after tick 1800 rejected; state is wiped; settlement is zero |
| `TST-04` | `test_tst04_tst07_warning_boundaries` | Warning onset (tick 299) | PASS | Warning is `False` at tick 299 with committed hazard |
| `TST-05` | `test_tst04_tst07_warning_boundaries` | Warning onset (tick 300) | PASS | Warning is `True` at tick 300 with committed hazard |
| `TST-06` | `test_tst04_tst07_warning_boundaries` | Warning close (tick 399) | PASS | Warning is `True` at tick 399 with committed hazard |
| `TST-07` | `test_tst04_tst07_warning_boundaries` | Warning close (tick 400) | PASS | Warning is `False` at tick 400 (half-open `[300, 400)`) |
| `TST-08` | `test_tst08_warning_hazard_id_mismatch` | Hazard ID gating | PASS | Mismatched hazard ID returns `warning_active: False` |
| `TST-09` | `test_tst09_command_at_1799_applies_before_deadline` | Command order at 1799 | PASS | Command submitted at tick 1799 applied before tick 1800 wipe |
| `TST-10` | `test_tst10_command_at_1800_wipe_wins` | Deadline priority | PASS | Command submitted at tick 1800 wiped; command rejected |
| `TST-11` | `test_tst11_event_tick_preservation` | Event tick preservation | PASS | State deltas and events record actual event tick (e.g. 100), not terminal settlement tick |
| `TST-12` | `test_tst12_purity` | Zero I/O purity | PASS | Kernel performs zero file, network, process, or wall-clock I/O; deterministic functions |
| `TST-13` | `test_tst13_authority_shared_functions` | Dual-consumer authority | PASS | `server.engine` and `coordination.full_game_simulator` call identical kernel functions |
| `TST-14` | `test_tst14_tst15_replay_parity` | Dual-consumer state parity | PASS | Both consumers produce identical state hashes given identical command sequences |
| `TST-15` | `test_tst14_tst15_replay_parity` | Dual-consumer event parity | PASS | Both consumers emit identical event streams and boundary hashes |
| `TST-16` | `test_tst16_tst18_pipeline_invariants` | Complete pipeline validation | PASS | All 6 pipeline invariants evaluate PASS on complete valid evidence bundle |
| `TST-17` | `test_tst16_tst18_pipeline_invariants` | Missing evidence rejection | PASS | Missing artifacts fail closed (status `FAIL`) |
| `TST-18` | `test_tst16_tst18_pipeline_invariants` | Tampered evidence rejection | PASS | Tampered hashes or altered source bytes fail closed |
| `TST-19` | `test_tst19_generic_oracle_pass_declared_property_fail` | Property-specific failure | PASS | Scenario oracle passes but failing declared property causes scenario failure |
| `TST-20` | `test_tst20_undeclared_invariant_excluded` | Undeclared property isolation | PASS | Undeclared invariants are excluded and marked `NOT_EVALUATED` |

---

## 3. Full Game Simulation Anti-Forgery Suite

1. `test_deterministic_golden_replay_identical_digests`: PASS
2. `test_finalize_rejects_reseal_before_any_writes`: PASS
3. `test_missing_and_malformed_prerequisites_fail_closed_despite_true_arguments`: PASS (35 negative variations tested)
4. `test_negative_feature_coverage_cannot_fabricate_passed_for_unobserved_render`: PASS
5. `test_negative_fixture_and_bot_provenance_cannot_mint_live_hype_or_quorum`: PASS
6. `test_negative_readiness_is_false_when_any_gate_fails`: PASS
7. `test_negative_simulator_cannot_author_independent_review_or_overwrite_run_root`: PASS
8. `test_negative_validators_reject_defective_baseline_artifacts`: PASS
9. `test_positive_two_stage_simulation_and_finalization_in_isolated_tempdir`: PASS
10. `test_preserved_rejected_run_remains_byte_for_byte_unchanged`: PASS
11. `test_raw_inventory_and_review_authorship_tampering_are_rejected`: PASS
12. `test_source_drift_aborts_finalize_before_any_writes`: PASS
13. `test_valid_revise_remains_sealable_and_not_ready`: PASS
