# 02_TASK_INDEX — Atomic Task Register

Contract version: v1.0 (2026-11-02). Task files under `tasks/` are the binding
contracts; this index and `task_manifest.yaml` are summaries and must agree.

| ID | WS | Title | Hard deps | Gates | Parallel class | Risk | Status |
|---|---|---|---|---|---|---|---|
| TASK-001 | W1 | Resolve evidence/commit-hash discrepancy (D-H1) | — | P (packet) | SERIAL (creates correction file) | CRITICAL | PLANNED |
| TASK-002 | W1 | Resolve review-packet-hash discrepancy (D-H2) | TASK-001 | P | SERIAL (amends same file) | CRITICAL | PLANNED |
| TASK-003 | W1 | Run-root disposition policy + sealed hash baseline | — | P | PARALLEL_SAFE vs 001/002 (different files; same W1 agent executes serially) | CRITICAL | PLANNED |
| TASK-004 | W2 | §7 development-closure verification record | TASK-001..003 | P | SERIAL_REQUIRED | HIGH | PLANNED |
| TASK-005 | W2 | STATUS.md closure update + directive-ledger rebind | TASK-004 | P | SERIAL_REQUIRED (exclusive shared files) | CRITICAL | PLANNED |
| TASK-006 | W3 | Gameplay core implementation (engine/kernel boundary) | TASK-005 | G-A, G-B, G-C | PARALLEL_WITH_ISOLATION (owns engine boundary) | HIGH | GATED |
| TASK-007 | W4 | Presentation & mobile HUD | TASK-006 contracts | G-A, G-B, G-C | PARALLEL_SAFE (distinct paths) | MEDIUM | GATED |
| TASK-008 | W5 | Twitch identity linking & command intake | TASK-006 contracts | G-A, G-B, G-C | PARALLEL_SAFE (distinct paths) | HIGH | GATED |
| TASK-009 | W6 | Booth telemetry & evidence | TASK-005 | G-A, G-B, G-C | PARALLEL_SAFE (distinct paths) | MEDIUM | GATED |
| TASK-010 | W7 | Submission/demo pipeline | TASK-006..009 completion evidence | G-A, G-B, G-C + live gate for capture | SERIAL_REQUIRED | MEDIUM | GATED |
| TASK-011 | W8 | Independent final review (read-only + review output) | TASK-006..010 | G-A; configured plan_review route | TERMINAL | HIGH | GATED |

## Gates (referenced by ID)

- **P — Compiler packet:** fresh `coordination.context_contract` packet, phase `plan`,
  registered task name (`development` or `planner_orchestrator` for W1/W2), owned paths
  bound. Rejection ⇒ stop, record verbatim.
- **G-A — Explicit user gameplay authorization:** new recorded directive; not inferable
  from `simulation_and_plan_ready`, readiness flags, or this plan's existence.
- **G-B — Execution packet accepted:** compiler accepts the gameplay task after G-A.
- **G-C — Codebase-memory index:** path assignment finalized via index/graph discovery;
  unavailability ⇒ record blocker, stop.

## Shared/exclusive resources

- `evidence/remediation-kernel-20261101/09_CORRECTIONS-20261102.md`: exclusive to
  TASK-001 then TASK-002 (serial).
- `evidence/remediation-kernel-20261101/10_RUN-ROOT-DISPOSITION-20261102.md` and
  `.../10_RUN-ROOT-HASHES-20261102.json`: exclusive to TASK-003.
- `docs/planning/STATUS.md`, `config/directive-policy.json`: exclusive to TASK-005
  (single transaction; ledger pins their hashes — any edit without rebind fails the
  compiler closed).
- All `artifacts/simulations/full-game/**`: read-only to every task.

## Permitted executor checks (no authorization expansion)

Static/context-framework suites only: `tests.test_context_contract`,
`tests.test_deterministic_kernel`, `tests.test_plan_rehearsal`,
`tests.test_model_router`, plus compiler `--validate-only`; `test_gameplan_rules` /
`test_city_setting` are static source/plan checks per recorded STATUS practice.
Forbidden everywhere: gameplay tests, `test_full_game_simulation` re-runs as new
evidence, `server.app`, `server.replay`, browser gameplay, `harness.run`, network/live
calls. Reported test/replay totals are reconciled against committed artifacts, never
independently re-executed as new evidence.
