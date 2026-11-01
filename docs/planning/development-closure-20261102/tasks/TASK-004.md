---
id: TASK-004
title: Development-closure verification record (handoff §7)
workstream: W2
objective: O2
contract_version: v1.0
status: PLANNED
risk: HIGH
parallel: SERIAL_REQUIRED
dependencies:
  hard: [TASK-001, TASK-002, TASK-003]
  integration: []
  gates: [P]
owned_paths:
  - docs/planning/development-closure-20261102/verification/DEVELOPMENT-CLOSURE-VERIFICATION.md  (CREATE)
protected_paths:
  - artifacts/simulations/full-game/**
  - docs/planning/STATUS.md              (TASK-005 only)
  - config/directive-policy.json         (TASK-005 only)
execution_context:
  files:
    - evidence/remediation-kernel-20261101/09_CORRECTIONS-20261102.md
    - evidence/remediation-kernel-20261101/10_RUN-ROOT-DISPOSITION-20261102.md
    - evidence/remediation-kernel-20261101/10_RUN-ROOT-HASHES-20261102.json
    - evidence/remediation-kernel-20261101/01_EVIDENCE_INDEX.md
    - evidence/remediation-kernel-20261101/03_TEST_EVIDENCE.md
    - evidence/remediation-kernel-20261101/04_INVARIANT_EVIDENCE.md
    - evidence/remediation-kernel-20261101/05_REPLAY_PARITY.md
    - artifacts/simulations/full-game/full-game-20261101T185524Z-2647e033/DEVELOPMENT-READINESS.json
    - artifacts/simulations/full-game/full-game-20261101T185524Z-2647e033/SOURCE-BINDINGS.json
    - artifacts/simulations/full-game/full-game-20261101T185524Z-2647e033/INVARIANT-RESULTS.json
    - artifacts/simulations/full-game/full-game-20261101T185524Z-2647e033/results/SCENARIO-RESULTS.jsonl
  commands_allowed:
    - git cat-file -t / git log            (commit resolution)
    - sha256sum / canonical tree hash      (evidence hashing; read-only)
    - python3 -m unittest tests.test_context_contract tests.test_deterministic_kernel \
        tests.test_plan_rehearsal tests.test_model_router -v   (permitted static/kernel suites)
    - python3 -m coordination.context_contract --task development --phase plan --validate-only
  commands_forbidden: [test_full_game_simulation, server.app, server.replay, harness.run, browser gameplay, network]
---

# TASK-004 — Development-closure verification record

## Assignment

Produce the O2 gate record mapping every handoff §7 criterion to artifact-and-hash
evidence. **Reconcile; do not re-execute gameplay/simulation evidence.** Permitted
live checks are only the static/kernel suites above (new framework evidence, not
gameplay evidence) and read-only hashing.

Record, per §7 item 1..9, one line: VERIFIED / OPEN, the cited artifact path(s),
SHA-256 digest(s) recomputed by you, and the reconciling note. Required mappings:

1. Commits `0557baa...`, `99aa1c9...`, `cee6d790...`, `a557946` resolve
   (`git cat-file -t` output inline).
2. Kernel purity → kernel module binding + purity tests in `03_TEST_EVIDENCE.md`;
   `coordination/deterministic_kernel.py` file digest.
3. Dual consumers (`server/engine.py`, `coordination/full_game_simulator.py`) →
   dual-consumer/SDC binding evidence + both file digests.
4. Invariant structure → `INVARIANT-RESULTS.json` (19 results, 6 pipeline kinds)
   recomputed digest; scenario-vs-pipeline separation note.
5. Counts 99 / 46 / 31 → `03_TEST_EVIDENCE.md` total row; 46 lines of
   `SCENARIO-RESULTS.jsonl` (`wc -l` output) + its digest
   (`2b85d3eb...` per readiness record — re-verify); 31-key `SOURCE-BINDINGS.json`
   parse output.
6. Historical run unchanged → TASK-003 baseline digests + pre/post tripwire from
   this task's own run of the procedure.
7. New run internal agreement → manifest/bindings/`REVIEW-INVOCATION`/`READINESS`
   digests + Correction C-2 citation (reviewed packet = `a9339b7c...`).
8. Readiness separation → `DEVELOPMENT-READINESS.json` fields verbatim +
   digest `1e3b45d8...` (re-verify).
9. Root disposition → cite TASK-003 artifacts + "0 untracked roots" verification.

Close with: either "CLOSURE CANDIDATE: all §7 items VERIFIED" or the explicit OPEN
list (closure may not be declared over open items). Also state explicitly that the
existing run `full-game-20261101T185524Z-2647e033` remains sufficient simulation
evidence unless any verification failed (handoff §9.4 triggers only on failure or
development change), and that this record does not authorize any rerun.

## Acceptance criteria

- All nine items have evidence lines with recomputed digests, or explicit OPEN items.
- Permitted test suite results appended verbatim (pass counts), labeled
  "static/kernel framework checks, not gameplay evidence".
- Pre/post rejected-run tripwire = `411de729...` recorded.
- Only the owned file created.

## Compiler packet

`python3 -m coordination.context_contract --task development --phase plan \
  --owned-path docs/planning/development-closure-20261102/verification/DEVELOPMENT-CLOSURE-VERIFICATION.md`

Return per §14 format.
