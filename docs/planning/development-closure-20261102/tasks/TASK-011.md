---
id: TASK-011
title: Independent final review (read-only plus review output)
workstream: W8
objective: O3
contract_version: v1.0
status: GATED
risk: HIGH
parallel: TERMINAL
dependencies:
  hard: [TASK-006, TASK-007, TASK-008, TASK-009, TASK-010]
  integration: []
  gates: [G-A]
review_route: {task: plan_review, provider: codex_subagent, model: gpt-6-astra, effort: high}
owned_paths:
  - docs/planning/development-closure-20261102/review/FINAL-INDEPENDENT-REVIEW.md      (CREATE)
  - docs/planning/development-closure-20261102/review/FINAL-INDEPENDENT-REVIEW.json    (CREATE)
  - docs/planning/development-closure-20261102/review/FINAL-REVIEW-INVOCATION.json     (CREATE)
protected_paths:
  - "** (read-only except owned_paths)"
execution_context:
  consumes:
    - evidence/remediation-kernel-20261101/09_CORRECTIONS-20261102.md
    - evidence/remediation-kernel-20261101/10_RUN-ROOT-DISPOSITION-20261102.md
    - docs/planning/development-closure-20261102/verification/DEVELOPMENT-CLOSURE-VERIFICATION.md
    - W3–W7 completion evidence (manifests, test records, review verdicts per package)
    - artifacts/simulations/full-game/full-game-20261101T185524Z-2647e033/** (read-only)
---

# TASK-011 — Independent final review

## Gates and route discipline

- Executes ONLY at the final independent-review gate, after W3–W7 completion
  evidence exists and G-A gameplay authorization scope covers the reviewed work.
- Invoked ONCE through the configured `plan_review` boundary
  (`codex_subagent` / `gpt-6-astra` / `high`) — never for implementation assistance
  (directives `model_allocation`, `manual_escalation`; handoff §11).
- **Recording convention (from Correction C-2):** `FINAL-REVIEW-INVOCATION.json`
  must bind the SHA-256 of the packet actually reviewed as `packet_hash`, distinct
  from every evidence-component digest; reviewer model/effort/provider recorded
  separately from configured; `configured_gate_satisfied` true only when the serving
  reviewer matches the configured route with no substitution.

## Assignment

1. Assemble the review packet: closure verification record, correction/disposition
   artifacts, W3–W7 evidence manifests, and readiness records — all read-only.
2. Invoke the configured review boundary once; propagate failure (no retry without
   human escalation per `manual_escalation`).
3. Write the three owned artifacts: markdown review (verbatim reviewer text),
   structured JSON verdict, and the invocation record.
4. Append-only state update path: report via your §14 return; you do not edit
   STATUS.md, the ledger, `03_EXECUTION_STATE.md`, or any task contract.
5. Pre/post rejected-run tripwire verification recorded in your return.

## Acceptance criteria

- Review output paths exactly as owned; nothing else written.
- Verdict propagates exactly as returned (READY / NOT-READY / conditional); a
  non-READY verdict blocks submission-readiness work, never W1–W2 history.
- Sealed roots verified byte-unchanged before and after.
