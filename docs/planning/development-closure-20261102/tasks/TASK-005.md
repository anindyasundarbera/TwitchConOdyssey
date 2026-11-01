---
id: TASK-005
title: STATUS.md closure update and directive-ledger rebind
workstream: W2
objective: O2
contract_version: v1.0
status: PLANNED
risk: CRITICAL
parallel: SERIAL_REQUIRED
dependencies:
  hard: [TASK-004]
  integration: []
  gates: [P]
owned_paths:
  - docs/planning/STATUS.md                 (EDIT — exclusive; single transaction)
  - config/directive-policy.json            (EDIT — exclusive; same transaction)
protected_paths:
  - artifacts/simulations/full-game/**
  - evidence/remediation-kernel-20261101/** (append history only; owned by W1)
execution_context:
  files:
    - docs/planning/development-closure-20261102/verification/DEVELOPMENT-CLOSURE-VERIFICATION.md
    - docs/planning/STATUS.md
    - config/directive-policy.json          (revision 9 structure, required_paths, revision_note)
    - tests/test_context_contract.py        (ledger structural assertions)
  commands_allowed:
    - python3 -m unittest tests.test_context_contract tests.test_deterministic_kernel \
        tests.test_plan_rehearsal tests.test_model_router -v
    - python3 -m coordination.context_contract --task development --phase plan --validate-only
    - sha256sum, git diff
  commands_forbidden: [gameplay/simulation tests, server.app, server.replay, harness.run, browser, network]
---

# TASK-005 — STATUS.md closure update and directive-ledger rebind

## Why this is CRITICAL

`config/directive-policy.json` `required_paths` pins byte hashes of `STATUS.md` (and
`directive-policy.json` via self-consistency tests). Editing STATUS without a ledger
rebind makes every subsequent compiler packet fail closed. Both files therefore change
in one transaction, verified before completion.

## Assignment

Prerequisite: TASK-004 record says either "CLOSURE CANDIDATE" or lists OPEN items.
You record exactly what the evidence supports — closure only with zero open items.

1. **STATUS.md**: append/insert a dated record (do not rewrite history) stating:
   - development-closure verification outcome, citing the TASK-004 record digest and
     the correction artifacts (`09_CORRECTIONS-20261102.md`,
     `10_RUN-ROOT-DISPOSITION-20261102.md`, `10_RUN-ROOT-HASHES-20261102.json`);
   - the readiness separation unchanged: development readiness recorded, gameplay
     implementation workstreams GATED pending explicit user authorization
     (`gameplay_enabled: false`); `submission_ready: false` untouched;
   - the plan namespace `docs/planning/development-closure-20261102/` as the current
     closure plan, including its G-A/G-B/G-C gates;
   - NO new authorization granted; `remediation_rerun_and_decision_delegation`
     remains the only active runtime authorization.
2. **directive-policy.json**: bump `revision` to 10; update `required_paths` entries
   for every file whose bytes changed (at minimum `docs/planning/STATUS.md`); set
   `revision_note` describing the rebind (pattern: revision 9's note); make NO gate,
   task, decision, or gameplay changes. Do not add new tasks to the tasks map.
3. **Verify**: run the permitted suites + compiler `--validate-only`; both the new
   STATUS digest appearing in `required_paths` and static ledger assertions must
   pass. If any ledger-structure assertion encodes the old hash (check
   `tests/test_context_contract.py` conventions), STOP (test edits are out of scope
   — report as a follow-up decision rather than editing tests).

## Acceptance criteria

- `git diff` touches exactly the two owned files.
- Compiler `--validate-only` passes; permitted suites pass (output appended to your
  return summary; full logs may be referenced, not pasted).
- Pre/post rejected-run tripwire verified unchanged (both values recorded).
- STATUS text contains no claim that gameplay is implemented or authorized.

## Compiler packet

`python3 -m coordination.context_contract --task development --phase plan \
  --owned-path docs/planning/STATUS.md --owned-path config/directive-policy.json`

Return per §14 format (include new digests for both files and the new packet hash).
