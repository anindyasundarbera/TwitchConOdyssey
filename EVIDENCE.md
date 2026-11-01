# Evidence

This file records observed results. `evals/latest.json` and history contain the executable gate output. Passing static checks does not certify real external services.

## Initial probes
- Empty workspace; codebase-memory architecture returned 1 project node / 0 edges.
- `git status --short` failed: not a git repository; `.git` is a read-only placeholder.
- Python 3.14.4, Node v24.21.0; jsonschema, pytest and Playwright Python packages are present.
- `python3 -m server.replay --offline-fixture fixtures/stage.jsonl`: delivered at tick 1933 (96.65 simulated seconds). Digest pinned in `fixtures/expected.json`; replay asserts the golden digest with networking forbidden.
- First unit run: 10 engine/provider/storage checks passed; 3 API tests failed when socket creation raised `PermissionError: [Errno 1] Operation not permitted`. Retained as an environmental blocker. Added in-process HTTP request transport coverage; this does not replace the real browser startup gate.

## Release gate
Run `python3 -m harness.run`. It records exact pass/fail details, source provenance, compact failure context, backlog tasks and checkpoints. Score is percentage of checks passed, not a subjective quality rating. Full release requires 100% and no blocked checks. Browser gate must create real HTTP listener, execute controls and complete delivery using the authoritative engine.

## Unresolved risks
- Sandbox denies sockets; real startup/browser rendering and responsive/audio QA cannot be certified until run outside this restriction.
- Live OpenAI adapter has HTTP contract tests only; no credentials used. Real Twitch Extension identity/EventSub and AWS/IVS integrations remain future work.
- Loopback HTTP is a demo server, not an internet-facing deployment. Viewer identity is client supplied. Authentication and public rate limits are not claimed.
- SQLite disk latency can affect tick scheduling even though provider latency cannot; scheduler metrics expose lateness. Pure tick and slow-provider tests have explicit bounds, but no large production soak has been performed.
- Bounty is integer demo credit accounting; no real payouts. The stylized San Diego layout is not geospatially precise and has not yet been gameplay-verified. Audio is synthesized and opt-in.
