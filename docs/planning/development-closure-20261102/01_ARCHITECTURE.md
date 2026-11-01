# 01_ARCHITECTURE — Gated Objectives, Workstreams, and Dependency Structure

Namespace `development-closure-20261102`. All task contracts live under `tasks/` and
are indexed by `02_TASK_INDEX.md` / `task_manifest.yaml` (which must never contradict).

## 1. Gated Objectives

- **O1 — Evidence & ledger reconciliation.** A corrected, provenance-consistent ledger
  exists as new artifacts; D-H1/D-H2 resolved with evidence; untracked-root disposition
  policy-backed and recorded; sealed roots provably unchanged (before/after hashes).
- **O2 — Deterministic-kernel development closure.** Closed only when all 9 handoff §7
  criteria are verified and recorded against artifact-and-hash evidence; open items
  block closure.
- **O3 — Final gameplay implementation planning.** Atomic task contracts for W3–W8
  exist, each explicitly gated; no execution-dependent work begins until (a) explicit
  user gameplay authorization is recorded in the directive ledger and (b) the executor's
  fresh compiler packet is accepted for its task and owned paths.

## 2. Workstreams and Ownership

| WS | Objective | Ownership | Parallel class | Risk |
|---|---|---|---|---|
| W1 | Ledger repair | `evidence/remediation-kernel-20261101/` new correction/disposition artifacts ONLY; never edit existing ledger or sealed run roots | SERIAL (single exclusive file sequence) | CRITICAL (evidence integrity) |
| W2 | Development closure | `docs/planning/development-closure-20261102/verification/` new files; `docs/planning/STATUS.md` + `config/directive-policy.json` (exclusive, single transaction) | SERIAL_REQUIRED | CRITICAL |
| W3 | Gameplay core | `server/engine.py`; `coordination/deterministic_kernel.py` (provisional, index-gated) | GATED | HIGH |
| W4 | Presentation/HUD | `client/` paths (provisional, index-gated) | GATED | MEDIUM |
| W5 | Twitch linking/intake | Adapter paths (provisional, index-gated) | GATED | HIGH (identity/security) |
| W6 | Booth telemetry | Telemetry paths (provisional, index-gated) | GATED | MEDIUM |
| W7 | Submission/demo pipeline | Submission tooling + `evidence/` docs (provisional, index-gated) | GATED | MEDIUM |
| W8 | Independent final review | Read-only; new review output only | TERMINAL | HIGH |

## 3. Dependency Graph (hard deps by stable ID)

```
TASK-001 (D-H1 correction) ─┐
TASK-002 (D-H2 correction) ─┤ depends TASK-001 (shared correction file, serial)
TASK-003 (root disposition + hash baseline, CRITICAL) ─┘ independent of 001/002
TASK-004 (§7 closure verification record) depends 001, 002, 003
TASK-005 (STATUS.md + ledger revision rebind) depends 004  [SERIAL, exclusive]
TASK-006..010 (W3–W7 gameplay implementation) depend 005 AND external gates:
   G-A explicit user gameplay authorization (new ledger directive)
   G-B fresh compiler-accepted packet per task
   G-C codebase-memory index available (else record blocker, stop)
TASK-011 (W8 final independent review) depends 006..010 evidence; terminal; consumes
   configured `plan_review` route (`codex_subagent`/`gpt-6-astra`/`high`) only.
```

First execution wave (assignable now): TASK-001, TASK-002, TASK-003 (W1), then
TASK-004, TASK-005 (W2). W3–W7 are contract-only until gates open; W8 is terminal.

## 4. Sealed-Root and Hash Conventions

- All 7 run roots under `artifacts/simulations/full-game/` are read-only sealed
  evidence. The rejected run `full-game-20261101T102226Z-a8e33043/` has the explicit
  non-modification mandate (authorization of 2026-11-01T17:36:28+05:30).
- Canonical tree hash: sort files by repo-relative path, build
  `<rel_path>:<sha256>\n` lines, SHA-256 the concatenation (rejected-run tripwire
  `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d`, 116 files).
  TASK-003 records before-hashes for all roots; every later wave boundary re-runs the
  same procedure and appends results to the W1 hash log (new evidence, never edits).
- Corrections preserve superseded statements verbatim with their corrections
  (correction trail, not rewrite). Readiness values are computed, never asserted.

## 5. Review Design

- W1/W2: provenance review + hash re-verification before/after (CRITICAL → independent
  verifier agent, not the author).
- W3–W7: correctness review for functional change; security review for identity,
  linkage, dedup, rate limits, secrets, participation rules; integrity review for
  evidence/telemetry artifacts. No author may sole-declare success.
- W8: configured `gpt-6-astra`/`high` route once at the final independent-review gate;
  its packet hash recording convention must follow `REVIEW-INVOCATION.json`
  (`packet_hash` = hash of the packet actually reviewed) so D-H2 never recurs.
- Gate failures are repairable without rebuilding unrelated workstreams (each WS writes
  only its owned paths; shared files only in TASK-005's single transaction).

## 6. What This Plan Explicitly Excludes

Gameplay execution/simulation reruns, service startup, deployment, live Twitch
integration, live credentials, external submission, publishing, sealed-root edits,
and any change to `submission_ready`. Any rerun (handoff §9.4) requires a new
exclusive run root and separate gating; the existing run
`full-game-20261101T185524Z-2647e033` stands as the current simulation evidence
unless closure verification invalidates its provenance (then stop, do not rerun
without authorization).
