# Submission-readiness closeout plan

Date: 2026-11-02  
Current base HEAD: `bb02cea7e1c260eb30ea9491e7759761c0f290d4`  
Current offline candidate diff:
`c215b22a8735e15a88a38d6a64f7d7f9234729ef2db3af394b1b2a233f2420bd`  
Authorization recorded from the requester: “close the submission readiness” and
“Make it in such a way that Astra review does not get blocked. We can do astra
review at the end.”

This plan converts the remaining `live_submission_external_capture` decision
into an evidence-bound execution wave. It does not treat authorization as proof
of completion. `submission_ready` stays false until every acceptance predicate
below is evidenced and the final independent review returns READY.

## Current gap

Offline development is closed and R1–R5 pass. The repository still lacks:

1. an authenticated Twitch input adapter and observed Twitch-triggered gameplay;
2. honest live provenance derived from validated Twitch identity/event data;
3. rendered desktop and mobile evidence;
4. a real, accessible YouTube demo under three minutes showing Twitch operation
   and Codex use;
5. a judge-accessible repository URL, final setup instructions, project text,
   session ID, and submission manifest;
6. a mechanically derived `submission_ready: true` record bound to those bytes
   and URLs.

Official sources checked on 2026-11-02:

- https://twitchcon-codex.devpost.com/rules
- https://twitchcon-codex.devpost.com/updates/47341-final-weekend-make-your-project-come-alive
- https://dev.twitch.tv/docs/eventsub/handling-websocket-events
- https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types
- https://dev.twitch.tv/docs/authentication/validate-tokens

The rules require working Twitch integration, repository/setup material, a
project/Codex description, Codex session ID, and a YouTube demo under three
minutes. The organizer update says unlisted is acceptable but private is not.

## Required human inputs

These values must be supplied out of band before the dependent live/publishing
steps. Agents must never print or commit tokens or client secrets.

| Input | Purpose |
|---|---|
| Twitch client ID and user OAuth token source | Validate identity and subscribe to `channel.chat.message` |
| Broadcaster user ID, chat user ID, and channel login | Bind the exact authorized test channel |
| Consent-safe test viewer/account and message | Produce one attributable Twitch-triggered command without retaining raw chat |
| Judge-accessible repository destination/URL | Freeze and expose the reviewed code and setup instructions |
| YouTube channel/upload target and visibility | Upload the final `<180s` video; `unlisted` or `public`, never private |
| Devpost project URL | Bind the readiness record to the intended submission |
| Explicit booleans for push, YouTube upload, and Devpost final submit | Separate readiness work from irreversible publication/submission |

## Single-shot execution graph

The saved single-shot prompt launches one coordinator. The coordinator first
records the new authorization in an exclusive governance transaction, then
creates and saves three bounded worker packets before spawning them.

| Wave | Owner | Exclusive ownership | Completion condition |
|---|---|---|---|
| A — live Twitch adapter | Implementor A | `server/twitch_live.py`, live wiring in `server/app.py`/`server/intake.py`, Twitch schemas and focused tests | OAuth token validated; one EventSub WebSocket; `channel.chat.message` reaches canonical intake; dedupe/reconnect/bounds fail closed; no secrets/raw chat persisted |
| B — presentation and capture | Implementor B | `client/**`, capture/storyboard tooling, rendered evidence paths | Honest live HUD; desktop `1440×1100` and mobile `390×844` evidence; accessible controls; sanitized `<180s` video showing Twitch event, gameplay consequence, and Codex evidence |
| C — readiness/package/governance | Implementor C | `tools/**`, `docs/submission/**`, readiness schemas/records, package manifest, ledger/context tests | Repository/setup/description/session/video metadata complete; all evidence hashed; `submission_ready` remains false while any predicate is missing |

Workers A–C run in parallel only after their exact owned paths and base hashes
are compiled. They may not edit each other's paths. The coordinator integrates
their work, resolves interface mismatches, and reruns the context compiler after
every governance/source-binding transaction.

## Live verification and capture wave

After integration, the coordinator performs one authorized live session:

1. Validate the OAuth token using Twitch's validation endpoint and verify the
   minimum required scopes. Record only token metadata needed for evidence.
2. Start one local authoritative runtime and one EventSub WebSocket connection.
3. Subscribe to `channel.chat.message`; send one consent-safe test message from
   the authorized account; prove receipt ID dedupe, identity binding, canonical
   command admission, and visible gameplay consequence.
4. Capture desktop and mobile views plus a sanitized audit trace. Confirm the
   page labels the session live only while authenticated Twitch evidence is
   active and fails closed to offline/disconnected status otherwise.
5. Record and assemble a demo shorter than 180 seconds. It must show actual
   Twitch operation and a sanitized Codex-development segment. Use only
   synthesized/owned audio and assets.
6. Stop the runtime/WebSocket, remove transient tokens, and verify that no secret
   or raw chat content entered Git or packaged evidence.

No fixture may satisfy a live predicate. A screenshot, mocked HTTP response, or
configured credential without an observed event is insufficient.

## Evidence and readiness contract

The submission evidence root must contain a machine-readable manifest binding:

- reviewed commit/base and tracked-diff hashes;
- Twitch token validation metadata without token bytes;
- EventSub subscription/session metadata and hashed receipt ID;
- canonical command/result and visible consequence;
- desktop/mobile capture hashes and dimensions;
- video file SHA-256, duration, upload URL, visibility, and observed availability;
- repository URL/commit, setup verification, project description and Codex
  session ID;
- license/trademark/audio checklist;
- cleanup result and sealed-root tripwire;
- final independent-review packet/verdict/invocation.

`submission_ready` becomes true only when every predicate above passes. Devpost
form submission is a separate external action and occurs only when its explicit
boolean is true.

## Final Astra review without route deadlock

Astra runs once, last, after all substantive bytes, URLs and evidence are frozen.
The governance transaction must separate review quality from serving-attestation
availability:

- `route_request_satisfied`: orchestration accepted the exact explicit request
  `codex_subagent / gpt-6-astra / high`;
- `substitution_observed`: true only when the platform reports a different route;
- `serving_attestation_available`: records whether the platform exposes an
  independent serving receipt;
- `substantive_review_gate_satisfied`: independent reviewer returned READY for
  the exact candidate and evidence packet.

Per the requester's current instruction, unavailable serving attestation alone
does not block the substantive verdict or submission readiness when the exact
route request was accepted and no substitution was observed. It remains an
explicit evidence caveat. A rejected route request or reported substitution
still fails closed; no fallback or retry occurs without the requester.

The Astra reviewer owns no implementation files and cannot change the candidate.
After READY, the coordinator performs a deterministic governance-only finalizer:
write review receipts, flip the readiness record, verify all hashes, then create
the final commit. Any implementation change invalidates the review and capture.

## Stop conditions

Stop and return one consolidated blocker report if credentials/IDs/targets are
missing, Twitch rejects authentication/subscription, the video is not accessible
or is 180 seconds or longer, any secret/raw chat is detected, candidate bytes
change after capture, a required external action lacks its exact authorization,
or Astra returns NOT-READY. Do not replace real evidence with fixtures.

## Recovery

Every worker prompt, compiler packet hash, candidate hash, evidence manifest and
agent status is saved under this directory. On restart, read
`SUBMISSION-CLOSEOUT-STATE.json`, verify current HEAD/diff and evidence hashes,
then resume only the first incomplete wave. Do not repeat a completed external
upload or Devpost submission without checking its current state first.
