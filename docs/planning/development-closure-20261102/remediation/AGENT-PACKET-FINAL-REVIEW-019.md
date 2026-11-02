# Agent packet — final review invocation 019

Task: independently review the unchanged candidate for offline development
closure and report whether the configured reviewer route is satisfied, using
only route metadata available to you. Do not infer serving model/effort from the
request unless the execution environment provides that as actual metadata.

Before review, compile fresh `plan_review/plan` and bind the output files
`FINAL-REVIEW-019.md`, `.json`, and `FINAL-REVIEW-019-INVOCATION.json`. Stop on
compiler rejection, stale binding, or identity mismatch. Read A/B reports and
`REVIEW-PACKET-018.md`; independently assess R1–R5 and verify candidate/diff and
sealed-root before/after. Try codebase-memory first; if unavailable, disclose
and inspect source.

Candidate base `bb02cea7e1c260eb30ea9491e7759761c0f290d4`; tracked diff SHA-256
`c215b22a8735e15a88a38d6a64f7d7f9234729ef2db3af394b1b2a233f2420bd`;
review packet SHA-256
`90dc0ab37f3444a0bfdc26c638198d010956921f85f742f7c22aa1c0737336bb`.
Configured route: `codex_subagent / gpt-6-astra / high`.

No files owned by you. Return <=250 words with verdict, R1–R5 findings, actual
route evidence and limits, candidate/packet/tripwire checks. Do not edit, commit,
run prohibited behavioral suites, server/replay/browser/harness/live services or
network calls. `submission_ready=false`; external capture remains unresolved.
