# Final independent review — candidate 012

The reviewer response is recorded verbatim below.

---

**NOT-READY for offline development closure.**

- **BLOCKER, R1:** Shipped client lacks steering controls, command submission, and command-status feedback: `client/index.html:18–47`, `client/app.js:65–116`. This fails `tasks/TASK-007.md:43–49`; canonical state display alone does not complete W4.
- **MAJOR, R1:** `server/app.py:72–86,111–118` stamps asynchronous results with the current tick/turn without rechecking their original round or deadline. A delayed result can therefore enter a later turn, violating D-05 expiration/no-rollover requirements.
- **MAJOR, R2:** `server/intake.py:91,118` initializes `_joined` empty and rejects leave unless intake previously registered that subject. Linked subjects already present in the engine’s initial roster cannot leave through this adapter.
- **MAJOR, R5:** Fresh-checkout reproduction required by `tasks/TASK-010.md:59` remains unverified for this candidate. Restricted behavioral suites were not run.

R3 locking/cardinality bounds and R4 fixed false live-participation labels are improved; these do not resolve the above failures.

Checks: fresh compiler accepted; saved audits and candidate source inspected; `git diff --check` passed; no edits or behavioral tests.

Before/after identities match:

- Base: `bb02cea7e1c260eb30ea9491e7759761c0f290d4`
- Diff: `3df90ab5f142192abf9c8448d9a891b4eae6729be1a1f1d2b5101c95cf15615a`
- Review packet: `16a8aa0310ac9248e00e5bb415bc3b8dca0cab479df19c9e7ca521f8c3f9a8ff`
- Sealed root: 116 files; `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d`
- Compiler packet: `f0c106db8a2dec712ee7d64eb1cad1a25d6cacf919c1f45cce3cef514a094d59`

Provider: `codex_subagent`; invocation count: **1**. Orchestrator confirms spawn-specified `gpt-6-astra/high`; actual serving model/effort are not independently observable, so configured-route satisfaction is **unverified**.

Owned artifacts: none. `submission_ready=false`; `live_submission_external_capture` remains unresolved.
