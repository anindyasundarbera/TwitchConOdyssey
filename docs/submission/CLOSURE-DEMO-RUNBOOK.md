# Closure Demo Runbook — Offline Fixture Reproduction (TASK-010)

Scope: this runbook reproduces the **offline fixture** development demo and the
hashed evidence package. It performs **no live Twitch integration, no rendered
viewport/demo-video capture, and no external submission**. `submission_ready`
remains `false`; the unresolved decision `live_submission_external_capture`
(gate `before_live_submission`) stays open. Gameplay service startup
(`server.app`) is not authorized by this runbook — a visual browser demo needs a
separate explicit authorization.

## 1. Clean checkout → fixture demo (offline)

```
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt -r requirements-inference.txt   # if present
python3 -m unittest tests.test_context_contract tests.test_deterministic_kernel \
  tests.test_plan_rehearsal tests.test_model_router \
  tests.test_gameplay_core tests.test_command_intake tests.test_telemetry
node --test client/hud.test.js
```

Fixture evidence without any service:

```
python3 - <<'PY'
from server.engine import AuthoritativeGame
from server.telemetry import TelemetryRecorder
game = AuthoritativeGame(seed=42, initial_lane=1, initial_roster=["fixture_a"])
recorder = TelemetryRecorder(game, "demo-fixture", origin="fixture")
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
the manifest contains no timestamps.

## 3. Work packages (sealed `required_work_packages_order`)

| ID | State |
|---|---|
| WP-01-core-engine-implementation | implemented, offline fixture evidence |
| WP-02-hud-and-mobile-presentation | implemented, offline state tests |
| WP-03-twitch-extension-linking | implemented, offline intake (no live integration) |
| WP-04-codex-booth-telemetry | implemented, privacy-bounded fixture events |
| WP-05-submission-demo-pipeline | implemented; live capture open |

## 4. Failure modes and recovery

- **`Changed required source hash` (compiler):** a `required_paths` file changed
  without a ledger rebind. Reconcile `config/directive-policy.json` in the same
  transaction (revision bump + rebound hash), then re-run `--validate-only`.
- **`missing evidence artifact`:** a packaged path is absent (e.g., stale run
  root). Restore from git; never edit sealed run roots.
- **`hash mismatch` in `check`:** the package was modified after build. Rebuild
  from a clean checkout; do not patch the manifest.
- **unlinked identity / duplicate / expired intake statuses:** expected
  fail-closed behavior; verify linkage and timing windows (t=15 hazard, t=20
  counter).
- **telemetry shows fixture events as live:** stop; this is an INV-FIXTURE-LABEL
  violation. Rebuild with `origin="fixture"` and re-run `test_telemetry`.

## 5. Cleanup

```
rm -rf build/submission-package .venv
```

No repository files under `artifacts/` are written by any step above.

## 6. Readiness statement

Development closure is verified for simulation/offline evidence only. The
packaged record preserves `submission_ready: false` and lists
`live_submission_external_capture` as open. No production, live-service or
submission-readiness claim is made from simulation evidence (DECISION-03).
