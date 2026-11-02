# Agent packet C — final independent review

You are the independent final reviewer after audit packets A and B complete.
First compile a fresh packet for the registered `plan_review` task, phase `plan`,
and bind every review output path you own. Read the compiled directives/gate and
stop on any rejection, stale binding, or candidate mismatch.

Review TASK-012-R1-R5 and all five original findings. Read
`IMPLEMENTATION-AUDIT-012.md`, `GOVERNANCE-AUDIT-012.md`, and
`REVIEW-PACKET-20261102.md`. Target candidate base
`bb02cea7e1c260eb30ea9491e7759761c0f290d4` plus tracked diff SHA-256
`3df90ab5f142192abf9c8448d9a891b4eae6729be1a1f1d2b5101c95cf15615a`. Target
review packet SHA-256
`16a8aa0310ac9248e00e5bb415bc3b8dca0cab479df19c9e7ca521f8c3f9a8ff`. Read the
saved A/B reports and project review packet. Use codebase-memory first for code
structure. Independently inspect R1 authoritative server/HUD wiring, R2 leave
semantics, R3 concurrency/bounds, R4 provenance, and R5 reproducibility/evidence
coverage. Verify candidate identity and sealed-root tripwire before and after.

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
