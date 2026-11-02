# Completion plan — parallel closeout

Date: 2026-11-02  
Authorization: requester explicitly approved completion and delegation in the
current turn.  
Plan compiler packet: task `planner_orchestrator`, phase `plan`; owned paths
bound before creation.  
Current code candidate: base `bb02cea7e1c260eb30ea9491e7759761c0f290d4`, tracked
diff SHA-256
`e3a7e4e5e9573f383dfa82d6be816d372bde426e584aa0e6d02f0676930c89e0`.  
Current external readiness gate: `live_submission_external_capture` remains
unresolved; this plan closes offline development only.

## Parallel work packets

| Work | Owner | Packet | Scope / output |
|---|---|---|---|
| A — independent implementation audit | Read-only agent | `AGENT-PACKET-IMPLEMENTATION-AUDIT.md` | Re-check R1–R5 against the exact current diff, tests, and line evidence; return findings only. |
| B — governance and evidence audit | Read-only agent | `AGENT-PACKET-GOVERNANCE-AUDIT.md` | Verify packet/candidate hashes, ledger revision and gate separation, review route record, sealed-root tripwire; return mismatches only. |
| C — final independent review | Separate reviewer after A and B | `AGENT-PACKET-FINAL-REVIEW.md` | Compile `plan_review` ownership packet for new output paths, independently review exact candidate and A/B reports, issue READY/NOT-READY; no implementation edits. |

A and B run concurrently because their scopes and outputs do not overlap. C
starts only after both reports are returned and the candidate identity is
rechecked. If either audit finds a blocker, stop C, prepare a narrow correction
packet, then rerun A/B against the changed candidate before the final review.

## Gates and stop conditions

1. Every delegated agent receives only its saved packet, not conversation
   history, and must compile a fresh local packet before inference.
2. No agent may modify implementation, ledger, status, or sealed artifacts.
3. Final reviewer route must be the configured
   `codex_subagent / gpt-6-astra / high`; otherwise record the substitution and
   leave that configured gate unsatisfied.
4. Close offline development only on independent READY for the exact candidate.
   Do not set `submission_ready: true` or resolve the live external-capture
   decision from offline evidence.
5. The review packet hash, candidate diff hash, and 116-file rejected-root
   tripwire must match immediately before and after review.

## Recovery procedure

After a session restart, read this file and the three packet files, inspect
`COMPLETION-STATE-20261102.json`, query available agent status, and continue only
unfinished work. Verify each returned report against the exact candidate before
starting the final reviewer. Never assume a spawned agent finished merely
because its packet was dispatched.
