# Agent packet B — governance/evidence audit (read-only)

Task: independently verify remediation closeout identity and governance facts.

Before inference, compile a fresh local packet with
`python3 -m coordination.context_contract --task development --phase plan`.
Read emitted directives/gate; stop on rejection or stale bindings.

Verify, without editing: candidate base HEAD and tracked diff hash; review packet
hash; ledger revision 14 and simulator binding; invocation record configured vs
actual route and `configured_gate_satisfied`; current `submission_ready` and
`live_submission_external_capture` state; rejected-root file count/tree hash;
review evidence says READY and addresses R1–R5. Expected candidate diff SHA-256
is `e3a7e4e5e9573f383dfa82d6be816d372bde426e584aa0e6d02f0676930c89e0`;
review packet is `REVIEW-PACKET-015.md`, SHA-256
`98a7e7b7452d2c349fae9333ea3234964341cd066a2374d85c4c15810d8c28ff`.
Verify ledger revision 14 and the engine/context-test bindings.

Ownership: no files. Do not edit, commit, run prohibited gameplay/runtime actions,
or modify sealed artifacts. Report at most 250 words with each expected/observed
value and any discrepancy. Do not infer external submission readiness.
