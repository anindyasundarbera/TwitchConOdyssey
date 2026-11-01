# Stage runbook

1. From repository root run `python3 -m server.app --offline-fixture fixtures/stage.jsonl` and open http://127.0.0.1:8000. Keep terminal visible for startup errors. Use a normal local shell that permits loopback sockets.
2. Frame the canvas and bounty. Explain the shared build, four rival squads and 20s planning / 5s resolution latency buffer.
3. Click a sponsor ability or type `patch the build and boost`. Show chat → structured proposal → authoritative execution. Provider label must remain “deterministic mock” in the offline demo.
4. At the first resolution, toggle Bullet time. Record the frozen tool-call trace while the real match continues. Resume the inspector.
5. Enable sound: planning square-wave arpeggios become synthwave action pulses and a festival melody at delivery.
6. Follow the stylized San Diego route through Little Italy / North Embarcadero, the Embarcadero waterfront / Marina, Gaslamp Quarter, and the San Diego Convention Center to the fictional Main Stage. The existing fixture timing and golden digest must be reverified after this city migration; human votes can change the outcome.
7. Show final broadcaster/viewer credit split. These are simulated credits, with no financial transfer.

## Recovery
- No internet or API key needed. If the browser/server cannot start, run `python3 -m server.replay --offline-fixture fixtures/stage.jsonl` to show the pinned simulation result. This verifies engine behavior, not browser rendering.
- Restart the process to replay. New match ID avoids overwriting the old journal.
- Inspect `.runtime/game.sqlite` using Python sqlite3; raw chat, proposal and validation records remain local. Remove only your own demo database when retention is no longer needed.
- Before stage use, run `python3 -m harness.run` in an environment permitting sockets and Chromium. Do not describe the entire MVP as verified until the gate passes.
