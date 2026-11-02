# Agent packet A — implementation audit 018 (read-only)

Compile fresh `planner_orchestrator/plan`; stop if rejected/stale. Try
codebase-memory first; if unavailable, disclose and use read-only source review.

Candidate base `bb02cea7e1c260eb30ea9491e7759761c0f290d4`; diff SHA-256
`c215b22a8735e15a88a38d6a64f7d7f9234729ef2db3af394b1b2a233f2420bd`.
Review packet `REVIEW-PACKET-018.md`; verify digest locally.

Recheck R1–R5. For R1, confirm a committed uncountered active hazard renders as
active while active, and the packaged runtime source assertion matches the
actual canonical event source. Review the full relevant implementation for
regressions. R2 leave/quorum; R3 atomicity, bounds, generations and persistence;
R4 fixture-only runtime/provenance and no external provider path; R5 exact
artifact coverage and documented package output.

No files owned. Do not edit/commit, run server/replay/browser/harness/live
service/network, or prohibited behavioral suites. Return <=250 words with
candidate hash, R1–R5 pass/fail, source lines, checks, and unresolved issues.
