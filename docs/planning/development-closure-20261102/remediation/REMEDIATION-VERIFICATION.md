# Remediation verification

Status: IN PROGRESS

This record is append-only for the remediation wave defined in
`REMEDIATION-PLAN.md`. No success or closure claim exists until the exact
candidate, targeted verification, sealed-root tripwire, and fresh independent
review are recorded below.

## Candidate correction and re-audit — 2026-11-02

- Corrected R1: the old canvas/UI adapter fabricated integrity, squad winners,
  telemetry and chat-action affordances. The page now renders only canonical
  server state and server evidence; unsupported mock panels/actions were removed.
- Corrected R3: `AuthoritativeGame` serializes `submit` and `step` with one
  reentrant lock; intake holds that lock across identity/sequence/rate admission
  and engine dispatch. Identity registrations and receipt history remain bounded;
  per-subject sequence and accepted-tick history is retained without eviction.
- Corrected R5: package checks require the full declared artifact set, all
  work-package evidence declarations, valid SHA-256 syntax and matching bytes.
- Governance rebind: ledger revision 14 updates the `server/engine.py` binding
  and advances the static revision assertion; the previous note is retained.
  Staged candidate packet accepted (`f2eee75b…`); normal development compile and
  validate-only both passed at revision 14.
- Permitted checks: context-contract suite 24 passed; Python AST parsing, Node
  syntax check and `git diff --check` passed. Disallowed gameplay/intake/runtime/
  HUD/package behavioral suites are not acceptance evidence. Earlier narrow
  suite runs occurred before the explicit test boundary was re-read and are not
  relied on here.
- Current base: `bb02cea7e1c260eb30ea9491e7759761c0f290d4`; candidate tracked-diff
  SHA-256 `3df90ab5f142192abf9c8448d9a891b4eae6729be1a1f1d2b5101c95cf15615a`.
- Review packet hash and final verdict remain pending. Sealed rejected-root
  tripwire remains `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d`
  (116 files); `submission_ready=false`; `live_submission_external_capture`
  remains unresolved.

## Independent candidate audits — 2026-11-02

- Implementation audit `IMPLEMENTATION-AUDIT-012.md`: READY for offline
  development closure on static review; R1–R5 all pass. No tests run by auditor.
- Governance audit `GOVERNANCE-AUDIT-012.md`: base/diff/packet, revision 14,
  simulator binding, readiness gate, route history and sealed-root tripwire
  match. Prior READY review remains stale.
- Both audits bind candidate diff
  `3df90ab5f142192abf9c8448d9a891b4eae6729be1a1f1d2b5101c95cf15615a` and
  review packet `16a8aa0310ac9248e00e5bb415bc3b8dca0cab479df19c9e7ca521f8c3f9a8ff`.
- Final configured review is the remaining gate for offline development closure.

## Final review 012 result — 2026-11-02

- `FINAL-REVIEW-012.md`, `.json`, and `-INVOCATION.json` preserve the single
  configured-route review of candidate `3df90ab5…` / packet `16a8aa03…`.
- Verdict: NOT-READY. Findings: no controls or visible command feedback; async
  results can roll into a later phase/turn; intake cannot leave initial roster
  members; fresh-checkout reproduction unverified.
- The implementation wave now addresses controls/feedback, result expiry, and
  initial-roster leave. R5 receives a fresh-copy build/check reproduction.
- The review process was invoked once for this candidate; a new candidate needs
  its own independently packet-bound final review.

## Candidate correction wave 2 — 2026-11-02

- R1 restored visible accessible left/right controls wired to `/api/command`;
  the server translates them to `streamer.steer` commands with fixture provenance
  and returns status for the HUD's live-region feedback. The only UI state source
  remains the canonical state/evidence envelope.
- R1/R3 stale async provider results now expire on turn mismatch, phase close,
  terminal state, or 40 ticks (2 seconds) from dispatch. They are not retimed to
  the current turn.
- R2 leave no longer requires an in-memory prior `join`; the engine validates
  linked subjects already in the initial roster and stages valid leave for the
  next freeze.
- R5 fresh-copy documented build/check reproduced successfully in a temporary
  copy: 23 artifacts, manifest digest
  `4f8d5902dfbea50c03b542bb0abdcc4bce671df46dab1392d1cfa6eace2c5095`; check
  verified all 23. `submission_ready=false`.
- Static checks: context compiler/validation, allowed context-contract suite,
  Python AST, Node syntax, diff hygiene passed. Prohibited gameplay/intake/runtime/
  HUD/package behavioral suites remain unrun.
- Candidate base `bb02cea7e1c260eb30ea9491e7759761c0f290d4`; tracked diff SHA-256
  `911a7480c27aa88df3a1de7c0856116bd3ba8b4a796c002965b503df00347c25`; review
  packet 013 SHA-256
  `38d55c82292310cee1ea5c9d4407e80469522aa39a1bdbaecdf19bf2eaa62c81`.
- New independent A/B audits and final review are pending. The prior NOT-READY
  verdict is preserved in `FINAL-REVIEW-012.md`.

## Candidate correction wave 3 — 2026-11-02

- Candidate 013 implementation audit found that polling overwrote the command
  response before reliable reading. Candidate 014 sends command responses to a
  separate persistent `role=status` / `aria-live` region; connection polling no
  longer changes that feedback.
- Added operator pause/resume and terminal-only next-fixture control. Restart
  creates a fresh offline authoritative game, clears bounded queues, and tags
  provider work with a match identity so old results cannot cross into the new
  match.
- The candidate clean-copy package build/check was repeated after these client
  and runtime changes: 23 artifacts, manifest digest
  `3d67e5827de7b9af102addb1996f244ef6dd219f939a0c4f11f91abfed469604`; check
  verified all 23. No submission-readiness change.
- Allowed context-contract, syntax, Node syntax and diff-hygiene checks passed.
  Gameplay/intake/runtime/HUD/package behavioral suites remain unrun.
- Candidate base `bb02cea7e1c260eb30ea9491e7759761c0f290d4`; tracked diff
  `d2598828b97e632b4baffb611cf748d95ac80b530bbf727856ec2329a3572de7`; review
  packet 014 `649200dc1374ba0acec426415d46ba67f131280918274b0566e32a2d81a8f3d3`.
- Candidate 014 requires fresh A/B audits and final independent review.

## Candidate correction wave 4 — 2026-11-02

- Candidate 014 audit found a store append race at restart and async provider
  results surviving pause/resume. `Runtime.run()` now captures `record_match_id`
  under the lock for event/snapshot persistence. Queued provider work carries a
  generation token; accepted pause/resume and restart invalidate older work,
  pending identities are cleared, paused results expire, and match IDs remain in
  each job/result tuple.
- Allowed static checks passed after these fixes: compiler/validate-only,
  context-contract suite (24), AST parsing, Node syntax, and `git diff --check`.
- Clean-copy package reproduction after these changes: 23 artifacts, manifest
  digest `3d67e5827de7b9af102addb1996f244ef6dd219f939a0c4f11f91abfed469604`,
  check verified all 23.
- Candidate base `bb02cea7e1c260eb30ea9491e7759761c0f290d4`; diff
  `e3a7e4e5e9573f383dfa82d6be816d372bde426e584aa0e6d02f0676930c89e0`; packet
  015 `98a7e7b7452d2c349fae9333ea3234964341cd066a2374d85c4c15810d8c28ff`.
- New A/B audits and final independent review are pending. `submission_ready`
  remains false; live external capture remains unresolved.
- Candidate-015 governance audit passed: base/diff/packet hashes, revision-14
  bindings, 23-artifact clean-copy record and 116-file sealed-root tripwire match
  (see `GOVERNANCE-AUDIT-015.md`). Implementation audit is pending.
- Candidate 014 governance review caught a stale “ledger revision 13” sentence
  in its review packet. The sentence now says revision 14; the packet hash changed
  to `fdc7e08bcf879e10677cfea2caa41bcaad0c6ce820db0c29c6d7839e38b23498`, so A/B
  reviews must bind these corrected bytes before final review.

## Candidate correction wave 5 — 2026-11-02

- Candidate 016 implementation audit passed R1–R3 and R5, but found R4 allowed
  `server.app` to select `OpenAIProvider` via `--provider openai`, despite fixed
  fixture provenance and the no-network authorization boundary.
- Candidate 017 removes the external provider import and CLI selection, and
  removes provider injection from `Runtime`; the runtime uses only
  `MockProvider`. No service/network action was run.
- Permitted verification: context-contract suite 24 passed before this change;
  after change AST parsing, Node syntax, diff hygiene and package build/check
  passed. The package includes 25 artifacts; manifest SHA-256
  `f3bed45867670106668648ffbf2e7d142969eef07c0aea92aca2a71d2eb307a1`.
- Candidate base `bb02cea7e1c260eb30ea9491e7759761c0f290d4`; tracked diff
  `34867262701d01afbdd49d76cdfad95ac5d42c45387bbf329e5d385f1580bae3`;
  review packet `REVIEW-PACKET-017.md`. A/B audits passed; final independent
  review returned NOT-READY. `submission_ready=false`; external capture remains
  open.

## Final review 017 result — 2026-11-02

- `FINAL-REVIEW-017.md`, `.json`, and `-INVOCATION.json` preserve the
  independent NOT-READY verdict for candidate 017. Findings: HUD says an active
  uncountered obstacle is resolved; runtime integration test's source-literal
  assertion does not match client formatting.
- Configured reviewer route was spawn-specified `codex_subagent /
  gpt-6-astra / high`; serving metadata was not independently observable, so
  `configured_gate_satisfied=false`. Candidate and review-packet hashes matched
  before/after; sealed-root tripwire stayed 116 files with the recorded hash.
- Candidate 018 corrects the HUD label and source assertion. Current diff
  `c215b22a8735e15a88a38d6a64f7d7f9234729ef2db3af394b1b2a233f2420bd`; packet
  `REVIEW-PACKET-018.md`, SHA-256
  `90dc0ab37f3444a0bfdc26c638198d010956921f85f742f7c22aa1c0737336bb`.
- Candidate 018 requires fresh A/B audits and final review. `submission_ready`
  stays false; `live_submission_external_capture` remains unresolved.

## Candidate 018 final review — 2026-11-02

- Candidate-018 implementation and governance audits pass. The final reviewer
  independently found R1–R5 pass and verified exact candidate, packet, package
  manifest and sealed-root hashes.
- Final verdict is NOT-READY for the final gate because the configured
  `codex_subagent / gpt-6-astra / high` serving model and effort cannot be
  independently verified. Invocation record sets
  `configured_gate_satisfied=false`; no route substitution is claimed.
- Offline code remediation is complete on candidate diff
  `c215b22a8735e15a88a38d6a64f7d7f9234729ef2db3af394b1b2a233f2420bd`.
  Formal development closure remains unclaimed pending a review route whose
  serving model/effort can be evidenced. `submission_ready=false`, and
  `live_submission_external_capture` remains unresolved.

## Final review invocation 019 — offline development closure

- At the requester's direction, a fresh independent agent was spawned explicitly
  with `model=gpt-6-astra` and `reasoning_effort=high` and reviewed the unchanged
  candidate 018. It returned READY for offline development and independently
  passed R1–R5, verified the 25-artifact manifest, and matched candidate, packet
  and sealed-root hashes.
- Actual serving model/effort remain unobservable. The invocation record
  therefore preserves `configured_gate_satisfied=false` and makes no claim that
  serving metadata was independently verified. This does not change the
  reviewer's READY verdict for the bounded offline candidate.
- Offline development is closed on exact diff
  `c215b22a8735e15a88a38d6a64f7d7f9234729ef2db3af394b1b2a233f2420bd`;
  `submission_ready=false`, and `live_submission_external_capture` remains
  unresolved.

## Final review retry 020

- A new independent agent was explicitly requested with
  `model=gpt-6-astra`, `reasoning_effort=high`, and fresh context. It returned
  READY for the unchanged offline candidate; R1–R5 pass.
- It independently matched candidate, packet, package-manifest and sealed-root
  identities. The exact diff remains
  `c215b22a8735e15a88a38d6a64f7d7f9234729ef2db3af394b1b2a233f2420bd`.
- The platform still exposes no serving-model/effort attestation. The invocation
  record keeps `configured_gate_satisfied=false` and distinguishes the explicit
  matching request from unverified serving metadata.
- Offline development remains closed. `submission_ready=false`; external capture
  remains unresolved.

