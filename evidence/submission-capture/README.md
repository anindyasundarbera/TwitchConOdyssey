# Submission capture evidence (Worker B)

Status: **offline presentation evidence only. No live Twitch session, no live
capture and no final video.** `submission_ready` remains `false`.

These renders were produced locally by `tools/capture_submission.py` with
Playwright `set_content` from the real client files. No HTTP service, no
gameplay, no external network destination and no upload was started. The tool
aborts any request except `data:`, `blob:` and `about:blank`; live mode
additionally allows only the explicitly supplied loopback origin. Each run recorded
`blocked_requests: []` and `page_errors: []`.

## What is present

| Directory | Label | Meaning |
| --- | --- | --- |
| `fixture/` | `FIXTURE — offline fixture render (not live Twitch activity)` | Offline fixture state rendered at desktop and mobile viewports. Controls enabled. **Not live evidence.** |
| `disconnected/` | `DISCONNECTED — no authoritative state (offline render)` | Fetch unavailable; controls disabled and no live status inferred. **Not live evidence.** |
| `live/` | absent | Requires the coordinator's observed live session and a validated live record. |

Every directory contains:

- `CAPTURE-MANIFEST.json` — mode, truthful label, source bindings, artifact
  SHA-256 map, `live_verified` (false here), and the note that the final video
  is not eligible;
- `timeline.json` — ordered steps, expected labels, viewports, measurements,
  capture hashes and blocked-request/page-error records;
- `accessibility.json` — labelled controls, live regions, focus-visible and
  reduced-motion rules, contrast ratios and horizontal-overflow checks;
- PNGs at exactly `1440×1100` and `390×844` (viewport screenshots, not
  full-page stretches).

## Current hashes

### `fixture/`

| Artifact | SHA-256 | Dimensions |
| --- | --- | --- |
| `CAPTURE-MANIFEST.json` | `bdf554bc0b89297abf002a35da770ee06de912f08f9d03b87cff6bea09f7c0eb` | — |
| `fixture-desktop.png` | `4a8cd3735099c8c27fbdbb86efd0cc231f1cf8e5c54f52289b76fc2fdcd2840e` | 1440×1100 |
| `fixture-mobile.png` | `5d14d07e7e5c581b4e54600e7047bb8ceb334a9e8751ca8ebbcdc754a87e000b` | 390×844 |
| `timeline.json` | `a14debec5dab5f42b0cbf376ad6682b0b47f0096275260016854a9c873c4fb0c` | — |
| `accessibility.json` | `19acca4e30f7a279cc393815f53acf612d6cc5147318d8be16394fdc5d4a4a4a` | — |

### `disconnected/`

| Artifact | SHA-256 | Dimensions |
| --- | --- | --- |
| `CAPTURE-MANIFEST.json` | `460420578d9daa12152692626e6abbe17089a1ba5bac6e796a603f665e90ca48` | — |
| `disconnected-desktop.png` | `eca57e18b3b68fa15f10caf55a4fda9658693a4d32283da5f73c81efbe16f66f` | 1440×1100 |
| `disconnected-mobile.png` | `aa5c196d4a1ae3b4a73b1e72fdb263ce7e4d1740a1c56108386f05d1bd9f496d` | 390×844 |
| `timeline.json` | `b46c0c66fa280ba13f242498b93716a3e11ca4aa161526bc23a63ef1b1dcf7d5` | — |
| `accessibility.json` | `9e9596c9ba411aa1d0b4bd4bc501aadd449323a9dde6ece6f8a85f11d4fcc685` | — |

All listed accessibility runs passed. The lowest measured text contrast was
`7.47:1` (muted HUD text) against a `4.5:1` minimum. Mobile document
`scrollWidth` equalled `390`; desktop equalled `1440`.

## Reproduce and verify

```text
python3 -m tools.capture_submission capture --mode fixture \
  --out evidence/submission-capture/fixture
python3 -m tools.capture_submission capture --mode disconnected \
  --out evidence/submission-capture/disconnected
python3 -m tools.capture_submission verify evidence/submission-capture/fixture
python3 -m tools.capture_submission verify evidence/submission-capture/disconnected
```

`capture` refuses to replace a non-empty destination unless `--force` is
explicit. Re-running with `--force` changes PNG bytes and therefore hashes;
treat each manifest as a sealed record of that run.

## Live and video gate

```text
python3 -m tools.capture_submission capture --mode live \
  --url http://127.0.0.1:8000 \
  --evidence path/to/observed-live.json
```

Live mode refuses:

- any URL that is not an explicit loopback `http(s)` URL;
- a missing or fixture record;
- a record without `origin: live`, `fixture: false`,
  `live_participation: true`, `live_verified: true`, a recorded timestamp,
  successful token validation with `user:read:chat`, an enabled
  `channel.chat.message` subscription, a hashed EventSub session, a hashed
  receipt and subject, an applied canonical command, an engine result and a
  visible consequence;
- records containing tokens, secrets, raw chat, handles or display names.

The validator accepts the sanitized `schemas/twitch-live.json` shape
(`token_validation.validated`, `subscription`, `session`, `receipt_sha256`,
`subject_sha256`, `result`, `consequence`) as well as the legacy nested
aliases. The receipt hash is treated as the notification evidence when the
adapter record omits a separate notification flag.

`assemble --evidence <manifest>` evaluates the final-video predicate. The
composed manifest carries the live-adapter record plus:

```json
{
  "capture": {
    "mode": "live",
    "live_verified": true,
    "desktop": {"path": "...", "sha256": "...", "width": 1440, "height": 1100},
    "mobile":  {"path": "...", "sha256": "...", "width": 390,  "height": 844}
  },
  "video_segments": [
    {"role": "twitch_receipt", "path": "...", "sha256": "...", "duration_seconds": 20},
    {"role": "linked_subject", "path": "...", "sha256": "...", "duration_seconds": 20},
    {"role": "canonical_command", "path": "...", "sha256": "...", "duration_seconds": 20},
    {"role": "engine_result", "path": "...", "sha256": "...", "duration_seconds": 20},
    {"role": "visible_consequence", "path": "...", "sha256": "...", "duration_seconds": 20},
    {"role": "codex_session", "path": "...", "sha256": "...", "duration_seconds": 20}
  ]
}
```

Every file must exist inside the repository and match its SHA-256. The six
segments must be in that order and total under 180 seconds.
`assemble --out <file>` additionally requires `ffmpeg`; nothing is uploaded.

**Exact blocker:** no observed live Twitch EventSub session exists (validated
token, real receipt, linked subject, admitted command, authoritative result,
visible consequence), and no sanitized Codex recording has been captured.
Therefore no live capture, final video, YouTube upload or Devpost submission
exists. The fixture and disconnected renders in this directory cannot satisfy
any of those predicates.

## Tooling route note

The configured `codex_subagent / gpt-6.1-sol / high` route was unavailable in
this OpenCode harness. Worker B ran under the current session model. This route
deviation changes no capture bytes, hashes or evidence claims above.
