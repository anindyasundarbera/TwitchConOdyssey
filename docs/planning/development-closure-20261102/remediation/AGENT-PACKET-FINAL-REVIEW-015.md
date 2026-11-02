# Agent packet C — final independent review

You are the independent final reviewer after audit packets A and B complete.
First compile a fresh packet for the registered `plan_review` task, phase `plan`,
and bind every review output path you own. Read the compiled directives/gate and
stop on any rejection, stale binding, or candidate mismatch.

Review TASK-012-R1-R5 and all five original findings. Read
`IMPLEMENTATION-AUDIT-015.md`, `GOVERNANCE-AUDIT-015.md`, and
`REVIEW-PACKET-015.md`. Target candidate base
`bb02cea7e1c260eb30ea9491e7759761c0f290d4` plus tracked diff SHA-256
`e3a7e4e5e9573f383dfa82d6be816d372bde426e584aa0e6d02f0676930c89e0`. Target
review packet SHA-256
`98a7e7b7452d2c349fae9333ea3234964341cd066a2374d85c4c15810d8c28ff`. Read the
saved A/B reports and project review packet. Use codebase-memory first for code
structure. Independently inspect R1 authoritative server/HUD wiring, R2 leave
semantics, R3 concurrency/bounds, R4 provenance, and R5 reproducibility/evidence
coverage. Verify candidate identity and sealed-root tripwire before and after.

No repository files are owned by the reviewer; return the verdict only. The
orchestrator records the response at `FINAL-REVIEW-015.md`, `.json`, and
`FINAL-REVIEW-015-INVOCATION.json` after binding those paths in a fresh packet.

Configured route: `codex_subagent / gpt-6-astra / high`. Record actual provider,
model, effort, invocation count, packet hash, candidate hash, and whether the
configured route was satisfied. Return READY only if every criterion passes;
otherwise NOT-READY with severity and file/line evidence.

Do not edit implementation, commit, or run server/replay/browser/harness/live
services/network, deployment, capture, or submission. Honor AGENTS.md's allowed
test boundary: context-contract, routing, rehearsal and pure deterministic-kernel
checks only; do not run gameplay, intake, runtime, HUD, or package test suites.
No submission-readiness claim: `submission_ready` remains false and the live
external-capture decision is a separate gate.
