---
id: TASK-001
title: Resolve evidence/commit-hash discrepancy (D-H1)
workstream: W1
objective: O1
contract_version: v1.0
status: PLANNED
risk: CRITICAL
parallel: SERIAL
dependencies:
  hard: []
  integration: []
  gates: [P]
owned_paths:
  - evidence/remediation-kernel-20261101/09_CORRECTIONS-20261102.md  (CREATE; exclusive until TASK-002)
protected_paths:
  - artifacts/simulations/full-game/**
  - docs/planning/STATUS.md
  - config/directive-policy.json
execution_context:
  files:
    - evidence/remediation-kernel-20261101/00_CONTEXT.md
    - evidence/remediation-kernel-20261101/01_EVIDENCE_INDEX.md
    - docs/planning/development-closure-20261102/00_CONTEXT.md  (§2 facts table, verified outcomes)
  commands_allowed: [git log, git cat-file -t, git show, sha256sum, grep]
---

# TASK-001 — Resolve evidence/commit-hash discrepancy (D-H1)

## Assignment

The external delivery report recorded evidence commit
`cee6d79a295c589b4e36d4b29f79b764c243ebcf`. That object **does not exist** in the
checkout (`git cat-file -t` fails) and the string appears in no committed artifact.
Actual chain: baseline `0557baadd468b1a0405477d058662c91965542b0` → remediation
`99aa1c9f773887f5fc0a5529691d068e3eecda18` → evidence commit
`cee6d79036b80afd4bd3f5db62c5733283d29e58` → delivery-report commit
`a55794600b02c8f71f9dd33ebd88b8007e223c71` (current HEAD).

## Required output

Create `evidence/remediation-kernel-20261101/09_CORRECTIONS-20261102.md` containing:

1. Purpose statement: correction trail; superseded statements preserved verbatim,
   never erased; sealed run roots untouched.
2. **Correction C-1**: quote the superseded statement (`cee6d79a295c...` as evidence
   commit), state the verified resolution evidence (exact `git cat-file -t` outputs
   for both the wrong and the real hashes, run by you, recorded verbatim), and give
   the corrected chain with all four SHA-256s and commit titles.
3. Statement that the wrong hash is a transcription error with no corresponding git
   object; no tree/history modification is implied or permitted.
4. The canonical tree-hash procedure reference for reuse by TASK-003.

## Acceptance criteria

- File exists; superseded statement quoted verbatim; corrected values match
  `git cat-file`/`git log` output reproduced in the record with commands shown.
- No other repository file modified. `git status` shows exactly one new untracked
  path (the output file) until committed by the orchestrator.
- Rejected-run tripwire re-verification (procedure in 01_ARCHITECTURE.md §4) run
  before and after; both values `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d`; record in the output file.

## Compiler packet

`python3 -m coordination.context_contract --task development --phase plan \
  --owned-path evidence/remediation-kernel-20261101/09_CORRECTIONS-20261102.md`

Rejection ⇒ stop, record verbatim in your return. Return ≤250 words + owned paths,
per §14 return format (owned paths changed; findings; commands run; hashes;
unresolved items; sealed-run confirmation with before/after tripwire values).
