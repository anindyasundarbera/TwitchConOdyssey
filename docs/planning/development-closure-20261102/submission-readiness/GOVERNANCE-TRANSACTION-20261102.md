# Submission-readiness governance transaction (2026-11-02)

Status: completed; live execution and publication are not started.  
Starting HEAD: `bb02cea7e1c260eb30ea9491e7759761c0f290d4`  
Starting tracked diff:
`c215b22a8735e15a88a38d6a64f7d7f9234729ef2db3af394b1b2a233f2420bd`  
Ledger revision: `14` → `15`  
`submission_ready`: **false**

## Requester authorization (verbatim)

> "close the submission readiness"

> "Make it in such a way that Astra review does not get blocked. We can do astra review at the end."

The exact wording is recorded in `docs/planning/STATUS.md` and bound by
`config/directive-policy.json` revision 15. The plan
`SUBMISSION-READINESS-CLOSEOUT-PLAN.md` records the same authorization in its
opening section.

## Decision transition

`live_submission_external_capture` moved from `unresolved` to
`authorized_in_progress` with `authorization_ref:
"live_submission_authorization"`. The decision remains open until real,
current evidence passes and an independent review returns READY. Fixtures,
mocked calls, screenshots alone and configured credentials never satisfy the
live predicates.

Authorized actions:

- implement and test the official Twitch EventSub WebSocket
  `channel.chat.message` boundary;
- run the local authoritative runtime for one bounded live-capture session;
- open one EventSub WebSocket with a validated user token;
- send one consent-safe test message from the authorized account;
- capture rendered desktop `1440×1100` and mobile `390×844` evidence;
- assemble a sanitized under-180-second demo from observed live operation and
  sanitized Codex evidence.

Explicitly excluded: repository push, YouTube upload, Devpost final submission,
credential exposure, automatic retry/substitution and fabricated live or Codex
footage. All three publication booleans remain `false`. The plan compiler gate
remains closed; live execution is a separate bounded route that requires the
exact external inputs listed in the closeout state.

## Review-route separation

`coordination/review_route.py` evaluates the requested route, configured route,
spawn acceptance, reported substitution, serving-attestation availability,
candidate match and substantive verdict separately. Per the requester decision,
missing serving attestation alone is a recorded caveat, not a veto. A rejected
request, reported substitution, candidate mismatch or substantive NOT-READY
fails closed. Tests: `tests/test_review_route.py`.

## Bound files and verification

Tracked diff after the final state/ledger rebind and worker integration:
`8f79e9254950c0e7ed0e2b50cc10a50817ceefa6ad2f3e9e5ef13e302feba16e`

- `config/directive-policy.json` — revision 15, decision/auth records
- `coordination/context_contract.py` — authorized decision validation
- `coordination/review_route.py` — route/substitution/attestation separation
- `tests/test_context_contract.py` — authorization and fail-closed tests
- `tests/test_review_route.py` — route evaluation tests
- `tests/test_gameplan_rules.py` — stale revision assertion corrected to 15
- `docs/planning/STATUS.md` — authorization entry
- `docs/planning/CONTEXT-v2.md` — authorized-in-progress wording

Targeted verification after worker integration:

```text
python3 -m unittest tests.test_context_contract tests.test_review_route \
  tests.test_gameplan_rules tests.test_command_intake tests.test_runtime_integration \
  tests.test_telemetry tests.test_submission_package tests.test_submission_readiness \
  tests.test_twitch_live tests.test_deterministic_kernel tests.test_model_router \
  tests.test_plan_rehearsal tests.test_city_setting tests.test_presentation_capture
Ran 169 tests ... OK
node --test client/hud.test.js
13 tests ... pass
```

Package: 55 artifacts; `MANIFEST.json` SHA-256
`d373461f0ca87bcdfdf6911110eb69a08ff275a4324dc163489fb8eebff778d2`;
`check` verified 55/55. Readiness remains `false` with 53 exact missing/stale
predicates. Sealed roots matched 116 files (`411de7…`) and 170 files
(`9cb21a…`). Secret scan found 0 hits in 1478 scanned files.

The exact configured project name
`home-anindyasundar-bera-Projects-hackathon-TwitchConOdyssey` is absent from
codebase-memory. The indexed near-name project is an older evidence snapshot
and does not contain the current `server/app.py` or `Runtime` nodes. Discovery
therefore used direct source inspection; this coverage gap is recorded rather
than treated as evidence.

## Stop condition

All live and publication work is blocked on the exact external inputs recorded
in `SUBMISSION-CLOSEOUT-STATE.json`. No live token was accessed, no Twitch call
was made, no service was started and no external action occurred.
