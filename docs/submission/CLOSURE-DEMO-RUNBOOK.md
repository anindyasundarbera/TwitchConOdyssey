# Closure demo runbook — offline fixture reproduction

Scope: this runbook reproduces the **offline fixture** development demo and the
hashed evidence package. It performs **no live Twitch integration, no rendered
viewport/demo-video capture, and no external submission**. `submission_ready`
remains `false`; the decision `live_submission_external_capture` (gate
`before_live_submission`) stays open. Gameplay service startup for a visual demo
requires separate explicit authorization.

## 1. Clean checkout → fixture demo (offline)

```
python3 -m venv .venv
. .venv/bin/activate
# The base project has no third-party runtime dependencies. Optional QA extras
# are declared in pyproject.toml and are not required for this offline suite.
python3 -m unittest tests.test_context_contract tests.test_review_route \
  tests.test_submission_package tests.test_submission_readiness \
  tests.test_deterministic_kernel tests.test_plan_rehearsal \
  tests.test_model_router tests.test_gameplay_core tests.test_command_intake \
  tests.test_telemetry
node --test client/hud.test.js
```

Fixture evidence without any service:

```
python3 - <<'PY'
from server.engine import AuthoritativeGame
from server.telemetry import TelemetryRecorder
game = AuthoritativeGame(seed=42, initial_lane=1, initial_roster=["fixture_a"])
recorder = TelemetryRecorder(game, "demo-fixture")
recorder.poll()
for _ in range(20):
    game.step()
recorder.poll()
print(recorder.evidence_bundle()["MANIFEST.json"].decode())
PY
```

Every emitted event is labeled `origin: fixture` and
`live_participation: false`; fixtures never count as live participants.

## 2. Evidence package build + verification

```
python3 -m tools.package_submission build build/submission-package
python3 -m tools.package_submission check build/submission-package
```

The package contains `MANIFEST.json` (artifact SHA-256 map, work-package
tracking, readiness labels) and `files/` copies. Builds are byte-reproducible:
the manifest contains no timestamps. It has two tiers:

- **core artifacts** must exist and are verified byte-for-byte;
- **extension artifacts** (Wave A/B Twitch adapter, capture tooling, storyboard,
  capture evidence) are listed under `artifact_set.pending` when absent. The
  package reports `artifact_set.complete: false`; it never omits or invents
  them.

A package with pending artifacts cannot support submission readiness.

## 3. Mechanical readiness check

```
python3 -m tools.verify_submission_readiness
python3 -m tools.verify_submission_readiness --help
```

The verifier reads `docs/submission/SUBMISSION-METADATA.json`, recomputes local
file hashes and sealed-root tree hashes, checks local `HEAD` and
`git diff HEAD --binary`, and prints exact failure reasons. It does not use the
network, start a service or execute gameplay. It ignores publication booleans as
evidence.

Current result: `submission_ready: false`. The missing predicates include live
token validation, EventSub receipt, live command consequence, desktop/mobile
captures, final video, repository URL/commit, licensing/audio, cleanup/secret
scan, complete package and independent READY review.

## 4. Work packages (sealed `required_work_packages_order`)

| ID | State |
|---|---|
| WP-01-core-engine-implementation | implemented, offline fixture evidence |
| WP-02-hud-and-mobile-presentation | implemented, offline state tests |
| WP-03-twitch-extension-linking | offline intake implemented; live EventSub adapter pending integration |
| WP-04-codex-booth-telemetry | implemented, privacy-bounded fixture events |
| WP-05-submission-demo-pipeline | package/readiness tooling implemented; live capture and final video open |

## 5. Failure modes and recovery

- **`Changed required source hash` (compiler):** a `required_paths` file changed
  without a ledger rebind. Reconcile `config/directive-policy.json` in the same
  transaction (revision bump + rebound hash), then re-run `--validate-only`.
- **`missing core evidence artifact`:** a packaged path is absent (e.g., stale
  run root). Restore from git; never edit sealed run roots.
- **`artifact_set incomplete` / `pending`:** Wave A/B artifacts are not in the
  tree. Integrate them, rebuild, and re-check; do not remove them from the
  catalog to make the package pass.
- **`hash mismatch` in `check`:** the package was modified after build. Rebuild
  from a clean checkout; do not patch the manifest.
- **readiness reason `candidate.*_stale`:** `HEAD` or the tracked diff changed
  after the record was authored. Re-freeze the candidate and re-evaluate; do not
  rewrite the recorded hash to match a moving worktree.
- **readiness reason `live.*`:** no observed live Twitch evidence exists. A
  fixture, mocked transport or configured credential cannot fix this.
- **readiness reason `review.*`:** the independent review is missing, stale,
  substituted or not READY. Do not flip readiness manually.
- **unlinked identity / duplicate / expired intake statuses:** expected
  fail-closed behavior; verify linkage and timing windows (t=15 hazard, t=20
  counter).
- **telemetry shows fixture events as live:** stop; this is an INV-FIXTURE-LABEL
  violation. The offline recorder has no live-origin argument; re-run
  `test_telemetry` and inspect the authoritative state envelope.

## 6. Cleanup

```
rm -rf build/submission-package .venv
```

No repository files under `artifacts/` are written by any step above. Never
delete or rewrite a sealed run root.

## 7. Readiness statement

Development closure is verified for simulation/offline evidence only. The
packaged record preserves `submission_ready: false` and lists
`live_submission_external_capture` as open. No production, live-service or
submission-readiness claim is made from simulation evidence.
