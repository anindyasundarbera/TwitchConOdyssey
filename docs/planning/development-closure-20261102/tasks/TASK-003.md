---
id: TASK-003
title: Run-root disposition policy and sealed hash baseline
workstream: W1
objective: O1
contract_version: v1.0
status: PLANNED
risk: CRITICAL
parallel: PARALLEL_SAFE (distinct new files; W1 agent executes serially with 001/002)
dependencies:
  hard: []
  integration: []
  gates: [P]
owned_paths:
  - evidence/remediation-kernel-20261101/10_RUN-ROOT-DISPOSITION-20261102.md  (CREATE)
  - evidence/remediation-kernel-20261101/10_RUN-ROOT-HASHES-20261102.json      (CREATE)
protected_paths:
  - artifacts/simulations/full-game/**   (READ-ONLY; hashing is permitted, writing never)
  - docs/planning/STATUS.md
  - config/directive-policy.json
execution_context:
  files:
    - docs/planning/00_CONTEXT.md            (B-4 tripwire, canonical tree-hash method)
    - docs/planning/development-closure-20261102/00_CONTEXT.md  (§2, §3)
    - docs/planning/development-closure-20261102/01_ARCHITECTURE.md (§4 conventions)
  commands_allowed: [git status, git ls-files, git log, find, sha256sum, python3]
---

# TASK-003 — Run-root disposition policy and sealed hash baseline

## Established facts (re-verify)

- The handoff's "six untracked simulation run roots" claim is **stale**:
  `git status --porcelain -uall` at HEAD `a557946` is empty; all 7 run roots are
  tracked (six `2647e033` roots added by `a557946`; rejected run `a8e33043` by
  `2bb0b53`). They were untracked when the report was drafted.
- Rejected run tripwire (canonical sorted-tree SHA-256):
  `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d` (116 files).
- Historical-run reference: `full-game-20261101T174648Z-2647e033/` tree SHA
  `b79455d3eb63ae80002750f7ad673935cfb6249094f60935bb7e31892a7ccaa5`
  (from `01_EVIDENCE_INDEX.md` EV-005/EV-018; re-verify).

## Required outputs

1. `10_RUN-ROOT-DISPOSITION-20261102.md` — the evidence-management policy record:
   - Disposition per root (table, all 7): `tracked`, `sealed: true`,
     `mutable: false`, role (rejected-preserved / historical-reviewed /
     intermediate / current-evidence), adding commit.
   - Policy: run roots are immutable once sealed; corrections land only as new
     artifacts outside the roots; new simulation evidence requires a new exclusive
     run root (never reuse); removal/rewrite/reseal is forbidden absent explicit
     recorded authorization; git tracking is the distribution mechanism, not a
     mutability grant.
   - The stale untracked-roots claim and its verification (commands + empty output).
   - The repeatable verification procedure (exact command sequence producing the
     canonical tree hash) as the scheduled pre/post wave-boundary check for
     TASK-004/005/011.
2. `10_RUN-ROOT-HASHES-20261102.json` — machine-readable baseline:
   `{"procedure": "...", "timestamp": ..., "git_head": "...",
     "roots": {"<root>": {"file_count": n, "tree_sha256": "...", "sealed": true,
     "role": "..."}}, "verification": "before", "status": "unchanged-vs-records"}`
   Baselines recompute and must equal the recorded digests above (and the manifests'
   own digests where recorded); any mismatch ⇒ BLOCKED, record verbatim, stop.

## Acceptance criteria

- Both files present, internally consistent, JSON valid.
- Every root hashed with the canonical procedure; tripwire matches for `a8e33043`.
- Zero writes under `artifacts/`; `git status` shows only the two new files.

## Compiler packet

`python3 -m coordination.context_contract --task development --phase plan \
  --owned-path evidence/remediation-kernel-20261101/10_RUN-ROOT-DISPOSITION-20261102.md \
  --owned-path evidence/remediation-kernel-20261101/10_RUN-ROOT-HASHES-20261102.json`

Return per §14 format (include all 7 root hashes and the head SHA).
