# Current authorization and handoff

Updated 2026-11-01.

## Approved by the user in the current turn

- Adopt San Diego as the sole city setting and remap the game.
- Research the official model catalog and select different models by task.
- Have GPT-6 Astra review the game plan.
- Create a shared model-selection/inference boundary and generic plan-rehearsal tooling usable by future development and simulation.
- Rehearse the plan with simulated streamer, viewer, character, stage-operator and attacker perspectives. Findings are design hypotheses, not gameplay observations.
- Implement the smallest reusable deterministic preparation/transport kernel without executing gameplay or selecting unresolved mechanics.
- Implement the durable directive ledger and deterministic context-packet compiler, with bounded plan-only checks. Gameplay remains deferred until a later explicit user authorization after this framework work.
- Migrate active runtime district names, visible map labels, city copy, and current demo documentation from the superseded setting to San Diego. This city-consistency correction does not authorize gameplay simulation.
- Earlier: record five partial rule proposals without gameplay authorization. Superseded for D-01 through D-05 by the current S1 selection below.
- Research and select the exact D-01 through D-05 [S1 simulation profile](S1-SIMULATION-PROFILE.md) as `selected_for_s1_simulation_unverified`; update current plans and context-framework records. This authorizes plan selection and static checks only; separate explicit gameplay authorization is still required.
- Resolve exactly the three critical S1 REVISE findings as selected/unverified design decisions and synchronize the profile, plan/data, ledger, audit and static checks. Preserve the original review and other selected values; this grants no gameplay or runtime authorization.
- **Same-Day Deterministic Remediation Grant (2026-11-01T17:36:28+05:30):** Following the read-only audit checkpoint in [SIMULATION-EVIDENCE-AUDIT.md](SIMULATION-EVIDENCE-AUDIT.md) (`REJECT READY; evidence pipeline requires remediation before development`), the user explicitly authorized one or more fresh deterministic simulation runs under new, non-existing run roots and delegated resolution of `D-06`, `D-07`, `D-08`, booth placement, and other blocking product choices by recorded decision ([DECISIONS.md](DECISIONS.md)). Modification of the preserved rejected run (`artifacts/simulations/full-game/full-game-20261101T102226Z-a8e33043/`), product development, gameplay execution beyond the authorized simulation, and publication remain explicitly excluded.

## Explicitly deferred

Do not run gameplay simulation yet. First expose gaps in the plan, then review and fix the plan, then obtain explicit authorization for gameplay simulation using the revised plan. This turn does not approve runtime gameplay changes, deployment, platform provisioning, or publication.

## Completed in this turn

- San Diego route/product target and user-approved city decision recorded.
- Shared policy, routing/injected-executor helper and plan-only packet/aggregation tools implemented.
- Seven role perspectives produced 35 design findings; Astra's verdict is revise before gameplay.
- A pure coordination kernel now provides canonical commands, seeded/hashed reusable viewer corpora, state diffs/summaries and content-addressed context/result reuse. It does not import or mutate the legacy game runtime.
- Bounded JSON admission now rejects invalid types, cycles, excessive depth, shared-reference expansion, node/container growth, aggregate UTF-8/escaped byte growth and pathological integers before serialization or detachment. Commands, cache bindings/values and deltas have tighter admission budgets.
- Thirty-five targeted kernel/routing/rehearsal tests passed, including generation and validation of a synthetic 100,000-message corpus and mocked checks that rejected inputs never reach serialization; no gameplay, replay, server, browser or harness ran.
- V2 revision 3 selected D-01 through D-05 for a later S1 simulation as unverified, replacing revision 2 partial proposals, and received the independent [S1 REVISE review](S1-ASTRA-REVIEW.md). Revision 4 records design closure of its three critical findings in the [response](S1-ASTRA-REVIEW-RESPONSE.md), with no new Astra verdict. The profile separates project inference from external evidence; D-06 through D-08 retain their gates. Revision 4 still requires fresh version-bound review and has not been gameplay-tested.
- Selected closure: exactly 5.0 active seconds of display-only reward with auto-forward/steering until terminal state; one final delivery settlement ending simulation; turn 3 reaches t=90 deadline, no turn 4. Priority is deadline, phase-close, pause request, sequence commands, then effects; clear_lane, collision, delivery and final settlement order those effects. Hazard proposal/admission closes strictly before planning t=15; committed ID binds the complete [15,20) warning, counter and deduplicated increment. Without commitment, no hazard/warning/increment. Counter/general cutoff stays t=20.
- The compiler now emits a dedicated selected-decisions collection, requires exactly D-01 through D-05 with status/gate/source bindings, and rejects duplicate/cross-list IDs. Remaining unresolved trust decisions are retained; gameplay stays closed.

`gameplay_simulation_enabled` remains false. Active runtime/UI city names now follow the proposed San Diego sequence. The existing route geometry, 25-second implementation cycle, mechanics, fixture timing, and golden digest have not been simulated or reverified against the revised target.

## Context entry points

- `config/model-policy.json`: task-to-model/provider mapping and availability caveats.
- `coordination/canonical_commands.py`, `scenario_inputs.py`, `state_transport.py`, and `content_cache.py`: pure reusable simulation preparation/context-saving primitives.
- `docs/planning/GAMEPLAN-v2.md`, `gameplan-v2.json`, and `CONTEXT-v2.md`: current selected S1 plan and remaining unresolved decisions.
- `docs/planning/S1-SIMULATION-PROFILE.md`: exact selected/unverified controls, hazard caps, account accounting, fictional Hype and clock oracles.
- `docs/planning/S1-ASTRA-REVIEW.md` and `S1-ASTRA-REVIEW-RESPONSE.md`: unchanged revision-3 REVISE critique and revision-4 design response; the response is not a fresh review verdict.
- `docs/planning/research/S1-PLATFORM-EVIDENCE.md` and `S1-SYSTEMS-EVIDENCE.md`: bounded primary-source research and explicit evidence limits; research is not runtime evidence.
- `docs/planning/PLAN-REHEARSAL.md` and `ASTRA-REVIEW.md`: findings, methods, limits and next gate.
- `docs/planning/GAMEPLAN-v1.md`, `gameplan-v1.json`, `CONTEXT.md` and `rehearsal-v1/`: sanitized historical baseline and review evidence; future edits still require explicit approval.
- `docs/planning/SAN-DIEGO-ROUTE.md`: geographic facts versus proposed level compression.
- `docs/research-2026-11-01/PROJECT-CONTEXT.md`: dated product intent; current San Diego city-tour decisions supersede its earlier location language.

Pre-serialization traversal/admission hardening remains complete. D-01 through D-05 are selected for S1, not unresolved: auto-forward three-lane digital steering remains active through reward until terminal state; one bounded center-lane obstacle/turn committed before planning t=15; linked authenticated account-level quotas and a 60% frozen-roster quorum; fictional Hype with capped growth, exact rational allocation and one terminal delivery settlement; 90s active deadline and total clock/pause/cutoff/effect ordering. These are project design inferences, not one-human assurance or verified protections. Safe-danger farming remains possible. Fresh version-bound independent review and later initial-state/geometry/transition, reachability and boundary/settlement fixtures remain required, followed by separate explicit bounded gameplay-simulation authorization. Legacy `100+25/voter` formulas are retired. No later phase starts automatically.

## S1 static verification

`python3 -m unittest tests.test_gameplan_rules tests.test_context_contract tests.test_city_setting -v` passed **35 tests** (8 selected-plan checks, 24 compiler checks, 3 city checks). These are static/local fixture and mocked-boundary checks. They cover the three review-response decisions, exact reward/terminal settlement, total deadline/pause/collision/delivery priority, distinct hazard/counter cutoffs and committed-ID binding, unchanged review digest, selected status/source/gate separation, retained superseded rules, exact mandatory selected IDs, duplicate/cross-list rejection, stale hashes and no runtime/model/network I/O. `python3 -m coordination.context_contract --task complex_coding_debugging --phase plan --validate-only` also passed. No gameplay, server, replay, browser, harness, model inference or live service ran in this revision task. Ledger revision 7 binds current plan, profile, review/response, research and static-test bytes; superseded partial proposals and revision 6 selected rules are retained separately. The original S1 REVISE review SHA-256 remains `29280f55a0d69fd4f8cb06d70f22e7daa23cf0d511c1e0b8eb8a82614c71e530`; this response is no fresh Astra verdict.

## Durable context handoff

`config/directive-policy.json` records active and superseded directives, provenance, precedence, current gate, selected/unverified S1 decisions, remaining unresolved decisions and pinned source bytes. Original user wording unavailable in project records is explicitly marked unavailable; the rules are normalized summaries, not reconstructed quotations. Before each task, use `python3 -m coordination.context_contract --task TASK --phase plan` (repeat `--owned-path` for existing or planned owned files). Existing ownership bindings contain byte hashes; safe absent paths, including nested new directories, are explicitly planned with null hashes. Symlink targets and repository escapes are rejected. The mandatory `bounded_subagents` directive preserves deliberate bounded background research/development, configured model/effort, explicit ownership/acceptance criteria and compact summaries. The compiler emits only relevant rules and file hashes with the configured routing decision and a packet hash; it performs no model/network/gameplay execution. Changed required sources fail closed until their directives and bindings are deliberately reconciled. Hashes do not authenticate authorization. Completing this framework cannot authorize gameplay.

Observed framework verification: `python3 -m unittest tests.test_context_contract tests.test_model_router tests.test_plan_rehearsal tests.test_deterministic_kernel -v` passed 57 tests (22 context-contract tests and 35 existing permitted tests), including delegation retention, planned ownership and duplicate-key rejection for both directive and model policy JSON. This is deterministic local/schema/hash/mocked-boundary evidence only. No gameplay, server, replay, browser, harness, model inference or live service ran.

San Diego consistency verification is a static source/design check only: `tests/test_city_setting.py` guards the whole repository against removed city and landmark terms. The repository-wide source scan returned zero matches; all 37 JSON files parsed; sanitized rehearsal plan/context, packet copies, result hashes, report hashes and v2 baseline binding were checked for consistency. `python3 -m unittest tests.test_city_setting tests.test_context_contract -v` passed 25 tests. Historical plan/rehearsal artifacts were mechanically sanitized and rebound without new agent inference; they are not original-byte evidence after that redaction. No replay, fixture regeneration, gameplay, server, browser, or harness was run during the migration.
