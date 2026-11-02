# Agent packet C — final independent review 018

Begin only after candidate-018 A/B reports pass. Compile fresh
`plan_review/plan` and bind the three final review output paths before any
review; read directives/gate and stop on rejection, stale binding or candidate
mismatch. Read `IMPLEMENTATION-AUDIT-018.md`, `GOVERNANCE-AUDIT-018.md`, and
`REVIEW-PACKET-018.md`. Independently review R1–R5, confirm candidate identity,
and recompute sealed-root tripwire before/after using
`coordination.evidence_pipeline.compute_tree_sha256`.

Base HEAD `bb02cea7e1c260eb30ea9491e7759761c0f290d4`; diff SHA-256
`c215b22a8735e15a88a38d6a64f7d7f9234729ef2db3af394b1b2a233f2420bd`;
`REVIEW-PACKET-018.md` SHA-256
`90dc0ab37f3444a0bfdc26c638198d010956921f85f742f7c22aa1c0737336bb`.
Tripwire root `artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043`,
116 files, expected tree SHA-256
`411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d`.

No files owned by reviewer. Orchestrator saves verdict. Configured route:
`codex_subagent / gpt-6-astra / high`; record actual evidence and do not claim
gate satisfaction if serving metadata is unavailable. No prohibited behavioral
tests, runtime/server/replay/browser/harness/live services/network, edits,
commit, capture, publication or submission. `submission_ready=false`; external
capture remains unresolved. Return concise READY/NOT-READY with exact evidence.
