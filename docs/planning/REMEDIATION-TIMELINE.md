# REMEDIATION-TIMELINE — Same-Day Cutoff, Freeze Point & Minute-by-Minute Allocation

## 1. Deadline Governance & Clock Parameters

- **Planning Start Timestamp:** `2026-11-01T17:36:28+05:30` (IST, UTC+05:30)
- **Plan Completion Timestamp:** `2026-11-01T18:00:00+05:30`
- **Same-Day Hard Cutoff:** `2026-11-01T23:59:00+05:30` (`360` minutes gross window from `18:00:00+05:30`; `270` minutes net execution ceiling against `240` minutes critical path, leaving `30` minutes net buffer and `120` minutes gross buffer).
- **Hackathon Submission Window (Tomorrow):** `2026-11-02` (`21:00 UTC` / `2026-11-03T02:30:00+05:30` earliest FAQ cutoff; `22:00 UTC` / `03:30:00+05:30` Rules cutoff per [`docs/research-2026-11-01/HACKATHON.md`](../research-2026-11-01/HACKATHON.md)).
- **Hard Code & Behavior Freeze Point:** `2026-11-01T21:00:00+05:30` (`180` minutes from `18:00:00+05:30`, reserving `179` minutes — **49.8% of remaining today budget** — exclusively for fresh simulation execution, independent Astra review, repair buffer, packaging, and final acceptance verification).

---

## 2. Minute-by-Minute Schedule (18:00 IST → 23:59 IST Cutoff)

| Window (IST, +05:30) | Duration | Phase / Wave | Tasks Executed | Parallelism / Gate Type | Reserved Buffer / Output |
|---|---|---|---|---|---|
| `17:36 – 18:00` | `24m` | **Phase 0: Checkpoint Binding, Authorization & Decision Recording** | Bind `SIMULATION-EVIDENCE-AUDIT.md`, append `remediation_rerun_and_decision_delegation` to `config/directive-policy.json`, write `DECISION-01..04` (`D-06..D-09`) in `docs/planning/DECISIONS.md`, emit `TASK-001..010` contracts | Serial governance gate (Completed) | `0m` slack; all 10 task contracts and 4 decision records persisted |
| `18:00 – 18:45` | `45m` | **Wave 1: SDC Core, Evidence Pipeline Primitives & Revision 5 Plan Sync** | `TASK-001` (`coordination/full_game_simulator.py`, 25m), `TASK-003` (`coordination/evidence_pipeline.py` & `scenario_inputs.py`, 25m), `TASK-005` (`GAMEPLAN-v2.md` rev 5, `gameplan-v2.json` rev 5, `S1-SIMULATION-PROFILE.md`, `config/directive-policy.json` rev 8, static tests, 20m) | `PARALLEL_WITH_ISOLATION` (3 disjoint write scopes) or sequential 3-step batch within 45m–70m | Includes `5m` per-task local smoke test |
| `18:45 – 19:45` | `60m` | **Wave 2: Dual-Consumer Runtime Wiring & Orchestrator Refactor** | `TASK-002` (`server/engine.py` + `tests/test_deterministic_kernel.py`, 20m) and `TASK-004` (`coordination/run_full_game_simulation.py` 46 frozen contracts + 2-stage CLI, 40m) | `SERIAL_REQUIRED` after `TASK-001` & `TASK-003` (`TASK-002` and `TASK-004` have disjoint write scopes) | Includes tempdir 46-scenario smoke run |
| `19:45 – 20:30` | `45m` | **Wave 3: Anti-Forgery Negative Test Suite & Integration** | `TASK-006` (`tests/test_full_game_simulation.py` positive + 6 mandatory negative test suites, 30m) + `15m` integration regression window | `SERIAL_REQUIRED` after `TASK-002`, `TASK-004`, `TASK-005` | `15m` integration repair window reserved |
| `20:30 – 21:00` | `30m` | **Wave 4: Pre-Rerun Ledger Binding & Hard Freeze Gate** | `TASK-007` (bind all code/test/plan SHA-256 hashes in `config/directive-policy.json` and run `context_contract --validate-only` + 70+ unit tests, 15m) + `15m` pre-freeze verification buffer | `SERIAL_REQUIRED` after `TASK-006` | **21:00 IST HARD FREEZE POINT** (No `MUST_SHIP` code/behavior changes after 21:00 IST) |
| `21:00 – 21:30` | `30m` | **Wave 5: Authorized Fresh Simulation Run (Stage 1 Freeze)** | `TASK-008` (`python3 -m coordination.run_full_game_simulation --stage simulate --authorize AUTHORIZE_COMPLETE_GAME_SIMULATION=true`, 15m) + `15m` artifact verification | `SERIAL_REQUIRED` (Exclusive resource: `artifacts/simulations/full-game/<NEW_RUN_ID>/`) | Produces frozen pre-review bundle and `REVIEW-PACKET.md` |
| `21:30 – 22:15` | `45m` | **Wave 6: Genuine Independent Astra Review & Stage 2 Bundle Finalization** | `TASK-009` (`context_contract --task plan_review`, `invoke_subagent` independent review writing `INDEPENDENT-REVIEW.md` & `REVIEW-INVOCATION.json`, then `--stage finalize`, 30m) + `15m` review inspection buffer | `SERIAL_REQUIRED` (Cannot run in parallel with simulation; requires frozen `REVIEW-PACKET.md`) | Seals `DEVELOPMENT-READINESS.json` and `RUN-MANIFEST.json` |
| `22:15 – 23:15` | `60m` | **Contingency Repair Pass Window (Reserved for Re-Run if Review Returns `REVISE`)** | Reserved exclusively in case `TASK-009` independent review identifies any defect requiring a bounded fix and a second fresh simulation run (`<NEW_RUN_ID_2>`) before cutoff | Serial contingency gate | `60m` explicit repair-and-rerun capacity |
| `23:15 – 23:45` | `30m` | **Wave 7: Final Acceptance Audit & State Closure** | `TASK-010` (11-point checkpoint acceptance verification, preserved rejected run tree SHA-256 proof, `REMEDIATION-STATE.md` & `STATUS.md` closure, final `context_contract --validate-only`, 20m) + `10m` packaging check | `SERIAL_REQUIRED` after `TASK-009` | Verified execution state & handoff report |
| `23:45 – 23:59` | `14m` | **Final Handoff / Requester Escalation Review Buffer** | Surface `ESCALATE` items (`DECISION-01..04` provisional product gates and `TIME_GATE_CONFLICT` items) to requester before `23:59` cutoff | Human-review buffer | `14m` hard cutoff margin |

---

## 3. Gates That Cannot Run in Parallel & `TIME_GATE_CONFLICT` Registry

### Non-Parallelizable Gates
1. **Pre-Rerun Hash Binding (`TASK-007`) → Stage 1 Simulation (`TASK-008`):** `SOURCE-BINDINGS.json` inside `<NEW_RUN_ID>` must bind the exact frozen bytes of `config/directive-policy.json` and all code/plan files.
2. **Stage 1 Simulation (`TASK-008`) → Independent Review (`TASK-009`):** `REVIEW-PACKET.md` must bind the immutable SHA-256 digests of the completed scenario results, coverage, and issues before the independent reviewer is invoked (`AUDIT-01`, `AUDIT-09`).
3. **Independent Review (`TASK-009`) → Stage 2 Finalize (`TASK-009`):** `DEVELOPMENT-READINESS.json` and `RUN-MANIFEST.json` depend on the verified `INDEPENDENT-REVIEW.md` and `REVIEW-INVOCATION.json` (`AUDIT-07`, `AUDIT-09`).

### `TIME_GATE_CONFLICT` Entries

| Conflict ID | Rule / Gate Source | Nature of Conflict | Smallest Compliant Path (Adopted in Plan) |
|---|---|---|---|
| `TGC-01` | `AGENTS.md:11` ("Gameplay remains disabled... Do not run `server.app`, `server.replay`, gameplay tests, browser gameplay or `harness.run`") vs `FEAT-14-READABILITY-AND-HUD` / `D-08` live browser/Twitch/video capture | The Linux sandbox denies socket creation (`EVIDENCE.md:10,16`) and `AGENTS.md:11` forbids running `server.app` or browser gameplay during this phase. Therefore, live browser rendering (`FEAT-14`), acoustic audio output (`FEAT-13` audio), and a 3-minute live Twitch video (`D-08` / `FEAT-15`) cannot be observed inside this remediation window. | Per `SIMULATION-EVIDENCE-AUDIT.md:84` (`AUDIT-04`) and `DECISION-03` (`D-08`), `derive_feature_statuses` mechanically marks unrendered/live capabilities as `not_observed` (never fabricated as `passed`), and `DEVELOPMENT-READINESS.json` separates `ready: true` (simulation & candidate plan gate for bounded development) from `submission_ready: false` (live external Twitch/video gate). |
| `TGC-02` | `SIMULATION-EVIDENCE-AUDIT.md:35` ("Invoke Astra/high through the configured agent boundary after freezing the evidence bundle") vs local offline environment without external OpenAI API keys | `config/model-policy.json:51` maps `plan_review` (`principal_review`) to `provider: "codex_subagent", model: "gpt-6-astra", reasoning_effort: "high"`. Direct external HTTP calls are disabled/uncredentialed (`EVIDENCE.md:17`), whereas the local agent environment provides the native `invoke_subagent` boundary. | In `TASK-009`, compile the `plan_review` packet via `coordination.context_contract` and invoke an isolated review subagent via `invoke_subagent` (with fresh narrow context, no chat history, and `REVIEW-INVOCATION.json` recording the exact subagent `conversationId` and bound SHA-256 digests). If subagent invocation were to fail, fail closed with `BLOCKED_REVIEW_UNAVAILABLE` and `ready: false`. |
