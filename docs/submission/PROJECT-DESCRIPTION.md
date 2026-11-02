# Project description

**TwitchCon Odyssey** is a local, deterministic Twitch co-op crisis game: the
streamer steers a shared build through a stylized San Diego route while chat
proposes hazards and counter-commands that the authoritative engine resolves.
The prototype is built around a strict split between model/transport input and
game authority, and around evidence that distinguishes fixtures from observed
live activity.

## What the project does

- Runs a 90-second, three-turn match on a San Diego route ending at a fictional
  main stage. Planning, resolution and reward phases follow the selected
  deterministic clock contract.
- Renders a canvas HUD with route progress, committed-hazard state, a
  plain-language next action, account-eligible audience counts and a final
  fictional-Hype settlement.
- Accepts canonical commands through a bounded intake boundary: linked account
  subjects, one influence per subject per turn, receipt deduplication, expiry
  windows and fail-closed rejection of unlinked or late input.
- Emits fixture-labelled telemetry and an offline evidence package whose bytes
  are SHA-256 bound and reproducible.
- Provides a mechanical submission-readiness verifier that separates live
  Twitch, capture, video, repository, licensing and independent-review
  predicates. Missing or stale evidence keeps `submission_ready: false`.

## Twitch participation

The intended production path is the official Twitch EventSub WebSocket
subscription to `channel.chat.message`, with token validation, one welcome
session, bounded reconnect/dedupe, hashed identity binding and at most one
canonical command per accepted receipt. The live adapter is implemented behind
a transport-injectable boundary and covered by fake-transport tests under the
2026-11-02 authorization; **live verification remains pending in this tree**.
No live token validation, EventSub subscription or chat receipt has been
observed. Tests use fake transports and are labelled fixtures.

The offline fixture path remains the only verified runnable demo. Fixture
events are labelled `origin: fixture` and `live_participation: false`; they can
never satisfy a live predicate.

## Codex use

The project's planning, implementation, remediation and evidence audits were
performed in a recorded Codex session. The judge-facing session identifier is
`01a1955f-ecad-7053-a225-82baa06d86bd`; provenance and privacy boundaries are in
[`CODEX-SESSION.md`](CODEX-SESSION.md). The session ID is an identifier, not
proof that every described feature works.

## Determinism and safety

- Physics, collision, phase transitions, settlement and pause behaviour live in
  the deterministic kernel and authoritative engine, not in a model or
  transport.
- Models and fixtures cannot mutate physics directly. Runtime constructs the
  deterministic mock provider only; there is no runtime path to an external
  model provider.
- Hazards are bounded: one obstacle per turn, three per match, no stun, no
  steering loss and capped slowdown. A committed hazard ID binds its warning,
  counter and bounty increment.
- The package omits credentials, raw chat and unhashed handles. It contains
  fixture/offline evidence with `live_validated: false`.

## Evidence status (2026-11-02)

| Area | Status |
| --- | --- |
| Deterministic engine, intake, telemetry, offline HUD | Implemented and covered by targeted offline tests |
| Offline evidence package and readiness verifier | Implemented; package verifies declared bytes with `live_validated: false` |
| Official Twitch EventSub live adapter | Implementation authorized; not live-verified |
| Observed Twitch-triggered gameplay | Missing |
| Live desktop 1440x1100 / mobile 390x844 captures | Missing; offline fixture/disconnected renders exist and are explicitly non-live |
| Public YouTube demo under 180 seconds | Missing |
| Judge-accessible repository URL and final commit | Missing |
| Repository license | Missing; owner must select |
| Independent Astra review of the final candidate | Missing |

`submission_ready` is **false**. This document is a truthful project
description, not a submission or completion claim. See
[`SUBMISSION-METADATA.json`](SUBMISSION-METADATA.json) for the machine-readable
predicate record.
