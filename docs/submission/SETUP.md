# Clean-checkout setup

This is the judge-facing setup for the repository candidate. The public
repository URL and final commit are **not yet bound**; both are explicit
missing predicates in
[`SUBMISSION-METADATA.json`](SUBMISSION-METADATA.json). Do not treat the
placeholders below as a published destination.

## Requirements

- Python 3.11 or newer (standard library only; no runtime dependencies).
- A local shell that permits loopback HTTP (the offline fixture demo uses
  `127.0.0.1:8000`).
- Optional for client tests: Node.js 20 or newer.
- Optional only for rendered capture work: Playwright plus Chromium. Neither is
  needed to run or review the offline fixture demo.

## Exact clean-checkout commands

Once the repository URL and final commit are supplied, run:

```bash
export REPOSITORY_URL="<pending-public-repository-url>"
export FINAL_COMMIT="<pending-final-commit>"

git clone "$REPOSITORY_URL" twitchcon-odyssey
cd twitchcon-odyssey
git checkout "$FINAL_COMMIT"
git status --porcelain
```

`git status --porcelain` must print nothing. A dirty checkout means the
reviewed candidate bytes are not the bytes you are running.

## Verify the offline evidence chain

```bash
python3 -m unittest \
  tests.test_context_contract tests.test_review_route \
  tests.test_submission_package tests.test_submission_readiness -v
python3 -m tools.package_submission build build/submission-package
python3 -m tools.package_submission check build/submission-package
python3 -m tools.verify_submission_readiness
```

`check` verifies the package's core bytes and reports any pending Wave A/B
integration artifacts. `verify_submission_readiness` recomputes local hashes
and prints `submission_ready: false` while any predicate is missing. It does not
use the network, start a service or run gameplay.

The full test suite includes behavioural and browser checks and is intentionally
not part of this bounded clean-checkout verification.

## Run the offline fixture demo

```bash
python3 -m server.app --offline-fixture fixtures/stage.jsonl
```

Open <http://127.0.0.1:8000>. The page must label the session **LOCAL FIXTURE**
or **Offline fixture (not live Twitch activity)**. Never describe this mode as
live Twitch participation.

Deterministic replay without a browser or listening socket:

```bash
python3 -m server.replay --offline-fixture fixtures/stage.jsonl
```

## Live Twitch mode

Live Twitch mode requires a validated user OAuth token with at least
`user:read:chat`, an authorized broadcaster/chat account pair, and one observed
`channel.chat.message` EventSub receipt. No token, client secret or raw chat is
committed to tracked files or included in the package. If those inputs are
absent, the runtime must stay in offline/disconnected mode and the HUD must say
so. Setup evidence for live mode is currently **missing**; see
`SUBMISSION-METADATA.json`.

## Troubleshooting

- `Address already in use`: stop the other process on port 8000 or choose
  another local port; the demo needs loopback only.
- `python3: command not found`: install Python 3.11+ and rerun with
  `python3.11` or newer.
- Package `hash mismatch`: rebuild from the reviewed checkout; never patch
  `MANIFEST.json`.
- `pending` artifacts reported by `check`: one or more declared Wave A/B
  integration files are absent from this tree. That is an honest incomplete
  package, not a passing submission.

## Licensing

No repository `LICENSE` file exists yet. The owner must select a license before
publication; see [`LICENSING-CHECKLIST.md`](LICENSING-CHECKLIST.md).
