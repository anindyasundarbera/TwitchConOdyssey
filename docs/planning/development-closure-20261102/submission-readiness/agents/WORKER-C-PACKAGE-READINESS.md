# Worker C packet — package, docs, readiness verifier

Task: `development`  
Phase: `plan`  
Coordinator: one; worker: C of 3  
Base HEAD: `bb02cea7e1c260eb30ea9491e7759761c0f290d4`  
Ledger revision: `15`

## Mandatory preflight

Before reading, inferring, editing or testing, run the context compiler with
exactly these owned paths:

```text
python3 -m coordination.context_contract --task development --phase plan \
  --owned-path tools/package_submission.py \
  --owned-path tools/verify_submission_readiness.py \
  --owned-path schemas/submission-readiness.json \
  --owned-path tests/test_submission_package.py \
  --owned-path tests/test_submission_readiness.py \
  --owned-path docs/submission/SETUP.md \
  --owned-path docs/submission/PROJECT-DESCRIPTION.md \
  --owned-path docs/submission/CODEX-SESSION.md \
  --owned-path docs/submission/LICENSING-CHECKLIST.md \
  --owned-path docs/submission/SUBMISSION-METADATA.json \
  --owned-path docs/submission/CLOSURE-DEMO-RUNBOOK.md \
  --owned-path README.md \
  --owned-path docs/DEMO.md
```

Read the emitted packet. Stop on failure. Do not edit `config/**`,
`coordination/**`, `server/**`, `client/**`, `docs/planning/**` or another
worker's paths. Preserve all existing uncommitted edits.

## Authorization boundary

The requester authorized readiness packaging and a mechanical verifier.
`submission_ready` must remain **false** while any live/capture/video/
repository/Astra predicate is missing or stale. Do not push, upload, submit or
claim any external action. Never write tokens, credentials, raw chat or
unhashed handles into docs, manifests or tests.

## Owned paths

- `tools/package_submission.py`
- `tools/verify_submission_readiness.py` (new)
- `schemas/submission-readiness.json` (new)
- `tests/test_submission_package.py`
- `tests/test_submission_readiness.py` (new)
- `docs/submission/**` (judge-facing docs)
- `README.md`
- `docs/DEMO.md`

## Required behavior

1. Keep the existing package artifact set reproducible and extend it
   truthfully for the new Twitch adapter, presentation/capture tooling and
   readiness records. The package must continue to omit credentials and raw
   chat and must fail closed on missing/tampered bytes.
2. Add `tools/verify_submission_readiness.py` that mechanically evaluates a
   readiness record against explicit predicates:
   - starting/final HEAD and tracked-diff hashes;
   - token-validation metadata (no token bytes);
   - EventSub subscription/session metadata and hashed receipt;
   - canonical command/result and visible consequence;
   - desktop/mobile capture hashes and dimensions;
   - accessible, under-180-second video with URL/visibility/observed
     availability;
   - repository URL/commit and clean-checkout setup;
   - project description, Codex session ID, licensing/audio checklist;
   - cleanup/secret scan and sealed-root tripwire;
   - independent review READY with the review-route fields.
   Missing or stale predicates return `submission_ready: false` with exact
   reasons. It must not consult the network or execute gameplay.
3. Write judge-facing setup and project docs: exact clean-checkout commands,
   working feature description, Codex/session evidence, licensing/audio
   checklist, repository/video/Devpost metadata, and the package manifest.
   Correct stale README/demo instructions (old OpenAI/Twitch-simulated claims,
   outdated sandbox/gameplay-deferred language, wrong demo commands).
4. Keep `docs/submission/CODEX-SESSION.md` honest. If the exact session ID is
   unavailable, record it as an explicit missing predicate rather than
   inventing one.
5. Add tests for every readiness predicate and for the fail-closed behavior:
   a complete synthetic record may return true; each missing/stale field must
   return false; publication booleans must not be treated as evidence.
6. The package/manifest may include fixture/offline evidence only with a
   truthful `live_validated: false` label. Do not call an offline capture a
   live Twitch observation.

## Acceptance checks

```text
python3 -m unittest tests.test_submission_package tests.test_submission_readiness -v
python3 -m tools.package_submission build
python3 -m tools.package_submission check build/submission-package
python3 -m tools.verify_submission_readiness --help
python3 -m coordination.context_contract --task development --phase plan \
  --owned-path tools/package_submission.py --owned-path tools/verify_submission_readiness.py \
  --owned-path schemas/submission-readiness.json --owned-path tests/test_submission_package.py \
  --owned-path tests/test_submission_readiness.py --owned-path docs/submission/SETUP.md \
  --owned-path docs/submission/PROJECT-DESCRIPTION.md --owned-path docs/submission/CODEX-SESSION.md \
  --owned-path docs/submission/LICENSING-CHECKLIST.md --owned-path docs/submission/SUBMISSION-METADATA.json \
  --owned-path docs/submission/CLOSURE-DEMO-RUNBOOK.md --owned-path README.md \
  --owned-path docs/DEMO.md --validate-only
```

## Return

At most 250 words plus owned artifact paths. Report compiler packet hash, files,
tests, package manifest digest, readiness result/reasons, and remaining
blockers. Do not claim submission readiness or any external publication.
