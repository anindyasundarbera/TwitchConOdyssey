# TwitchCon Odyssey

A local, deterministic Twitch co-op crisis game set on a stylized **San Diego**
route. The streamer steers a shared build while chat proposes hazards and
counter-commands; the authoritative engine, not a model, owns every state
transition. Python 3.11+ standard library only.

> **Submission status:** `submission_ready: false`. The repository has no
> observed live Twitch session, rendered desktop/mobile capture, final video,
> public repository URL, chosen license or independent READY review yet. See
> [`docs/submission/SUBMISSION-METADATA.json`](docs/submission/SUBMISSION-METADATA.json).

## What works now

- **Deterministic match:** 90-second, three-turn clock contract; 20 Hz target;
  planning, resolution and reward phases; pause and terminal settlement.
- **San Diego route:** Little Italy, North Embarcadero, Gaslamp Quarter and the
  convention center to a fictional main stage.
- **Authoritative HUD:** route progress, committed-hazard state, one
  plain-language next action, eligible-account audience counts and fictional
  Hype settlement. The HUD has distinct `live`, `fixture` and `disconnected`
  modes and never infers live status from a query parameter.
- **Bounded intake:** linked account subjects, one influence per subject per
  turn, receipt deduplication, phase/expiry validation and fail-closed rejection.
- **Evidence:** fixture-labelled telemetry, a reproducible SHA-256 package and a
  mechanical readiness verifier.

## What is not yet true

- The official Twitch EventSub `channel.chat.message` adapter is implemented
  behind a transport-injectable boundary and covered by fake-transport tests,
  but **no live token validation, subscription or chat receipt has been
  observed** in this tree.
- There are no **live** rendered `1440x1100` desktop or `390x844` mobile
  captures and no final YouTube demo under 180 seconds. Offline fixture and
  disconnected renders exist under `evidence/submission-capture/` and are
  explicitly labelled as non-live evidence.
- No public repository URL, Devpost URL, final commit or repository license is
  bound.
- No independent Astra review of the final candidate exists.

Fixtures, mocked transports, screenshots alone and configured credentials never
satisfy a live predicate.

## Quick start (offline fixture)

```bash
python3 -m server.app --offline-fixture fixtures/stage.jsonl
```

Open <http://127.0.0.1:8000>. The page must say **LOCAL FIXTURE** / **Offline
fixture (not live Twitch activity)**. Use the on-screen steer buttons, sound
toggle and Bullet time. The fixture is the only verified runnable demo.

Deterministic replay without a browser or listening socket:

```bash
python3 -m server.replay --offline-fixture fixtures/stage.jsonl
```

## Verify the evidence chain

```bash
python3 -m unittest \
  tests.test_context_contract tests.test_review_route \
  tests.test_submission_package tests.test_submission_readiness -v
python3 -m tools.package_submission build build/submission-package
python3 -m tools.package_submission check build/submission-package
python3 -m tools.verify_submission_readiness
```

`check` verifies every declared artifact and reports any absent Wave A/B
artifact as `pending`; `verify_submission_readiness` prints exact reasons and
keeps `submission_ready: false`.

## Documentation

- [Clean-checkout setup](docs/submission/SETUP.md)
- [Project description](docs/submission/PROJECT-DESCRIPTION.md)
- [Codex session record](docs/submission/CODEX-SESSION.md)
- [Licensing/audio checklist](docs/submission/LICENSING-CHECKLIST.md)
- [Closure demo runbook](docs/submission/CLOSURE-DEMO-RUNBOOK.md)
- [Demo script](docs/DEMO.md)
- [Current planning status](docs/planning/STATUS.md)

## Configuration and privacy

No runtime provider or credential is required. The runtime constructs the
deterministic mock provider; it has no `--provider` switch and no path to a
network model. Keep any future token in an ignored local environment file,
never in Git, docs, tests or packaged evidence. Raw chat and unhashed handles
are not packaged.

## License

No `LICENSE` file exists yet. The owner must choose a license before
publication; see the [licensing checklist](docs/submission/LICENSING-CHECKLIST.md).
