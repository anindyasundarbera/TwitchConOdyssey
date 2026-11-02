# Worker B packet — presentation, capture and sanitized video tooling

Task: `complex_coding_debugging`  
Phase: `plan`  
Coordinator: one; worker: B of 3  
Base HEAD: `bb02cea7e1c260eb30ea9491e7759761c0f290d4`  
Ledger revision: `15`

## Mandatory preflight

Before reading, inferring, editing or testing, run the context compiler with
exactly these owned paths:

```text
python3 -m coordination.context_contract --task complex_coding_debugging --phase plan \
  --owned-path client/app.js \
  --owned-path client/hud.js \
  --owned-path client/hud.test.js \
  --owned-path client/index.html \
  --owned-path client/style.css \
  --owned-path tools/capture_submission.py \
  --owned-path tests/test_presentation_capture.py \
  --owned-path docs/submission/STORYBOARD.md \
  --owned-path evidence/submission-capture/README.md
```

Read the emitted packet. Stop on failure. Do not edit `server/**`, `config/**`,
`coordination/**`, `tools/package_submission.py`, `docs/planning/**` or another
worker's paths. Preserve all existing uncommitted edits.

## Authorization boundary

The requester authorized honest live/disconnected/fixture presentation and the
future desktop/mobile/final-video capture. Worker B may build and unit-test the
renderer and capture tooling, and may render offline fixture states for
presentation evidence if clearly labelled. Worker B must **not** start the
authoritative server, call Twitch, use a token, fabricate a Twitch event or
Codex segment, upload a video, or claim the final live video exists. The final
video requires the coordinator's observed live session.

## Owned paths

- `client/**`
- `tools/capture_submission.py` (new)
- `tests/test_presentation_capture.py` (new)
- `docs/submission/STORYBOARD.md` (new)
- `evidence/submission-capture/**` (offline, clearly labelled only)

## Required behavior

1. Render three truthful modes from the server envelope:
   - `live`: only when `evidence.origin == "live"`,
     `evidence.live_participation == true` and the live adapter is verified;
   - `fixture`: offline fixture/simulation, explicitly not live;
   - `disconnected`: fetch/state unavailable, with controls disabled.
   The client must never infer live status from a query parameter, local state
   or a screenshot.
2. Keep the HUD accessible and mobile-ready: labelled controls, focus-visible
   states, live status announcements, no horizontal overflow at `390×844`, and
   readable contrast. Preserve the deterministic authoritative-state contract.
3. Implement `tools/capture_submission.py` with Playwright:
   - desktop viewport `1440×1100`, mobile viewport `390×844`;
   - deterministic timeline JSON (ordered steps, expected labels, hashes);
   - PNG capture plus a basic accessibility checklist;
   - refuse to write a "live" capture unless supplied an observed live evidence
     record; fixture captures must be labelled `fixture`;
   - no upload, no network destination other than an explicitly supplied local
     URL.
4. Write `docs/submission/STORYBOARD.md` for a sanitized under-180-second video:
   actual Twitch receipt -> linked subject -> canonical command -> engine
   result -> visible consequence, followed by a sanitized Codex/session
   segment. Use only synthesized/owned audio and assets. The storyboard must
   state that missing live footage blocks the final video.
5. Implement the video assembly boundary in `tools/capture_submission.py` or a
   documented subcommand that refuses to produce the submission video without
   the observed evidence manifest. An offline rehearsal clip, if produced, must
   be labelled rehearsal and cannot satisfy the video predicate.

## Acceptance checks

```text
node --test client/hud.test.js
python3 -m unittest tests.test_presentation_capture tests.test_runtime_integration -v
python3 -m coordination.context_contract --task complex_coding_debugging --phase plan \
  --owned-path client/app.js --owned-path client/hud.js --owned-path client/hud.test.js \
  --owned-path client/index.html --owned-path client/style.css \
  --owned-path tools/capture_submission.py --owned-path tests/test_presentation_capture.py \
  --owned-path docs/submission/STORYBOARD.md --owned-path evidence/submission-capture/README.md \
  --validate-only
```

Do not run browser gameplay against a live server. Static renderer tests and
Playwright capture of a local fixture-only page are allowed if no service or
network is started by the worker. Label every generated artifact truthfully.

## Return

At most 250 words plus owned artifact paths. Report compiler packet hash, files,
tests, capture artifacts and hashes, and the exact live/video blocker. Do not
claim the final video or live Twitch evidence.
