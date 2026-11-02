# Agent packet C — final independent review

You are the independent final reviewer after audit packets A and B complete.
First compile a fresh packet for the registered `plan_review` task, phase `plan`,
and bind every review output path you own. Read the compiled directives/gate and
stop on any rejection, stale binding, or candidate mismatch.

Review TASK-012-R1-R5 and all five original findings. Read
`IMPLEMENTATION-AUDIT-013.md`, `GOVERNANCE-AUDIT-013.md`, and
`REVIEW-PACKET-013.md`. Target candidate base
`bb02cea7e1c260eb30ea9491e7759761c0f290d4` plus tracked diff SHA-256
`911a7480c27aa88df3a1de7c0856116bd3ba8b4a796c002965b503df00347c25`. Target
review packet SHA-256
`38d55c82292310cee1ea5c9d4407e80469522aa39a1bdbaecdf19bf2eaa62c81`. Read the
saved A/B reports and project review packet. Use codebase-memory first for code
structure. Independently inspect R1 authoritative server/HUD wiring, R2 leave
semantics, R3 concurrency/bounds, R4 provenance, and R5 reproducibility/evidence
coverage. Verify candidate identity and sealed-root tripwire before and after.

No repository files are owned by the reviewer; return the verdict only. The
orchestrator records the response at `FINAL-REVIEW-013.md`, `.json`, and
`FINAL-REVIEW-013-INVOCATION.json` after binding those paths in a fresh packet.

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
