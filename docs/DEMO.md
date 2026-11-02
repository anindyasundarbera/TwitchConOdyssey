# Demo script

Status: offline fixture demo only. The final submission video — observed live
Twitch operation plus sanitized Codex evidence, under 180 seconds — does not
exist yet. Do not substitute fixture footage for live footage.

## Offline fixture demo (verified path)

```bash
python3 -m server.app --offline-fixture fixtures/stage.jsonl
```

Open <http://127.0.0.1:8000>. Keep the terminal visible for startup errors. The
page displays **LOCAL FIXTURE** and **Offline fixture (not live Twitch
activity)**.

### In-Game Controls & Synthwave Interface
1. **Fullscreen & Start Briefing:** Dismiss the start modal by clicking **Engage Link / Fullscreen** or pressing **[Space]** / **[Enter]**.
2. **Steering Controls:** Use **[A]** / **[D]** or **[←]** / **[→]** keyboard keys, or the labelled on-canvas touch controls to shift lanes.
3. **Avionics Flight HUD:** Located in the top-left corner, showing real-time speed (100/88 u/s), active district, phase countdown (20s planning / 5s resolution), and Hype pool.
4. **Pause & Settings:** Press **[ESC]** or click **PAUSE [ESC]** to open the in-game settings drawer. From here you can toggle synthesized Web Audio (**[M]**) and Bullet-Time inspection.
5. **Landmark Waypoint Gantries:** Watch the runner navigate through Little Italy, North Embarcadero, Gaslamp Quarter, and the San Diego Convention Center to the Fictional Main Stage.
6. **Holographic Hazards & Lasers:** Hazards display warning strobes, caution chevrons, and red barrier lasers. Countered hazards transition to emerald green pass-through gateways.
7. **Terminal Settlement:** Upon delivery at 100% progress, view the final 50/50 broadcaster/viewer Hype split with zero monetary transfer.

## Simulating Real-Time Viewer Participation

While the server is running, execute the viewer simulation in a separate terminal:

```bash
python3 tools/simulate_demo_match.py
```

This script drives live simulated viewer activity against the running engine:
- Simulates 5 distinct audience personas submitting chat proposals (`patch left`, `boost right`, `shield`) to `/api/chat`.
- Demonstrates rate limiting (0.3s cooldown) and planning phase cutoff enforcement.
- Dispatches streamer steering evasion commands to `/api/command`.
- Logs structured telemetry evidence to `evidence/ui-readiness/20261102T161855Z/VIEWER-ACTION-SIMULATION.json`.

Recovery: if the browser or server cannot start, run

```bash
python3 -m server.replay --offline-fixture fixtures/stage.jsonl
```

That verifies deterministic engine behavior only; it does not verify browser
rendering or live Twitch operation.

## What the final live video must show

The final video is blocked until the coordinator performs the authorized live
session. It must show, in order:

1. a validated Twitch identity and one observed `channel.chat.message` receipt;
2. the linked subject and canonical command admission;
3. the authoritative engine result and a visible HUD consequence;
4. an honest live/disconnected label transition;
5. a sanitized Codex-development segment using only owned or synthesized audio;
6. total duration under 180 seconds, hosted publicly or unlisted on YouTube.

No token, client secret, raw chat, unhashed handle or fixture clip may appear in
the final video. Missing live footage is a hard blocker, not a reason to
rehearse with a fixture and relabel it.

## Capture requirements

- Desktop viewport: `1440x1100`.
- Mobile viewport: `390x844`, no horizontal overflow, controls reachable.
- Capture only from an observed live session for readiness evidence; label any
  offline rehearsal as `fixture`/`rehearsal`.
- Record SHA-256 and dimensions in the readiness record.

## What not to run

Do not start the live service, call Twitch, upload a video or submit to Devpost
without the corresponding explicit authorization. The offline runbook does not
authorize those actions.
