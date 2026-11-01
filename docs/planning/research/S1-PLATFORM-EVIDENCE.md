# S1 — Platform evidence for identity, timing and bounded model work

Retrieval date: **2026-11-01**. Research only; no integration, API inference, gameplay or timing measurements. D-03/D-05 in [GAMEPLAN-v2](../GAMEPLAN-v2.md) remain partially specified proposals requiring human decisions.

## Search boundaries and evidence weight

Question: which documented Twitch/OpenAI primitives support account-based input accounting and asynchronous proposals, and which official event rules constrain demonstration time?

Searched the web for Twitch Extension identity/JWT, EventSub chat identity/timestamps, OpenAI Structured Outputs/latency optimization, and Codex x TwitchCon Devpost rules. Opened 11 distinct official pages: three Extension pages; EventSub overview, reference, WebSocket handling/reference and webhook handling; two OpenAI guides; Devpost rules. Coverage is current English documentation retrieved on the date above, without a publication-date cutoff. Excluded forums, blogs, papers, search snippets and historical project research as platform evidence. This is a bounded documentation review, not a systematic literature review or independent platform test.

| Sources reviewed | Type/tier and weight | Limits/independence |
| --- | --- | --- |
| Twitch Extension overview, reference, building guide | Primary vendor specification; high for documented fields/authentication | Same vendor/documentation family; not three independent confirmations or identity-assurance studies |
| Twitch EventSub overview, reference and three transport pages | Primary vendor specification; high for envelope/payload semantics | Same specification family; no measured delivery performance |
| OpenAI Structured Outputs guide | Primary vendor specification; high for supported output contract | Not evidence of game-action correctness |
| OpenAI latency guide | Primary vendor engineering guidance; moderate for optimization direction | Heuristics, no benchmark here or deadline guarantee |
| Codex x TwitchCon Devpost rules | Primary event rules; high for stated submission conditions | One event/rules page; no inferred in-game duration |

## Identity and authentication

An Extension EBS verifies the signed JWT supplied through `onAuthorized()` using its Extension secret. Tokens expire; the Helper refreshes them and invokes the callback again. These are authenticated token claims, rather than trust in an arbitrary client-submitted identifier. [Building Extensions](https://dev.twitch.tv/docs/extensions/building/#verifying-the-jwt)

The JWT includes `channel_id`, `exp`, `role` and `opaque_user_id`. A `U` opaque identifier references a Twitch account across sessions/channels; an `A` identifier is transient, can represent different users over time, and must not be associated with persistent data. `user_id` is the actual Twitch user ID only when identity sharing is allowed. Users can revoke sharing at any time and then receive a new opaque identifier. Consequently, “stable” does not mean immutable through identity revocation. [JWT schema](https://dev.twitch.tv/docs/extensions/reference/#jwt-schema), [identity overview](https://dev.twitch.tv/docs/extensions/#identity)

EventSub `channel.chat.message` supplies `chatter_user_id`, separately from login/display names, and a UUID `message_id` for the chat message. This supports account identity and individual message identity. An unlinked opaque Extension identifier does not expose the corresponding chat user ID; the reviewed schema provides no general conversion from an opaque viewer identifier to that account ID. [Chat message event](https://dev.twitch.tv/docs/eventsub/eventsub-reference/#channel-chat-message-event), [JWT schema](https://dev.twitch.tv/docs/extensions/reference/#jwt-schema)

## IDs, timestamps and receipt

Keep three concepts separate: chat `event.message_id` identifies the chat message; EventSub envelope `metadata.message_id` identifies the notification; `chatter_user_id` identifies the account. WebSocket resends retain their notification ID. Twitch explicitly advises tracking already processed notification IDs because delivery may occur more than once. [WebSocket notification fields](https://dev.twitch.tv/docs/eventsub/websocket-reference/#notification-message), [duplicate-event guidance](https://dev.twitch.tv/docs/eventsub/#handling-duplicate-events)

WebSocket `message_timestamp` is UTC time the notification was sent. Webhooks likewise provide notification ID and sent timestamp, plus an HMAC signature covering ID, timestamp and raw body; verify authenticity before handling. These timestamps are neither this game's authoritative receipt time nor proof of when a viewer clicked. Twitch's suggested ten-minute replay-age check is a security consideration, not permission for ten minutes of game-input grace. [WebSocket reference](https://dev.twitch.tv/docs/eventsub/websocket-reference/#notification-message), [webhook headers/verification](https://dev.twitch.tv/docs/eventsub/handling-webhook-events/), [replay guidance](https://dev.twitch.tv/docs/eventsub/#guarding-against-replay-attacks)

Twitch documents no replay of events lost while reconnecting and resubscribing after a lost WebSocket connection. Webhook handlers should respond promptly and can store notifications for later processing. Neither behavior establishes a delivery-time bound for a twenty-second turn. [WebSocket handling](https://dev.twitch.tv/docs/eventsub/handling-websocket-events/), [webhook handling](https://dev.twitch.tv/docs/eventsub/handling-webhook-events/)

## Structured output and latency

OpenAI Structured Outputs supports strict adherence to a supported JSON Schema, rather than JSON validity alone. It requires `additionalProperties: false` on objects; unsupported strict schemas error. Refusals and incomplete responses need explicit handling, and schema-conforming content can still contain mistakes. Schema validity therefore cannot establish a proposal's legal placement, current turn, safety or correctness. [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)

The latency guide recommends fewer output tokens and compact structured syntax, fewer requests, and parallelizing independent work. It also identifies hard-coded confirmations/refusals, precomputed responses and conventional UI components as alternatives to generation. These support compact proposals and deterministic status UI as engineering choices. The guide does not prescribe a game-loop architecture or promise completion before t=20. [Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization)

## Event and demo constraints

The official rules say the demo video **should** be under three minutes and judges need not watch beyond three minutes. It should show Twitch functionality and Codex development; it must be publicly visible on YouTube. The project must connect to Twitch and function as depicted. Submission closes November 2, 2026 at 2 p.m. Pacific Time. The reviewed rules set no numerical match deadline, first-simulation duration or full-match-in-video requirement. [Official rules, dates and submission requirements](https://twitchcon-codex.devpost.com/rules)

## Evidence-backed constraints

- Authenticate Extension claims; respect expiry, consent revocation and anonymous-ID limitations. Account and notification IDs have distinct documented meanings.
- Expect duplicate notifications and potential disconnection loss; sent timestamps do not establish local receipt.
- Handle refusals/incomplete outputs alongside strict schema use. Compact output and conventional UI have official optimization support, without a latency SLA.
- Preserve the demo rule's wording: under three minutes is stated as “should”; judges need not watch longer. This concerns the video.

## Unsupported/unknown

No reviewed source guarantees one account equals one human, excludes automation/multiple accounts, equates an opaque Extension ID with a chat account ID, supplies atomic cross-input influence accounting, or defines Odyssey's receipt boundary. No reviewed primary rule selects a match length. Twitch/video/model end-to-end latency, fairness under actual load, boundary ordering and network grace remain unmeasured or unresolved. Confidence is high in the quoted specification meanings; unknown for implementation/runtime assurance.

## Design inferences (not source claims)

For an eventual approved design, a common verified account subject could join linked Extension/chat inputs; an atomic `(match, turn, subject)` ledger could enforce an account-level quota separately from transport dedupe. Anonymous participation needs a separately approved eligibility policy and cannot substantiate the human-level invariant. Recording monotonic server receipt and retaining source timestamps separately could implement D-05. Keeping model work asynchronous, validating completed proposals locally, discarding late results and using deterministic fallback/status UI could preserve engine independence. These are design options consistent with project proposals, not Twitch/OpenAI requirements or approved mechanics. A match deadline still needs human selection and later evidence.
