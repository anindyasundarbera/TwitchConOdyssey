# Orchestration Projection — Contract-Driven Autonomous Delivery Protocol v2.0

**Artifact class:** planning / orchestration projection
**Source protocol:** `contract-driven-autonomous-delivery-protocol.md` — v2.0 (incl. §3.1 Baseline Commit Gate)
**Projected plan:** Same-Day Deterministic Remediation Plan v2.0 (TASK-001..TASK-010, AUDIT-01..AUDIT-09)
**Projection date:** 2026-11-01
**Status:** projection complete; execution not yet dispatched

---

## 1. Purpose

This document is the protocol instantiated against this repository. It is not a restatement of
`REMEDIATION-PLAN.md`; it is the coordination layer that governs *how* the plan is executed:
eligibility, isolation, review gates, authorization boundaries, evidence and completion.

It was produced by a read-only bootstrap reconciliation of the working tree, not by trusting the
plan's own status claims — per protocol §3, *never trust a DONE status without sufficient evidence*.

---

## 2. Instantiated mission (§1)

Deliver TASK-001..TASK-010 so that `compute_development_readiness()` can return `ready: true`
against all six readiness predicates, with evidence that survives independent review.

Binding characteristic: this is a **self-auditing delivery**. The plan exists because the prior
evidence pipeline was rejected for circular oracles, placeholder artifacts and a self-authored
verdict (AUDIT-01/02/05/09). The protocol's anti-patterns are therefore the primary acceptance
criteria, not boilerplate:

- implementation reports are not evidence of completion;
- "all tests passed" is not an accepted claim;
- a verdict produced by the party that produced the evidence is synthetic.

---

## 3. Governance precedence (§2) — adopt, do not replace

Authority chain, highest first:

| Order | Authority | Enforcement |
|---|---|---|
| 1 | `AGENTS.md` + `docs/planning/directive-policy.json` | `coordination/context_contract.py` (`packet_hash 153dad11…d37d`) |
| 2 | `GAMEPLAN-v2.md` rev 5 / `gameplan-v2.json` | canonical plan (authoritative only after TASK-005) |
| 3 | `remediation-plan.json` + `REMEDIATION-TASKS/TASK-001..010.md` | task manifest used for scheduling |
| 4 | `model-policy.json` / `MODEL-CONFIGURATION.md` | role routing |
| 5 | `REMEDIATION-STATE.md` | single authoritative state writer |

Non-substitution rule: no new orchestration framework, plan format or evidence layout. The immutable
allocation helpers (`allocate_immutable_run_root`, `write_immutable_json`, `apply_diff`-verified
manifests) are the mandated evidence mechanism; orchestration rides on `context_contract.py`.

---

## 4. Bootstrap reconciliation (§3, §3.1)

### 4.1 Verified repository state

| Fact | Observed value |
|---|---|
| Branch | `main` |
| HEAD | unborn (0 commits) |
| Tracked files | 0 |
| Working tree | 23 untracked entries (directories collapsed) |
| Git identity | configured (`user.name`, `user.email` present) |
| Ignore rules | `.runtime/`, `__pycache__/`, `*.pyc`, `.env` |
| Preserved baseline | `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/` present, single run |
| Planning set | all 12 artifacts present under `docs/planning/`, incl. `REMEDIATION-TASKS/` |
| `coordination/full_game_simulator.py` | **present** |
| `coordination/scenario_inputs.py` | **present** |
| `coordination/evidence_pipeline.py` | **absent** (expected — TASK-003 greenfield) |

### 4.2 Findings requiring action before dispatch

**B-1 — No baseline exists (RESOLVED BY GATE).** The plan asserted "branch `master` has an unborn
HEAD"; the branch is `main` and HEAD is unborn with zero tracked files. No task record can carry a
baseline commit, so no change can be attributed, no regression isolated, no finding reproduced.
Resolution: protocol §3.1 Baseline Commit Gate — commit all work through the remediation plan first,
record the SHA in `00_CONTEXT.md`, and use it as the baseline field of every task record.

**B-2 — Two tasks are mis-scoped as greenfield.** `full_game_simulator.py` and `scenario_inputs.py`
already exist. TASK-001 and TASK-004 are therefore *converge-existing-to-contract* work, not creation.
Consequences: eligibility check must include a diff-against-contract review, and the 55m/50m estimates
are unreliable until that diff is measured.

**B-3 — `evidence_pipeline.py` absent.** Confirms TASK-003 is greenfield. No action.

**B-4 — Read-only invariant.** The preserved rejected run must not be written by any task. The sorted
tree digest `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d` is the tripwire,
re-verified at every wave boundary (pre and post).

---

## 5. Eligibility and wave schedule (§7)

Recomputed against actual write scopes rather than the plan's wave numbers.

| Wave | Tasks | Classification | Write-scope audit |
|---|---|---|---|
| 1 | TASK-001 ‖ TASK-003 ‖ TASK-005 | PARALLEL_SAFE | `full_game_simulator.py` / `evidence_pipeline.py` / 6 plan docs + 2 tests — disjoint |
| 2 | TASK-002 ‖ TASK-004 | PARALLEL_SAFE | `engine.py`+`replay.py` / `scenario_inputs.py` — disjoint; both consume TASK-001's frozen API |
| 3 | TASK-006 | SERIAL_REQUIRED | single file `run_full_game_simulation.py`, consumes 001/003/004 |
| 4 | TASK-007 | SERIAL_REQUIRED | tests depend on 001–006 behavior |
| 5 | TASK-008 | SERIAL_REQUIRED | sole writer of a fresh immutable run root |
| 6 | TASK-009 | SERIAL_REQUIRED | bundle freeze must precede review read |
| 7 | TASK-010 | SERIAL_REQUIRED | final seal; single writer on `STATUS.md`, `directive-policy.json`, audit doc |

Concurrency: 3 agents in Wave 1, 2 in Wave 2, single-owner thereafter. Waves 3–7 are serial on the
critical path and gain nothing from added parallelism.

### 5.1 Integration ordering hazard (hash cascade)

TASK-005 mutates `directive-policy.json`, which binds SHA-256 digests of `GAMEPLAN-v2.md`,
`STATUS.md` and `CONTEXT-v2.md`. `STATUS.md` is *also* written by TASK-010. The plan mitigates the
cascade for TASK-005 only, which is insufficient.

Hard gate: no wave boundary may pass while

```
python3 -m coordination.context_contract --task development --phase plan --validate-only
```

is failing. TASK-010 must re-derive the cascade a second time after audit sign-off.

---

## 6. Agent roster and minimal-context briefs (§5, §6)

| Protocol role | Route (`model-policy.json`) | Scope |
|---|---|---|
| Implementation Agent | `development` (gpt-5.4) | TASK-001..007 |
| Code Review Agent | `independent_review` (Astra, high) | after every task |
| Test & Reliability Agent | `rehearsal_Verify_Gate` (Astra, high) | Wave 4 |
| Integration Agent | `planner_orchestrator` | wave boundaries |
| Security Review Agent | conditioned on §14 gates | TASK-002, TASK-008 |
| Architecture Review Agent | triggered per §13 criteria | TASK-002 (adapter boundary), TASK-003 (new module) |

Brief shape — exactly these ten fields, nothing else:

```
Role / Task (id + contract version) / Objective / Constraints / Depends on /
Write scope / Protected files / References / Acceptance / Verification + reporting
```

Returns use the ten §6 result fields (task id, contract version, role, baseline, outcome, changed
files, patch reference, commands + observed results, findings, deviations, blockers, evidence path).
No transcripts.

---

## 7. Review gates by risk class (§10)

| Tasks | Class | Gate |
|---|---|---|
| TASK-005, 007, 009, 010 | CRITICAL | independent review + governance validation + recovery-path verification |
| TASK-001, 003, 004, 006, 008 | HIGH | correctness + specialized review + negative-path testing + integration verification |
| TASK-002 | HIGH | legacy `Engine` import compatibility → mandatory negative import test |

AUDIT-01 gate (non-negotiable): the reviewer must not share the implementer's route, must run in a
fresh narrow context bound by `context_contract.py`, and must recompute its verdict from the frozen
bundle. A reviewer that has seen the implementation transcript is, by this project's own standard,
synthetic — and would reintroduce AUDIT-01.

---

## 8. Authorization boundaries (§14)

Gates: `gameplay_authorized: false`, `live_model_calls_authorized: false`,
`network_access_authorized: false`.

- Waves 1–5 are fully inside authorization (deterministic kernel, contracts, local tests, offline fresh run).
- **Wave 6 / TASK-009 sits on the boundary.** It invokes an external Astra review while
  `live_model_calls_authorized: false`. Resolution required before dispatch: either the directive
  `remediation_rerun_and_decision_delegation` explicitly extends to reviewer invocation (cite the
  ledger line), or TASK-009 stops and reports the approval needed. Authorization is not to be assumed.
- TASK-008 stays strictly offline: `model_calls: 0`, `provider_calls: 0` (DECISION-03).

---

## 9. Repair, integration, persistence, compaction (§11, §12, §15, §16)

- **Repair:** classify → reproduce → targeted fix → re-verify → re-review. Maximum 3 iterations per
  defect, then independent diagnosis (root cause, failed assumption, constraint, whether the contract
  itself needs revision). Forbidden: relaxing the 46 oracles, trimming AUDIT regression tests, or
  hand-setting a readiness predicate.
- **Integration:** per wave, never deferred to the end. Order: TASK-005 cascade → dependent task →
  context-contract validation → baseline tripwire digest → accept.
- **State:** single writer `REMEDIATION-STATE.md`; `directive-policy.json` ledger is append-only;
  historical contract revisions are never rewritten.
- **Checkpoint fields** at each wave boundary: verified baseline SHA, completed task IDs, active
  assignments, blockers, pending integrations, next eligible tasks, evidence paths.

---

## 10. Instantiating the EXECUTION DIRECTIVE

> Reconcile findings B-1..B-4. Establish the §3.1 baseline commit containing all work through the
> remediation plan, tag it, record its SHA in `00_CONTEXT.md`. Then dispatch Wave 1
> (TASK-001 ‖ TASK-003 ‖ TASK-005) as three isolated implementation agents under ten-field briefs,
> each confined to its declared write scope. Review each result independently against code and
> evidence, never summaries. At every integration boundary run the context-contract validator and
> re-verify the baseline tripwire digest. Continue Waves 2–7 without asking permission between waves.
> Stop at the Wave 6 authorization boundary unless the Astra route is explicitly authorized in the
> directive ledger. Declare SUCCESS only when all six readiness predicates are mechanically true and
> `INDEPENDENT-REVIEW.json` reports `READY`; otherwise report BLOCKED or INTERRUPTED — never as success.

---

## 11. Baseline commit procedure (protocol §3.1)

Executed once, before any task plan revision or task dispatch.

```
cd /home/anindyasundar-bera/Projects/hackathon/TwitchConOdyssey

git add -A
git status --short                 # confirm no secrets / runtime output staged
git commit -m "baseline: remediation plan v2.0 (rev 5 planning set, pre-construction)"
git tag plan-baseline/remediation-v2.0

BASELINE_SHA=$(git rev-parse HEAD)
echo "$BASELINE_SHA"               # paste into 00_CONTEXT.md and every task record
```

Guard conditions:

- `.env` is ignored; only `.env.example` may be committed.
- `__pycache__/`, `*.pyc`, `.runtime/` must not enter the baseline.
- The preserved rejected run is included as read-only history; its digest is re-verified afterward.
- If commit fails (identity, hooks, policy), the run is BLOCKED with the exact command and error.
- No amend, squash, rewrite or force-push may be used to obtain a cleaner baseline.

---

## 12. Projection findings to correct in the plan itself

1. **B-1 branch/baseline** — `main` not `master`; unborn HEAD resolved by the §3.1 gate.
2. **B-2 mis-scoped greenfield tasks** — TASK-001 and TASK-004 converge existing files; estimates and
   acceptance wording must be re-measured.
3. **Hash cascade at TASK-010** — mitigation must cover the second `STATUS.md` write, not only TASK-005.
4. **TASK-009 authorization** — unresolved conflict with `live_model_calls_authorized: false`.
5. **Manifest count** — §9 states TASK-010 seals "RUN-MANIFEST.json (116 entries)", which is the
   *rejected* run's 115 + 1. A remediated run emits 46 scenarios × (`.commands.jsonl` + `.trace.jsonl`)
   = 92 files plus matrix, packet, readiness and manifests. The count must be derived, never copied —
   otherwise AUDIT-05/AUDIT-09 recur.
6. **AUDIT-07 owning task truncated** as `TASK-01`; should be `TASK-010`. `DECISIONS.md` is listed
   twice in §11 of the report.
7. **Budget arithmetic** — 240 min critical path against a 270 min net ceiling leaves 30 min; the
   "120 minutes total buffer" mixes the 360 min gross figure with the net ceiling. State both
   consistently.

---

## 13. Resume instructions

If execution is interrupted, rebuild state from artifacts only, in this order:

1. `git rev-parse HEAD` — confirm the committed baseline still exists and matches `00_CONTEXT.md`.
2. `docs/planning/REMEDIATION-STATE.md` — last recorded wave and task outcomes.
3. `docs/planning/remediation-plan.json` — dependency graph and readiness predicates.
4. `python3 -m coordination.context_contract --task development --phase plan --validate-only` — governance integrity.
5. Digest re-check of the preserved rejected run — provenance integrity.

Then recompute eligible tasks and resume at the first incomplete wave.
