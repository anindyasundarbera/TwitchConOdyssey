# Single-shot orchestrator prompt — close submission readiness

You are the submission-readiness coordinator for repository
`/home/anindyasundar-bera/Projects/hackathon/TwitchConOdyssey`.

## Inputs — replace every bracketed value before invocation

```text
TWITCH_CLIENT_ID_SOURCE=[secure source; never value]
TWITCH_USER_OAUTH_TOKEN_SOURCE=[secure source; never value]
TWITCH_BROADCASTER_USER_ID=[id]
TWITCH_CHAT_USER_ID=[id]
TWITCH_CHANNEL_LOGIN=[login]
TWITCH_TEST_ACCOUNT=[consent-safe account]
TWITCH_TEST_MESSAGE=[consent-safe bounded command]
REPOSITORY_DESTINATION_URL=[judge-accessible URL]
YOUTUBE_UPLOAD_TARGET=[channel/account]
YOUTUBE_VISIBILITY=[unlisted|public]
DEVPOST_PROJECT_URL=[URL]
ALLOW_REPOSITORY_PUSH=[yes|no]
ALLOW_YOUTUBE_UPLOAD=[yes|no]
ALLOW_DEVPOST_FINAL_SUBMIT=[yes|no]
```

Blank/placeholder values do not authorize inference. Continue all independent
work, then stop before the dependent live or publication action with one
consolidated input request.

## Objective and authority

Close `live_submission_external_capture` and set `submission_ready=true` only
from real, current evidence. The requester explicitly said: “close the
submission readiness” and “Make it in such a way that Astra review does not get
blocked. We can do astra review at the end.” This authorizes the readiness work
described here. Push, YouTube upload and Devpost final submission occur only when
their corresponding input boolean is `yes` and the exact destination matches.

Read `AGENTS.md` and
`docs/planning/development-closure-20261102/submission-readiness/SUBMISSION-READINESS-CLOSEOUT-PLAN.md`.
Before every task, resume, delegation or inference, run the required
`coordination.context_contract` compiler with exact owned paths. Stop on stale
bindings/conflicts. Attempt codebase-memory first and record missing coverage.
Never print or commit credentials. Preserve sealed/historical artifacts.

Expected starting identity:

- HEAD `bb02cea7e1c260eb30ea9491e7759761c0f290d4`
- tracked diff SHA-256
  `c215b22a8735e15a88a38d6a64f7d7f9234729ef2db3af394b1b2a233f2420bd`
- offline review READY at `FINAL-REVIEW-020.md`

Stop if identity differs until the state file and packets are rebound.

## Durable coordination

First save exact bounded prompts under `submission-readiness/agents/` and update
`SUBMISSION-CLOSEOUT-STATE.json`. Keep one coordinator and spawn at most three
workers. Workers are not alone in the repository; they must preserve other
edits and never revert another worker. Each returns <=250 words plus owned paths.

Before implementation, perform one exclusive governance transaction:

1. record the requester's exact authorization wording;
2. advance the directive-ledger revision and source bindings;
3. move `live_submission_external_capture` to `authorized_in_progress`, keeping
   `submission_ready=false` until evidence passes;
4. authorize only the bounded runtime/browser/live-capture actions in this
   prompt; preserve publication booleans and secret-handling boundaries;
5. add tested review-route fields separating requested route, substitution and
   serving-attestation availability. Unavailable serving attestation alone is
   not a substantive readiness blocker under this explicit requester decision.

## Parallel worker wave

Spawn all three with fresh narrow context after saving their packets.

### Worker A — live Twitch adapter

Exclusive ownership: `server/twitch_live.py`, required live wiring in
`server/app.py` and `server/intake.py`, Twitch-specific schemas, focused live
adapter tests. Implement official Twitch EventSub WebSocket
`channel.chat.message` using a validated user token and minimum scopes. Use one
WebSocket, welcome/session subscription, message-ID dedupe, reconnect semantics,
bounded queues/state, canonical identity linking and canonical command intake.
Live evidence may be emitted only after successful token validation and actual
subscription/event receipt. Persist no tokens, raw chat, or unhashed handles.
Offline fixture behavior must remain available and truthfully labelled.

### Worker B — presentation and capture

Exclusive ownership: `client/**`, `tools/capture_submission.py`, storyboard and
capture evidence paths. Render honest live/disconnected/fixture states. Produce
desktop `1440×1100` and mobile `390×844` evidence, accessibility checks and a
deterministic capture timeline. Build a sanitized video under 180 seconds that
shows an actual Twitch event changing the game and a sanitized Codex/session
segment. Use only synthesized/owned audio and assets. Never fabricate Twitch or
Codex footage. Do not upload unless `ALLOW_YOUTUBE_UPLOAD=yes`.

### Worker C — package, docs and readiness

Exclusive ownership: `tools/package_submission.py`, a mechanical submission
readiness verifier, `docs/submission/**`, readiness schemas/records, and the
governance/context tests assigned by the coordinator. Correct stale README/demo
instructions. Build judge-facing setup, feature/Codex description, session-ID
record, licensing checklist, repository/video/Devpost metadata, and complete
SHA-256 manifest. `submission_ready` must remain false if any live/capture/video/
repository predicate is missing or stale.

## Integration and observed execution

Review every worker diff. Integrate without overlapping ownership. Run the
allowed focused verification required by the changed surfaces. Then, only with
all Twitch inputs present:

1. validate the token without printing it;
2. start the local authoritative runtime and one EventSub WebSocket;
3. send the consent-safe message from the authorized test account;
4. record Twitch receipt → linked subject → canonical command → engine result →
   visible consequence, with sanitized hashes and timestamps;
5. capture desktop/mobile and the final video;
6. stop services, remove transient credentials, scan candidate/evidence for
   secrets and raw chat;
7. upload the video only when authorized, verify it is accessible and `<180s`;
8. bind repository URL/commit and run a clean-checkout setup/package check.

If a required observation fails, keep readiness false and return exact evidence.
Fixtures, screenshots alone, configured credentials, or mocked calls never
satisfy live predicates.

## Freeze and final Astra review

Freeze all substantive code, evidence, URLs and manifest bytes. Create a review
packet containing exact hashes and acceptance results. Only now spawn one
independent reviewer using explicit `model=gpt-6-astra`,
`reasoning_effort=high`, `fork_turns=none`. The reviewer owns no implementation
paths and must verify R1–R5, real Twitch operation, capture/video, repository
reproduction, secret hygiene, licensing, readiness derivation and tripwires.

The review verdict is substantive. Record separately:

- exact route requested and whether spawn accepted it;
- whether substitution was reported;
- whether serving attestation is available;
- READY/NOT-READY for the frozen candidate.

Per the current requester instruction, missing serving attestation alone must
not turn a substantively READY review into NOT-READY when the exact Astra/high
request was accepted and no substitution was reported. A rejected request,
reported substitution, candidate mismatch or substantive finding fails closed.
Do not retry or fall back automatically.

After READY, perform only the deterministic governance finalizer: save review
records, recompute all hashes, set `submission_ready=true`, resolve
`live_submission_external_capture`, create the final commit, and push/upload/
submit only when the respective booleans authorize the exact targets. Any code
or capture change requires a new packet and review.

## Finish

Update `SUBMISSION-CLOSEOUT-STATE.json`, run context validation, diff hygiene,
package/readiness verification, secret scan and sealed-root tripwires. Report
under 250 words: final commit/diff, Twitch observation evidence, capture/video
URL and duration, repository URL, package digest, Astra verdict/route evidence,
readiness predicates, external actions actually performed, and remaining
blockers. Do not claim Devpost submission unless its page visibly reports
Submitted.
