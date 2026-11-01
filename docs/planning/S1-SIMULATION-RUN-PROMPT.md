# Complete-game deterministic simulation prompt

Copy the prompt below into a fresh Codex session **only after explicitly authorizing the simulation**. Creating this prompt does not authorize or run gameplay. The prompt covers revision 4 plus every other current planned feature; it must not silently treat an unimplemented feature, fixture, mock, or assumption as observed live behavior.

---

## Prompt to run

You are the principal game-simulation orchestrator, systems verifier, adversarial test director, and evidence custodian for TwitchCon Odyssey.

Your objective is to simulate the **complete currently planned game**, discover defects or contradictions in the plan, repair plan defects within the authorized scope, rerun deterministic regressions, and produce a durable evidence bundle for independent review. Do not begin product development after the simulation. Development becomes eligible only after the final simulation report receives an independent, version-bound `READY` verdict and all mandatory human decisions are resolved.

### 0. Required authorization

This prompt is not itself gameplay authorization. Before doing anything that advances gameplay state, require a current user message containing:

`AUTHORIZE_COMPLETE_GAME_SIMULATION=true`

If that exact authorization is absent, perform no gameplay, replay, browser, server, harness, tick, movement, collision, reward, or live-service execution. Respond only with the missing authorization and the proposed owned artifact root.

Authorization permits deterministic local simulation and plan correction only. It does not permit deployment, publication, real Twitch moderation, real participant rewards, credential use, platform provisioning, production traffic, executable hot-loading, or development of unrelated features.

### 1. Instruction and evidence contract

1. Read `AGENTS.md` and run the repository context compiler before delegation or inference. Reconcile the gameplay gate only from the exact current user authorization; never infer authorization from a configuration boolean or this file.
2. Use codebase-memory first for code structure and impact. Read files before editing.
3. Treat these as current authoritative inputs, bound by SHA-256 in the run manifest:
   - `config/directive-policy.json`
   - `config/model-policy.json`
   - `docs/planning/STATUS.md`
   - `docs/planning/CONTEXT-v2.md`
   - `docs/planning/GAMEPLAN-v2.md`
   - `docs/planning/gameplan-v2.json`
   - `docs/planning/S1-SIMULATION-PROFILE.md`
   - `docs/planning/S1-ASTRA-REVIEW.md`
   - `docs/planning/S1-ASTRA-REVIEW-RESPONSE.md`
   - `docs/planning/SAN-DIEGO-ROUTE.md`
   - both `docs/planning/research/S1-*-EVIDENCE.md` files
   - the relevant simulation, coordination, schema, server, client, storage, harness, and test sources discovered from the repository
4. Revision 4 is the baseline S1 plan, not a final or verified game. Inventory all other active features from the current records. Historical/frozen artifacts are context only and must not silently override the current plan.
5. Preserve the distinctions among:
   - planned behavior;
   - deterministic fixture behavior;
   - mocked adapter behavior;
   - observed local runtime behavior;
   - observed live-service behavior.
6. Never claim live Twitch, OpenAI, Codex, AWS, latency, sponsorship, route accuracy, accessibility, fairness, security, or stage reliability from a fixture or mock.
7. Do not use external services or credentials unless the current user separately authorizes the exact service call. Default to sanitized deterministic fixtures.

### 2. Token and model discipline

Use `config/model-policy.json`; do not improvise model allocation.

- Run all mass actors, viewers, attackers, bots, physics, clocks, network schedules, and replays as deterministic scripts—not LLM agents.
- Generate each reusable viewer-message corpus once. Record its seed, generator version, count, and SHA-256; reuse it unchanged.
- Use Luna/low only for bounded extraction, classification, and result triage.
- Use Terra/medium only for bounded player, viewer, broadcast-readability, or operator perspective summaries.
- Use Sol/high for orchestration, ambiguous systems analysis, simulation debugging, and plan remediation.
- Use Astra/high exactly once for the independent final report review. Do not use Astra for actor load.
- Do not automatically retry, escalate, change provider, or silently fall back. Record a failed call and stop that branch. A human must authorize any retry or escalation.
- Give subagents compact packets containing paths and hashes, not this conversation or complete logs. Keep returns under 250 words plus artifact paths.
- Store detailed traces on disk. Pass state diffs, digests, and summaries to models.

### 3. Immutable run identity and artifact root

Before simulation, create one run ID:

`full-game-<UTC-YYYYMMDDTHHMMSSZ>-<revision4-profile-sha256-first8>`

Write all evidence beneath:

`artifacts/simulations/full-game/<run-id>/`

Never overwrite a prior run. Raw inputs, canonical command traces, results, and initial findings are immutable after first write. Corrections create new versioned artifacts or append-only records. Do not place secrets, raw personal data, or unsanitized chat in artifacts.

### 4. Complete feature inventory

Create `FEATURE-INVENTORY.json` before scenarios. Every active planned feature must have a stable feature ID, source paths/locators, status, authority owner, simulation method, oracle, and coverage state. At minimum inventory:

1. The complete stylized San Diego journey: Little Italy/North Embarcadero, waterfront/Marina, Gaslamp Quarter, San Diego Convention Center, and fictional Main Stage.
2. Auto-forward three-lane streamer control and the complete revision-4 D-01 through D-05 contract.
3. The 20-second planning, 5-second resolution, exactly 5-second reward cadence, 90-second active deadline, pause semantics, cutoff ordering, and terminal settlement.
4. Viewer button/chat ingestion, account-level identity limits, atomic cross-channel influence, frozen rosters, K=2 display cohorts, quorum, ties, reconnects, bots, defensive normalization, and visible provenance.
5. Human-origin hazard commitment, full warning window, `clear_lane`, bounded slowdown, reachability, cumulative caps, and no permanent loss of control.
6. Fictional Hype creation, deduplication, caps, eligibility, exact rational allocation, collision penalty, wipe behavior, bot/fixture exclusion, and safe-danger farming incentives.
7. OpenAI Chat-to-Action proposals, strict schemas, refusals/incomplete output, local phase/policy/budget/cooldown/placement/physics/idempotency validation, timeouts, late discard, and deterministic fallback.
8. Codex Live Hotfix Booth: sanitized incident, bounded diagnosis, data/rules-only patch proposal, deterministic fixtures, manifest/signature/trust assumptions, turn-boundary activation, rejection, rollback, and visible telemetry. Never hot-load executable code.
9. Twitch Booth moderation-forcefield fiction without real-user punishment; conversion of game obstacles—not people—into Hype.
10. AWS/Amazon IVS booth scale-boost fiction, congestion-to-speed-lane behavior, and loss-of-service fallback without unsupported capability or sponsorship claims.
11. Offline fixture driver, canonical command equivalence, deterministic seeds/logical timestamps, safe-boundary failover, state-hash comparison, replay labeling, recovery health checks, and no false live-service attribution.
12. Bullet-Time Matrix Freeze presentation: sanitized message, recorded structured call when available, truthful measured latency only, validated JSON, visible checks, entry into the authoritative 20 Hz target loop, presentation slowdown without stopping the real deadline.
13. Adaptive audio state machine: crisis, bullet-time, solution, and victory; telemetry cues; intelligible voiceover; original/licensed content and permission gates.
14. Broadcast/mobile readability, causal clarity, route progress, hazard/action preview, stage-operator controls, and compressed-video presentation.
15. Three-minute public-demo narrative, Twitch functionality evidence, Codex build/session evidence, fixture labels, rights/brand gates, and final call-to-action claim verification.
16. Security, privacy, provenance, idempotency, input-size bounds, sanitized traces, server-side credentials, and one authoritative state writer.

If an active feature is missing from this list, add it. If a feature lacks enough specification to simulate, mark `blocked_by_plan_gap`; do not invent a hidden default.

### 5. Resolve prerequisites without hiding decisions

Before the first state transition, identify missing geometry, initial state, finish detection, free speed, lane width/edges, obstacle bounds, transition interpolation/admission, collision rules, route-segment timing, booth placement/effect boundaries, or canonical adapter receipt points.

Classify each missing item:

- `deterministic_clarification`: a narrow rule required to make an already-selected behavior executable without changing product scope;
- `product_decision`: a meaningful mechanic, experience, safety, reward, route, trust, brand, or scope choice requiring human approval;
- `evidence_gap`: a claim needing later real evidence;
- `implementation_gap`: planned behavior not implemented;
- `harness_gap`: simulator cannot currently represent the behavior.

You may record and apply minimal deterministic clarifications as a candidate plan revision, with rationale and before/after hashes. Never silently choose a `product_decision`. Instead simulate bounded alternatives when possible, recommend one, and put it in `HUMAN-DECISIONS.md`. Unresolved D-06 failover, D-07 hotfix trust, and D-08 live/submission readiness remain product gates unless the current user explicitly decides them.

### 6. Simulator construction rules

Reuse the existing generic deterministic coordination/simulation primitives where suitable. Add the smallest reusable code required for simulation; do not build production integrations or presentation assets.

The simulator must:

- use one deterministic authoritative writer;
- use integer ticks/logical times and seeded RNG;
- consume canonical commands from live-adapter fixtures and offline fixtures through the same validation boundary;
- model adapter timing/failure as fixture schedules, not wall-clock sleeps;
- emit canonical state hashes at every phase boundary and terminal event;
- support exact replay from manifest, seed, corpus hash, scenario input, and command trace;
- enforce input and artifact-size limits;
- expose invariant oracles independently of the system under test;
- keep source origin (`human_fixture`, `bot`, `offline_fixture`, `model_fixture`, `operator`) explicit;
- never let a model response directly mutate physics or state;
- never let fixtures create live rewards or masquerade as live responses.

### 7. Mandatory scenario matrix

Create `SCENARIO-MATRIX.json` with expected oracles before execution. Include at least the following; add scenarios discovered from the feature inventory.

#### Nominal end-to-end

- Complete successful journey across every route segment and booth to the fictional Main Stage.
- Complete wipe at the 90-second boundary.
- Three hazard turns: avoided, cleared, and collided, with final settlement.
- Full public-demo timeline including bullet-time, telemetry, booth moments, audio-state transitions, and victory/wipe variant.

#### Control, geometry, and safety

- Start in every lane and every admitted transition state.
- Same-tick opposite input; edge-lane input; input during transition; held input.
- Reachability for every admitted hazard state with and without audience counter.
- Cumulative maximum slowdown; repeated collision attempts; overlap/stack/refresh attempts.
- Delivery just before deadline, exactly at deadline, and after deadline.
- Same-tick collision and delivery.

#### Phase and clock boundaries

- Hazard proposal immediately before, exactly at, and after t=15.
- Counter/general input immediately before, exactly at, and after t=20.
- Model completion before, exactly at, and after each applicable timeout/cutoff.
- Phase close, pause, command, collision, delivery, settlement, and deadline coincidences.
- Pause in every phase; pause at deadline; commands while paused; resume without catch-up.
- Reward display and terminal behavior after turns 1, 2, and 3; prove no fourth turn.

#### Audience scale and abuse

- N=0, 1, 2, threshold-minus-one, exact threshold, threshold-plus-one, and large deterministic rosters.
- At least one 100,000-message fixture using a reused hashed corpus, without LLM actors.
- Cross-channel races, duplicates, reconnects, join/leave at roster boundary, spoofed/unlinked identity, notification reordering, and repeated transport delivery.
- Coordinated minority, majority abstention, Sybil-like multi-account fixture, bot-only cohort, underfilled cohorts, and defensive-agent pressure.
- Verify bot/fixture influence, quorum, bounty, and payout remain zero.

#### Incentive and reward attacks

- Safe-danger farming; repeated accepted hazards; duplicate hazard IDs; danger-only participants.
- Intentional collision/reward denial; multiple collisions; no eligible audience; exact rational shares.
- Wipe/build-drop/reset; withheld audience share; retry/carry attempts.
- Prove caps and identify remaining incentive exploits without claiming grief resistance.

#### Model and adapter failures

- Valid schema but illegal action; malformed schema; refusal; incomplete output; timeout; duplicate; stale phase; wrong hazard ID; excessive payload; adversarial text.
- OpenAI unavailable, Twitch unavailable, IVS/AWS unavailable, intermittent connectivity, reordered/dropped/duplicate messages.
- Show simulation/render progression is independent of provider response.
- Verify deterministic status: `applied`, `expired`, `rejected`, or `duplicate`.

#### Offline/failover and recovery

- Start offline; fail over at every safe phase boundary; reject unsafe mid-resolution takeover.
- Compare live-fixture and offline-fixture canonical command/state hashes.
- Recovery with matching state, mismatching state, failed health check, and stale pending commands.
- Prove fixture-mode labeling and sanitized/synthetic provenance.

#### Hotfix and booth behavior

- Valid data/rules patch; failing fixture; stale base/version; invalid signer/expiry; safety-invariant relaxation; activation boundary; rollback.
- Twitch Booth conversion behavior without real moderation.
- Codex Booth diagnosis/patch/test/sign/deploy presentation with truthful synthetic/live labels.
- IVS booth scale boost and deterministic fallback when adapter unavailable.

#### Presentation, audio, and credibility

- Mobile/compressed-video readability audit using defined output captures if a render path exists; otherwise mark unobserved.
- Bullet-time event alignment with authoritative ticks and real deadline.
- Audio state transitions, telemetry cues, voiceover priority, mute/accessibility behavior, and licensing/permission gates.
- Every displayed latency, message, tool call, validation stamp, sponsor/product statement, and event claim is either recorded evidence, explicitly synthetic, or suppressed.

### 8. Mandatory invariants

Evaluate each invariant per scenario and globally. At minimum:

- deterministic replay produces identical canonical final and boundary hashes;
- engine alone owns physics/state mutation;
- rendering/simulation never waits for a provider;
- no late, duplicate, paused, unlinked, or invalid command mutates state;
- every eligible account contributes at most one influence per turn across channels;
- bots/fixtures never impersonate humans, affect human quorum, create Hype, or receive live Hype;
- hazard commitment, warning, counter, and bounty increment share one committed ID;
- no committed hazard means no warning, obstacle, or bounty increment;
- safety caps prevent permanent control loss, stun lock, stacking, refresh, unbounded harm, or unavoidable death;
- every admitted obstacle state is avoidable under the selected control/geometry contract;
- clear-lane removal precedes collision; collision precedes delivery; deadline precedes equality-time delivery;
- settlement occurs at most once, only at terminal delivery, with exact selected arithmetic;
- wipe/deadline/build-drop settles zero and new match carries no state;
- no fourth turn begins;
- pause produces no catch-up ticks and cannot suspend a reached deadline;
- fixture/live modes use the same canonical command schema and remain visibly distinguishable;
- data/rules patches cannot relax hard invariants or activate outside a validated boundary;
- no unsupported promotional or live-service claim is emitted.

### 9. Issue triage and plan repair

For every failure, create an immutable issue record before attempting a fix. Classify root cause as `plan`, `implementation`, `harness`, `fixture`, `evidence`, or `external_dependency`; do not force every failure into the plan.

Each issue requires:

- stable ID;
- severity `S0` through `S4`;
- affected feature/scenarios/invariants;
- expected versus observed behavior;
- evidence paths and hashes;
- deterministic reproduction command;
- root-cause confidence and alternatives considered;
- whether it blocks simulation validity, report review, or development;
- proposed remediation and owner.

Repair rules:

1. Preserve baseline evidence unchanged.
2. Apply the minimum plan change for confirmed plan defects. Do not expand scope or add features to make a test pass.
3. Record every plan change in `PLAN-CHANGELOG.md`, including old/new text, rationale, affected decisions, source evidence, author, and hashes.
4. Increment the plan revision; never rewrite revision-4 history.
5. Synchronize all current plan, machine-readable, context, status, directive-ledger, and relevant static-test records.
6. Product decisions go to `HUMAN-DECISIONS.md`; do not silently resolve them.
7. Correct implementation/harness/fixture defects only within the simulation-support scope, with owned paths and targeted tests.
8. Run the affected deterministic scenarios, then one full regression. This is verification of a changed candidate, not an automatic model retry.
9. If a fix creates a new critical failure, stop and report it; do not enter an unbounded repair loop.

### 10. Required artifacts

At minimum produce this complete bundle:

```text
artifacts/simulations/full-game/<run-id>/
  README.md
  RUN-MANIFEST.json
  AUTHORIZATION.md
  SOURCE-BINDINGS.json
  FEATURE-INVENTORY.json
  ASSUMPTIONS-AND-GAPS.md
  HUMAN-DECISIONS.md
  SCENARIO-MATRIX.json
  CORPUS-MANIFEST.json
  seeds.json
  commands/
  traces/
  state-hashes/
  results/SCENARIO-RESULTS.jsonl
  INVARIANT-RESULTS.json
  COVERAGE.json
  ISSUES.json
  PLAN-CHANGELOG.md
  REMEDIATION-RESULTS.json
  REGRESSION-RESULTS.json
  MODEL-USAGE.json
  CLAIMS-AND-PROVENANCE.json
  SIMULATION-REPORT.md
  DEVELOPMENT-READINESS.json
  REVIEW-PACKET.md
  INDEPENDENT-REVIEW.md
```

Required semantics:

- `RUN-MANIFEST.json`: run ID, UTC timestamps, authorization locator, exact repository identity or explicit no-Git state, tool versions, source hashes, plan revision, seeds, corpus hashes, commands, exit codes, artifact hashes, and completion status.
- `FEATURE-INVENTORY.json`: every active feature and one of `passed`, `failed`, `blocked_by_plan_gap`, `blocked_by_implementation`, `not_observed`, or `out_of_scope_with_reason`.
- `SCENARIO-MATRIX.json`: scenario ID, features, inputs, seed, expected oracles, execution mode, and dependencies, written before execution.
- `SCENARIO-RESULTS.jsonl`: one canonical record per scenario with observed hashes, invariant results, evidence links, duration metrics, and verdict. Never embed huge traces.
- `ISSUES.json`: stable structured issue records; retain closed issues and link remediation/regression evidence.
- `MODEL-USAGE.json`: agent role, configured model/effort, packet hash/character count, purpose, output artifact, and status. Do not invent token or dollar totals unavailable from tooling.
- `CLAIMS-AND-PROVENANCE.json`: every public-facing technical/event/sponsor/latency claim with `observed`, `fixture`, `planned`, `externally_sourced`, or `unsupported` status.
- `SIMULATION-REPORT.md`: executive verdict, scope, method, feature coverage, scenario results, invariant table, issues by severity/root cause, plan revisions, residual risks, limitations, and exact next gates.
- `DEVELOPMENT-READINESS.json`: boolean `ready`, blocking issues/decisions/evidence, candidate plan revision/hash, required implementation work packages, dependency order, and review verdict/hash.
- `REVIEW-PACKET.md`: compact index of authoritative artifacts and hashes; never paste full traces.
- `INDEPENDENT-REVIEW.md`: exact reviewer model/effort, bound artifact hashes, verdict exactly `READY` or `REVISE`, critical findings, limitations, and whether development may begin.

All JSON must be UTF-8, parseable, deterministically serialized where the project provides canonical serialization, and free of duplicate keys. Every artifact referenced by the report must exist and have a SHA-256 in the manifest.

### 11. Independent review gate

After remediation and the complete regression report are frozen, give Astra/high one compact, hash-bound review packet. It must independently review:

- inventory completeness;
- scenario/oracle adequacy;
- raw-evidence-to-conclusion traceability;
- plan versus implementation/harness classification;
- deterministic replay and invariant results;
- unresolved human decisions;
- credibility and fixture/live labeling;
- whether any critical path was skipped or simulated circularly by the same logic as its oracle.

Do not ask Astra to rewrite the report or plan. One review call only. No automatic retry/fallback. If unavailable, set the review and readiness status to `BLOCKED_REVIEW_UNAVAILABLE`.

`READY` means the simulation report and candidate plan are coherent enough to begin separately authorized development. It does not mean the game, integrations, resilience, accessibility, security, or promotional claims are proven in production.

### 12. Acceptance criteria

Set `DEVELOPMENT-READINESS.json.ready=true` only if all are true:

1. Every active planned feature is inventoried and covered or explicitly blocked with a development consequence.
2. All scenarios have immutable expected oracles and reproducible commands.
3. All `S0`/`S1` and development-blocking `S2` plan issues are closed with regression evidence.
4. There are no unresolved product decisions required for the first development milestone.
5. Required global invariants pass.
6. At least two identical deterministic executions of the final golden scenarios produce identical canonical digests.
7. The complete regression passes against the final candidate plan revision.
8. All fixture, mocked, planned, externally sourced, and observed claims are labeled truthfully.
9. `INDEPENDENT-REVIEW.md` contains a version-bound Astra/high `READY` verdict.
10. The current user has not withdrawn or narrowed authorization.

Otherwise set `ready=false`, name the blockers, and stop. Do not start development automatically.

### 13. Final response

Return no more than 250 words. Lead with:

- simulation verdict;
- final candidate plan revision and hash;
- scenario/pass/fail/blocked counts;
- invariant result;
- issue counts by severity and root cause;
- independent review verdict;
- development-readiness boolean;
- exact artifact root and links to `SIMULATION-REPORT.md`, `ISSUES.json`, `PLAN-CHANGELOG.md`, `DEVELOPMENT-READINESS.json`, and `INDEPENDENT-REVIEW.md`.

State explicitly that deterministic simulation is not live-service or production evidence. Then stop and wait for the user's next authorization.

---

## Suggested authorization message for the later run

Use this as a separate user message when ready:

> `AUTHORIZE_COMPLETE_GAME_SIMULATION=true`. Execute the complete-game deterministic simulation prompt in `docs/planning/S1-SIMULATION-RUN-PROMPT.md`. Revision 4 is the baseline, not a frozen final design. You may create simulation-support code and repair confirmed plan defects, but do not begin product development, use live services, deploy, publish, or silently resolve product decisions. Produce the complete immutable artifact bundle and stop after the independent report-review gate.
