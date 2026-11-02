# Agent packet A — implementation audit 017 (read-only)

Compile fresh `planner_orchestrator/plan`; stop on rejection/stale bindings.
Try codebase-memory first. If transport is unavailable, state so and inspect
source read-only.

Candidate base `bb02cea7e1c260eb30ea9491e7759761c0f290d4`; tracked diff SHA-256
`34867262701d01afbdd49d76cdfad95ac5d42c45387bbf329e5d385f1580bae3`.
Review packet: `REVIEW-PACKET-017.md`; verify its digest locally.

Audit R1 canonical state/HUD and controls; R2 initial-roster leave and quorum;
R3 intake atomicity/bounds, async expiry, generation-safe pending IDs and
match-bound persistence; R4 fixture-only provenance and provider isolation,
especially confirming the CLI cannot select/inject a network provider; R5
hashed evidence coverage, reproducible build/check. No files owned. Do not edit,
commit, run server/replay/browser/harness/live services/network or prohibited
behavioral suites. Return <=250 words: hash, pass/fail R1-R5, file/line evidence,
checks run, unresolved issues. No closure claim.
