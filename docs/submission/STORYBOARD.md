# Sanitized demo storyboard (under 180 seconds)

Status: **blocked — no live footage and no final video exists.**  
Prepared by Worker B on 2026-11-02 for the authorized submission-readiness wave.
This storyboard is a plan, not evidence that a live Twitch session happened.

> **Hard blocker.** The final video requires the coordinator's observed live
> session: a validated Twitch token, one EventSub `channel.chat.message`
> receipt, a linked account-level subject, one applied canonical command, the
> authoritative engine result and its visible consequence, followed by a
> sanitized Codex/session segment. Fixture, disconnected, rehearsal or
> screenshots cannot substitute. Until that session is recorded, the video
> predicate is false and `submission_ready` remains `false`.

## Target

- Runtime: **2:52 (172 seconds)**, hard ceiling 180 seconds.
- Desktop viewport: `1440×1100`. Mobile viewport: `390×844`.
- Language: English captions plus on-screen text. Captions are burned in or
  supplied as a sidecar; no auto-generated claims.
- Audio: synthesized/owned bed and SFX only. No Twitch audio, no third-party
  music, no copyrighted clips. Keep the bed under the voice track.
- Visual assets: owned title cards, the real client capture, and a sanitized
  Codex screen recording. No Twitch emotes, avatars, subscriber data or raw
  chat are shown.

## Shot list

| Time | Shot | Required content | Provenance label |
| --- | --- | --- | --- |
| 0:00–0:08 | Cold open | Title card: “TwitchCon Odyssey — one build, one route.” Caption: “Observed live session; sanitized.” | `LIVE SESSION` |
| 0:08–0:30 | Actual Twitch receipt | Live HUD badge, EventSub session metadata (hashed), token-validation metadata **without token bytes**, and the hashed receipt ID. No raw chat. | `ACTUAL TWITCH RECEIPT` |
| 0:30–0:45 | Linked subject | Account-level linked-subject hash and the statement “one receipt → at most one canonical command.” No handle, login or avatar. | `LINKED SUBJECT (HASHED)` |
| 0:45–1:05 | Canonical command | Command kind, sequence, tick and admission status from the audit trace. Show the sanitized command line, not chat text. | `CANONICAL COMMAND` |
| 1:05–1:25 | Engine result | Authoritative tick/sequence, phase, lane, hazard ID and route progress from the state snapshot. No inferred or simulated metrics. | `AUTHORITATIVE RESULT` |
| 1:25–1:55 | Visible consequence | Desktop `1440×1100` clip of the same command's visible lane change, hazard resolution or collision consequence. HUD mode must read live. | `DESKTOP VISIBLE CONSEQUENCE` |
| 1:55–2:15 | Mobile proof | Mobile `390×844` clip of the same authoritative state; controls labelled, no horizontal overflow, no second live claim. | `MOBILE 390×844` |
| 2:15–2:45 | Codex/session segment | Sanitized Codex screen recording: session ID `01a1955f-ecad-7053-a225-82baa06d86bd`, planning/diff/test review. Crop unrelated tabs, home paths, tokens and raw transcripts. | `SANITIZED CODEX SESSION` |
| 2:45–2:52 | Close | Repository/setup pointer, evidence-manifest hash, “fixture and rehearsal media are labelled and are not live evidence.” | `EVIDENCE BOUND` |

The required order is receipt → linked subject → canonical command → engine
result → visible consequence → Codex/session segment. Do not reorder the first
five. Do not insert a fixture clip between live shots without a visible
`FIXTURE` label.

## Sanitization checklist

- [ ] No OAuth token, client secret, authorization header or cookie.
- [ ] No raw chat message, handle, login, avatar, user ID or subscriber data.
- [ ] No home-directory path, unrelated browser tab, notification or shell history.
- [ ] Token metadata is limited to validity, scopes, hashes and timestamps.
- [ ] Receipt and subject are shown only as SHA-256 values.
- [ ] Every non-live insert is labelled `FIXTURE` or `REHEARSAL`; neither can
      satisfy the live/video predicate.
- [ ] Audio and visual assets are synthesized or owned; licensing checklist is
      updated before upload.
- [ ] Video is under 180 seconds and accessible (captions, readable contrast,
      no flashing cut).

## Capture and assembly boundary

Offline presentation evidence is produced by:

```text
python3 -m tools.capture_submission capture --mode fixture
python3 -m tools.capture_submission capture --mode disconnected
python3 -m tools.capture_submission verify evidence/submission-capture/fixture
```

Live capture is allowed only against an explicitly supplied loopback URL and a
validated observed live record:

```text
python3 -m tools.capture_submission capture --mode live \
  --url http://127.0.0.1:8000 \
  --evidence evidence/submission-capture/live/observed-live.json
```

The tool refuses non-loopback URLs, fixture evidence for live mode, and any
record missing the token, subscription, notification, receipt, subject,
command, engine-result or consequence predicates. It performs no upload.

Final video evaluation is fail-closed:

```text
python3 -m tools.capture_submission assemble --evidence <observed-manifest.json>
```

The manifest must bind live `desktop` and `mobile` captures at the exact
viewports and the six ordered segments above, totalling under 180 seconds.
`assemble --out <file>` additionally requires `ffmpeg`; the tool never uploads
the result. A structural pass is not proof of a human-observed Twitch session —
that remains a coordinator/human evidence obligation.

## Current evidence

- `evidence/submission-capture/fixture/` — offline fixture render, clearly
  labelled `FIXTURE`, with desktop and mobile PNGs, timeline and accessibility
  checklist. **Not live Twitch evidence.**
- `evidence/submission-capture/disconnected/` — offline disconnected render,
  controls disabled, clearly labelled `DISCONNECTED`. **Not live evidence.**
- No `live/` capture exists. No final video exists. No YouTube upload or
  Devpost submission has been performed.

**Exact live/video blocker:** the repository lacks an observed live Twitch
EventSub session with a validated token, real chat receipt, linked subject,
admitted canonical command, authoritative result and visible consequence; it
also lacks the sanitized Codex recording needed for the final segment.
