# Plan rehearsal result

**Result: revise before gameplay.** The document-only exercise produced **35 findings across seven perspectives**. This is synthetic design critique, not real player research, exploit execution, model-latency measurement, load testing or gameplay evidence.

## What actually ran

- One Luna mapper proposed the San Diego plan and sourced its geographic anchors.
- One Luna agent reviewed streamer, viewer, character and stage-operator perspectives together; these are four perspectives, not four independent reviewers.
- A separate Luna agent challenged the plan as a red team.
- Sol reviewed technical security contracts and implemented the shared helpers.
- Astra independently reviewed v1 and the security critique. The other completed role results were not available when Astra inspected them; this report combines them afterward.
- A script validated exactly seven complete role-result schemas, matching plan/policy/context hashes and declared models. It cannot independently authenticate caller-supplied model identity. [Dispatch record](rehearsal-v1/dispatch.json), [combined results](rehearsal-v1/report.json), [Astra review](ASTRA-REVIEW.md)

Sanitized baseline SHA-256: `ee0627b31df7a43ea7c9daba47821a58c8e52e0bfdabd430702329b1685d21fa`. At the user's explicit request, stored location terminology was mechanically removed from the plan, context and packet copies; dependent hashes were rebound without rerunning any agent. Review findings are retained, but these files are no longer original-byte evidence. [v1 JSON](gameplan-v1.json)

## Consolidated issues and dispositions

| Issue | Finding examples | Disposition |
| --- | --- | --- |
| Streamer has no concrete decision/counter timeline | ST-01–03, CH-01–03, AST-01 | Human controls, warnings, phase movement and collision/recovery decision required. No veto or checkpoint added automatically. |
| Refresh/channel-switch/Sybil influence | VW-01–03, ATT-01, SEC-01 | Require an explicit eligibility and cross-channel accounting contract. Account-level limits do not prove person-level fairness. |
| Cohort normalization can amplify coordinated minorities | ATT-02, AST-02 | Preserve bounded weighting/defensive balancing; select roster, denominator, tie and bot rules before testing. |
| Bots can create value even when excluded from payout | ATT-03, SEC-04, AST-03 | Restore no-bot-created-bounty requirement and immutable origin. Do not adopt per-event manual approval as a new game feature. |
| Repeated safe-looking hazards can accumulate into denial | ATT-04, AST-04 | Critical omission repaired in v2 requirements: explicit cumulative anti-stun-lock/damage limits; numerical bounds still pending. |
| Timely messages can produce late or injected proposals | ATT-05, SEC-02, AST-05 | Restore asynchronous authority and no silent rollover; choose precise cutoff/expiry semantics. |
| Failover/replay can double effects or rewards | ATT-06, SEC-05, AST-06, OP-01 | Specify atomic ownership and durable deduplication/recovery before resilience testing. |
| Data-only hotfixes can still violate safety or replay old rules | SEC-03, AST-10 | Require trusted approval/version/base binding and independent invariant checks; design remains unvalidated. |
| Fixture/AI/vendor visuals can overstate reality | OP-02–04, AST-07–09 | Restore truthful labels, measured traces, actor authority and evidence distinctions. |
| Offline acceptance can be mistaken for hackathon readiness | AST-11 | Separate plan, offline-slice, live-integration and submission gates. |

[Proposed v2](GAMEPLAN-v2.md) repairs omissions without selecting controls, balancing formulas or privileged operations. It is **not a second-reviewed or gameplay-validated plan**.

## Verified tooling, with limits

`python3 -m unittest tests.test_model_router tests.test_plan_rehearsal -v` passed **10 targeted tests**. They cover routing, disabled profiles, budgets, stale/incomplete role results and rejection of gameplay scope before executor calls. Static inspection found no gameplay/runtime imports in `coordination/`. No existing gameplay suite, server, replay, browser match or `harness.run` was executed.

The routing helper returns policy-bound decisions. Its injected executor can be reused by development and future simulation adapters; it does not install models, create provider credentials, spawn Codex agents automatically or establish live integration. The current Codex execution path and unavailable/disabled API choices are documented in [MODEL-CATALOG.md](MODEL-CATALOG.md).

## Next human gate

Resolve player agency, survival/recovery, audience fairness, reward settlement and clock ordering in v2. Then authorize a bounded gameplay exercise with an explicit district, scenarios, expected outcomes, seed/time policy and stop condition. That authorization has not been given.
