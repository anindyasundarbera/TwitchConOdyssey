# Agent packet A — implementation audit (read-only)

Task: independently audit remediation findings R1–R5 for TASK-012.

Before any inference, compile a fresh local packet with
`python3 -m coordination.context_contract --task development --phase plan`.
Read emitted directives/gate. Stop on compiler rejection or stale source.

Candidate base: `bb02cea7e1c260eb30ea9491e7759761c0f290d4`. Expected tracked diff
SHA-256: `e3a7e4e5e9573f383dfa82d6be816d372bde426e584aa0e6d02f0676930c89e0`.
Review packet: `REVIEW-PACKET-015.md`; SHA-256
`98a7e7b7452d2c349fae9333ea3234964341cd066a2374d85c4c15810d8c28ff`.

Read the remediation review packet and inspect the implementation/tests for:
R1 canonical state HUD, usable fixture controls and durable feedback; R2 canonical
leave including initially rostered linked subjects; R3 atomic/bounded intake,
async expiry, pause/restart invalidation, and match-bound persistence; R4 fixture-only
provenance; R5 complete package hashing and clean-copy reproduction. Verify candidate hash before
and after. Use codebase-memory first for code structure.

Ownership: no files. Do not edit, commit, run server/replay/browser/harness/live
services/network calls, or alter sealed artifacts. Report at most 250 words:
candidate hash, pass/fail per R1–R5, concrete file/line evidence, checks
actually run, and unresolved issues. Do not declare final closure.
