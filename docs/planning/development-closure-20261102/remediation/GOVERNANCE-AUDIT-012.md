# Governance audit — candidate 012

The current base HEAD, diff SHA, review-packet SHA, ledger revision 14, and simulator binding match their expected values. The rejected sealed root matches its 116-file count and tree hash.

- Base HEAD: `bb02cea7e1c260eb30ea9491e7759761c0f290d4`
- Tracked diff SHA-256: `3df90ab5f142192abf9c8448d9a891b4eae6729be1a1f1d2b5101c95cf15615a`
- Review packet SHA-256: `16a8aa0310ac9248e00e5bb415bc3b8dca0cab479df19c9e7ca521f8c3f9a8ff`
- Ledger: revision 14; simulator binding `1a6c55e1cbca0cf895025eb999ca14f56ce47c32ce9a2a7945b5545c9f51fda2`
- Readiness: `submission_ready=false`; `live_submission_external_capture` unresolved.
- Route history: configured `codex_subagent/gpt-6-astra/high`; prior invocation substituted requester-supplied Google DeepMind (Antigravity)/Gemini 3.8 Flash/high, so `configured_gate_satisfied=false`; one invocation.
- Prior READY review hashes `44c6cd…` / `10e9be…` do not cover this candidate.
- Rejected root: 116 files, SHA-256 `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d`.

The current candidate is ready for a new independent final review. No prohibited actions were performed.
