# Worker A packet — live Twitch EventSub adapter

Task: `development`  
Phase: `plan`  
Coordinator: one; worker: A of 3  
Base HEAD: `bb02cea7e1c260eb30ea9491e7759761c0f290d4`  
Ledger revision: `15`

## Mandatory preflight

Before reading, inferring, editing or testing, run the context compiler with
exactly these owned paths (repeat `--owned-path`):

```text
python3 -m coordination.context_contract --task development --phase plan \
  --owned-path server/twitch_live.py \
  --owned-path server/app.py \
  --owned-path server/intake.py \
  --owned-path schemas/twitch-live.json \
  --owned-path tests/test_twitch_live.py
```

Read the emitted packet. If it fails, stop and report the exact error. Do not
edit `config/directive-policy.json`, `coordination/context_contract.py`,
`docs/planning/STATUS.md`, `docs/planning/CONTEXT-v2.md`, `client/**`,
`tools/**` or another worker's paths.

## Authorization boundary

The requester authorized the bounded live-submission implementation and one
future live-capture session. Worker A may implement the adapter and run
focused local unit tests with fake transports. Worker A must **not** make a
real Twitch/HTTP/WebSocket call, start `server.app`, run gameplay, use a token,
or claim live evidence. Credentials and raw chat must never be printed,
committed, logged or persisted.

## Owned paths

- `server/twitch_live.py` (new)
- live wiring in `server/app.py` and `server/intake.py` only
- `schemas/twitch-live.json` (new)
- `tests/test_twitch_live.py` (new)

Do not edit other paths. Preserve the existing uncommitted edits in
`server/app.py`, `server/intake.py` and all other files.

## Required behavior

Implement the official Twitch EventSub WebSocket `channel.chat.message`
boundary around the existing authoritative `CommandIntake`:

1. Validate a user OAuth token against the Twitch validation endpoint without
   printing or persisting token bytes. Require at least `user:read:chat`;
   record only bounded metadata (client ID hash, user ID hash, scopes, expiry,
   validation timestamp). Reject missing/invalid/expired tokens.
2. Open exactly one WebSocket to the EventSub welcome URL. Read the welcome
   frame, capture `session.id`, then subscribe to `channel.chat.message`
   version 1 with `{broadcaster_user_id, user_id}` and WebSocket transport.
   Do not subscribe before the welcome session exists.
3. Handle `session_keepalive`, `notification`, `session_reconnect` and
   revocation. Reconnect only through the announced reconnect URL, bounded;
   fail closed after the bound is exhausted. No automatic model retry,
   provider change or silent fallback.
4. Deduplicate by `metadata.message_id` in a bounded store. Parse only a strict,
   bounded command grammar; reject unsupported, oversized or non-command chat.
   Link the Twitch chat user to an account-level subject using a stable SHA-256
   of the platform identity; never persist raw handles, user IDs or chat text.
5. Submit at most one canonical command per accepted receipt through
   `CommandIntake.submit` (or a thin equivalent method in `intake.py`). Keep
   engine authority independent of the transport.
6. Emit a live-evidence record only after token validation succeeded **and** a
   real subscription notification was received. The record contains sanitized
   hashes/timestamps, subscription/session metadata, receipt hash, linked
   subject hash, canonical command/result and visible consequence. A fake
   transport in tests must be labelled `fixture` and can never set
   `live_verified`.
7. Preserve the offline fixture path and the fixed offline evidence envelope.
   `public_state()` must report live only while the live adapter is validated
   and active; otherwise report disconnected/offline truthfully.

## Acceptance checks

```text
python3 -m unittest tests.test_twitch_live tests.test_command_intake \
  tests.test_runtime_integration -v
python3 -m coordination.context_contract --task development --phase plan \
  --owned-path server/twitch_live.py --owned-path server/app.py \
  --owned-path server/intake.py --owned-path schemas/twitch-live.json \
  --owned-path tests/test_twitch_live.py --validate-only
```

Unit tests must prove welcome-before-subscribe, dedupe, reconnect, bounded
queues/state, identity hashing, canonical intake, no token/raw-chat persistence
and fixture/live label separation. Do not run the real service or network.

## Return

At most 250 words plus owned artifact paths. Report the compiler packet hash,
files changed, tests run/results, interface assumptions, and any blocker. Do
not claim live Twitch evidence from tests.
