# Final-review remediation plan

Date: 2026-11-02  
Source verdict: `review/FINAL-INDEPENDENT-REVIEW.json` (`NOT-READY`)  
Current requester instruction (recorded verbatim): “Give me plan for remediation and close the development”  
Planning packet: `a87d4e6c5ea2651eb260daeb96250af573b4d4d735003631399bd886e6b45095`

This wave addresses the five final-review findings without modifying sealed run
roots or claiming live/submission readiness. It authorizes repository-local
development and targeted in-process verification only. It does not authorize
`server.app`, `server.replay`, browser gameplay, `harness.run`, live Twitch,
credentials, external network calls, capture, deployment, publication, or
submission. `submission_ready` remains false.

## Ordered remediation

| ID | Finding | Owned paths | Acceptance |
|---|---|---|---|
| R1 | Authoritative runtime/HUD integration | `server/app.py`, `client/app.js`, `client/hud.js`, `client/index.html`, focused tests | Runtime constructs `AuthoritativeGame`; `/api/state` carries an engine-owned evidence label; the browser emits and renders `odyssey:state`; callers cannot select live mode. |
| R2 | Leave/quorum semantics | `coordination/full_game_simulator.py`, `server/intake.py`, focused tests, `config/directive-policy.json` | `audience.leave` is canonical and becomes effective at the next roster freeze; the quorum denominator drops then, never mid-turn. The simulator hash is rebound in the ledger in this same, exclusive governance transaction. |
| R3 | Atomic, bounded intake state | `server/intake.py`, focused tests | Receipt dedupe, sequencing and rate-limit admission are serialized; receipt and per-subject tracking are bounded; rejected floods cannot grow memory without limit. |
| R4 | Evidence provenance | `server/telemetry.py`, runtime integration, focused tests | Telemetry derives fixture/live status from an immutable engine-issued evidence context; arbitrary constructor strings cannot mint `live_participation: true`. |
| R5 | Reproduction/package completeness | `tools/package_submission.py`, `docs/submission/CLOSURE-DEMO-RUNBOOK.md`, focused tests | Clean-checkout commands reference only present inputs; every work-package evidence path is required and included in the artifact hash map; missing evidence fails closed. |
| R6 | Verification and closure | this directory, review outputs | Targeted checks pass, sealed-root tripwire is unchanged, the exact committed candidate receives a fresh independent `READY`, and only then is development closure recorded. |

## Transaction rules

1. Compile a fresh `development` packet with exact owned paths before each code
   transaction; stop on stale bindings or conflicts.
2. Execute R2 separately because it changes the ledger-bound simulator. Apply
   the simulator edit and ledger revision/hash rebind as one exclusive change.
3. Preserve the original NOT-READY review verbatim. A new review uses new files
   and records its exact packet/candidate hash and actual route.
4. Do not edit historical sealed evidence. New verification is append-only in
   `REMEDIATION-VERIFICATION.md`.
5. A fresh independent review is mandatory. If the configured
   `codex_subagent/gpt-6-astra/high` route cannot be invoked, record the gate as
   unsatisfied and stop; do not claim closure.

