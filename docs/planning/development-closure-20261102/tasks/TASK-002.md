---
id: TASK-002
title: Resolve review-packet-hash discrepancy (D-H2)
workstream: W1
objective: O1
contract_version: v1.0
status: PLANNED
risk: CRITICAL
parallel: SERIAL
dependencies:
  hard: [TASK-001]      # shares the correction file; execute after TASK-001
  integration: []
  gates: [P]
owned_paths:
  - evidence/remediation-kernel-20261101/09_CORRECTIONS-20261102.md  (AMEND, append-only)
protected_paths:
  - artifacts/simulations/full-game/**
  - docs/planning/STATUS.md
  - config/directive-policy.json
execution_context:
  files:
    - artifacts/simulations/full-game/full-game-20261101T185524Z-2647e033/REVIEW-INVOCATION.json
    - artifacts/simulations/full-game/full-game-20261101T185524Z-2647e033/RUN-MANIFEST.json
    - artifacts/simulations/full-game/full-game-20261101T185524Z-2647e033/REVIEW-EVIDENCE.json  (hash only; content read permitted)
    - artifacts/simulations/full-game/full-game-20261101T185524Z-2647e033/REVIEW-PACKET.md
    - evidence/remediation-kernel-20261101/08_REVIEW.md
  commands_allowed: [sha256sum, grep, python3 json parse, git cat-file]
---

# TASK-002 — Resolve review-packet-hash discrepancy (D-H2)

## Established facts (re-verify; do not trust)

- Ledger `evidence/remediation-kernel-20261101/08_REVIEW.md:14` calls
  `648b8d080919ae843731646123aa4434a20675fe2ecff7c74cff40092193fb4b` the
  "Bound Review Packet SHA-256".
- Recomputed: `648b8d08...` is exactly the SHA-256 of the run's `REVIEW-EVIDENCE.json`
  (also listed under that name in `RUN-MANIFEST.json` and `REVIEW-PACKET.md`).
- The packet actually reviewed, per `REVIEW-INVOCATION.json` (`packet_hash` /
  `review_packet_sha256`) and sealed in `RUN-MANIFEST.json`, is
  `a9339b7cf897211bea5ca94f77a36942ab758a35f1e17d450caac09fb4697cca`; the invocation
  binds the same subagent conversation (`2d17a3bb-4dc0-4aab-a523-9808954b5762`),
  configured route (`codex_subagent`/`gpt-6-astra`/`high`), and verdict READY that
  the ledger records — so this is a **labeling error in the narrative ledger**, not an
  integrity failure of the review.

## Required output

Append **Correction C-2** to `09_CORRECTIONS-20261102.md`:

1. Quote the superseded ledger line (08_REVIEW.md:14) verbatim; do not modify
   `08_REVIEW.md` (its bytes stay historical; the ledger gains a correction record).
2. Record your own re-verification: exact `sha256sum` output for
   `REVIEW-EVIDENCE.json`; the `packet_hash` field values from
   `REVIEW-INVOCATION.json`; the manifest entry reference.
3. Corrected statement: the reviewed packet SHA-256 is `a9339b7c...`; `648b8d08...`
   is the `REVIEW-EVIDENCE.json` component digest.
4. Convention binding future reviews: human-readable review ledgers must bind the
   `packet_hash` (packet actually reviewed) from the invocation record, distinct from
   each evidence-component digest. This satisfies handoff §11 (reconciliation must
   close before any future review packet is sealed).
5. Before/after rejected-run tripwire values (unchanged, procedure as TASK-001).

## Acceptance criteria

- Append-only edit to the one owned file; all hashes reproduced from commands shown.
- No resolution claims a new review happened; record stays provenance-honest.
- `git status` otherwise clean.

## Compiler packet

As TASK-001 (task `development`, same owned path). Return per §14 format.
