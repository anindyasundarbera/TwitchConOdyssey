# Agent packet C — final independent review 017

Start only after candidate-017 implementation and governance audits pass. Compile
a fresh `plan_review/plan` packet and bind review-output paths before review;
stop on rejection, stale binding, or candidate mismatch. Read
`IMPLEMENTATION-AUDIT-017.md`, `GOVERNANCE-AUDIT-017.md`, and
`REVIEW-PACKET-017.md`. Independently review R1–R5 and verify candidate identity
and sealed-root tripwire before and after. Try codebase-memory first; if it is
unavailable, disclose and inspect source.

Candidate base `bb02cea7e1c260eb30ea9491e7759761c0f290d4`; diff SHA-256
`34867262701d01afbdd49d76cdfad95ac5d42c45387bbf329e5d385f1580bae3`.
Verify review-packet SHA-256 locally. The reviewer owns no repository files;
orchestrator saves the verdict and invocation records. Configured route is
`codex_subagent/gpt-6-astra/high`; record actual route and do not assert gate
satisfaction without evidence. No prohibited behavioral tests, server/replay/
browser/harness/live service/network, commit, publication, or submission.
`submission_ready=false`; external-capture decision remains separate. Return
READY or NOT-READY with precise evidence; no broad session history.
