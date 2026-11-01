# TwitchCon Odyssey

The approved setting is now **San Diego**. See the [current planning status](docs/planning/STATUS.md), [proposed v2 game plan](docs/planning/GAMEPLAN-v2.md), [Astra review](docs/planning/ASTRA-REVIEW.md), and [shared model routing](docs/planning/MODEL-ROUTING.md). The plan rehearsal is complete; gameplay simulation is explicitly deferred.

Runtime city labels, map copy, and route names now follow the proposed San Diego sequence. The route geometry and existing mechanics have not yet been gameplay-simulated or certified against the revised plan. Do not run them until a later explicit simulation prompt.

A local canvas co-op crisis game with a deterministic stage demo, authoritative engine and evidence-driven development harness. Python 3.11+; no runtime dependencies or external credentials.

```bash
python3 -m server.app --offline-fixture fixtures/stage.jsonl
```

Open **http://127.0.0.1:8000**. The fixture supplies chat while you can also vote with buttons or natural language. Planning lasts 20 seconds, resolution lasts 5. The pinned fixture delivers the build in about 97 seconds. Toggle sound after page load. Bullet time freezes the inspector while the engine keeps running. Refresh retains viewer identity; restart the server to start a new match. Ctrl-C stops it.

For a bot-backed match without fixture chat:

```bash
python3 -m server.app
```

For deterministic replay without a browser or listening socket:

```bash
python3 -m server.replay --offline-fixture fixtures/stage.jsonl
python3 -m unittest discover -s tests -v
python3 -m harness.run
```

The harness exits nonzero for failed or environmentally blocked checks. Outputs are `evals/latest.json`, `evals/history.jsonl`, `harness/context.json`, `harness/checkpoints.jsonl` and updated backlog. Optional browser QA: `python3 tests/browser_e2e.py` requires Playwright and an installed Chromium (`pip install '.[qa]'` in a suitable environment; `playwright install chromium`). No installation is needed to play.

Optional live OpenAI parsing: export `OPENAI_API_KEY` and `OPENAI_MODEL` (see `.env.example`) and run `python3 -m server.app --provider openai`. Never combine live mode with `--offline-fixture`. Live parsing is implemented and tested with a mock HTTP response; no credentialed API call has been verified. Twitch and AWS services are simulated; all bounty values are demo credits.

The current execution sandbox denies socket creation, so HTTP startup/browser E2E cannot be certified here. Pure replay and in-process request handling can still run. See [EVIDENCE.md](EVIDENCE.md), [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [BACKLOG.md](BACKLOG.md), and [docs/DEMO.md](docs/DEMO.md).
