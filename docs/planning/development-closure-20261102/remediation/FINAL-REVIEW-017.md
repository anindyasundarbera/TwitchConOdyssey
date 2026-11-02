**NOT-READY — candidate 017.**

- **R1 fails:** `client/hud.js:168` labels an active, uncountered hazard “resolved” whenever warning is false. The adjacent preview correctly reports an active obstacle, producing contradictory authoritative feedback. Also, `tests/test_runtime_integration.py:31` requires an unspaced literal absent from the formatted client source; this packaged assertion necessarily fails. Source inspection established both findings; no behavioral tests ran.
- **R2 passes static review:** linked initial-roster leave queues removal; current quorum remains frozen until the next turn.
- **R3 passes static review:** synchronized admission, bounded tracking, generation-aware pending removal, stale-result expiry, and captured match persistence are present.
- **R4 passes static review:** runtime constructs only `MockProvider`; constructor injection and CLI provider selection are absent. Runtime and telemetry retain fixture provenance.
- **R5 passes static review:** exact artifact coverage and digest checking are enforced; saved evidence reports 25 verified artifacts.

Compiler accepted, packet hash `1214a9eea9bc7718e298577f27df33e410adf73e65f489fc95fae6579fe386c1`. Configured route: `codex_subagent/gpt-6-astra/high`. Actual serving model/effort are not independently observable; configured-route satisfaction is not established.

Candidate base, diff, and review-packet hashes matched before/after. Tripwire matched before/after: 116 files, `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d`. Diff hygiene passed. Codebase-memory reported the requested project unindexed; direct source inspection followed.

No files changed or prohibited execution occurred. `submission_ready=false`; external capture remains unresolved.
