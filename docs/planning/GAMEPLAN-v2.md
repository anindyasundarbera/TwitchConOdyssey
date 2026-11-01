# San Diego game plan v2 — selected S1 plan

**Status: revision 5, `selected_for_s1_simulation_unverified`; gameplay remains disabled outside authorized deterministic simulation.** D-01 through D-05 select the exact [S1 simulation profile](S1-SIMULATION-PROFILE.md) for bounded S1 simulation, and D-06 through D-09 (`DECISION-01..04`, `ISSUE-SIM-01..03`) are recorded as `delegated_for_s1_remediation_provisional` in [DECISIONS.md](DECISIONS.md). Revision 5 builds on baseline Revision 4 (`a6967a24601f259be027ed7fbebed5ad6e0784d4a7f7b7f6c0a2c3967e47e6ed` for `GAMEPLAN-v2.md`; `1b43be51add9d6c5e1cc2b6378e66a7f48fb76985435693b3dcf303ad6234937` for `gameplan-v2.json`), preserving design closure of the three critical findings in the unchanged [S1 REVISE review](S1-ASTRA-REVIEW.md) ([response](S1-ASTRA-REVIEW-RESPONSE.md)) while binding steering lockout/clamping, `100/88` nominal speed calibration, diegetic booth waypoints (`35.0/60.0/80.0/100.0`), phase-boundary failover, 2-key signed turn-boundary hotfixes, and simulation-versus-live submission separation. Fresh version-bound independent review (`gpt-6-astra`) remains required. [Machine-readable plan](gameplan-v2.json)

## Route and core experience

**Little Italy / North Embarcadero → waterfront / Marina → Gaslamp Quarter → San Diego Convention Center → fictional Main Stage.** The geographic anchors are sourced in [SAN-DIEGO-ROUTE.md](SAN-DIEGO-ROUTE.md); the compressed sequence and stage are game proposals. Active runtime labels, map copy, and district names now use this sequence, but route geometry and gameplay remain unverified.

Keep the thesis: "The enemy is not chat or AI. The enemy is unstructured scale." The selected S1 cadence is 20-second planning, 5-second resolution with crowd/counter input locked, then exactly 5.0 active seconds of reward display. Auto-forward and streamer steering continue through all three phases until terminal state, subject to pause. Three full turns reach the 90-active-second deadline; no fourth turn starts. One localized Little Italy center-lane obstacle committed before planning t=15 and `clear_lane` form the first slice. These are selected project design values, not playtested tuning or implementation evidence.

## Repairs restored from original requirements

- Enforce safety across cumulative hazards: no permanent control loss, repeated stun-lock, unavoidable death or unbounded damage. Selected S1 numerical caps are specified below; reachability and enforcement need later fixtures.
- Keep model proposals asynchronous and separate from the authoritative engine. Revalidate phase, policy, budget, cooldown, placement, physics and idempotency. Late results cannot alter locked resolution or silently move influence to a later turn.
- Distinguish human, bot and fixture provenance. Bots cannot impersonate viewers or generate farmable bounty; excluding bots from payout alone is insufficient. A labeled fixture may illustrate a synthetic reward ledger without creating live participant progression.
- Preserve visible labeled backfill and bounded subject influence. S1 selects K=2 display groups, unit account weighting, frozen roster and a 60% roster quorum. Authenticated linked accounts do not prove one account equals one person or achieve human-level fairness.
- Preserve canonical commands, deterministic time/seeds, safe boundary handover, one authoritative writer, duplicate-effect prevention and health/state comparison before live recovery.
- Restore truthful demo evidence: sanitized actual messages, recorded API calls, measured latency, actual engine validation/execution and distinct Codex diagnosis/fixture evidence. Label replay; presentation slowdown cannot imply a paused authority loop or real deadline.
- Keep hotfixes data/rules only, with independent fixtures and validated turn-boundary activation. They cannot relax hard safety invariants. Signing/trust and activation design are pending.

These are requirements and proposed contracts, not implemented or proven protections. [Review evidence](PLAN-REHEARSAL.md)

## Actor authority

| Actor | Authority |
| --- | --- |
| Streamer | Auto-forward and digital adjacent-lane steering during planning, resolution and reward until terminal state, subject to pause; no manual counter confirmation/override; invalid or absent crowd result means abstain. |
| Viewer | Bounded untrusted proposals, subject to eligibility and influence accounting. |
| Character | Engine-owned deterministic state; no model controls physics. |
| Rival squad | Bounded game entity, governed by approved rules. |
| Rehearsal attacker | Document critic; not a deployed gameplay agent or attack service. |
| Stage operator | Defined presentation/mode controls, not arbitrary state changes. |
| AI / Codex | Advisory action or data/rules patch proposals only. |

## Selected decisions before gameplay

All five decisions have status `selected_for_s1_simulation_unverified` and gate `before_gameplay`. The [S1 profile](S1-SIMULATION-PROFILE.md) is the detailed selected specification, including boundary oracles, later fixture requirements and evidence limits. Selection does not authorize execution. All numbers/formulas below are project design inferences.

External evidence is separate: [platform review](research/S1-PLATFORM-EVIDENCE.md) documents account claims, transport IDs/timestamps and model-output limits; [systems review](research/S1-SYSTEMS-EVIDENCE.md) documents input/objective guidance, monotonic clocks, ordering and identity/incentive limitations. Neither selects or empirically validates these numerical mechanics. No latency, safety, fairness, accessibility or gameplay result was measured.

### D-01 — player_agency

Auto-forward; 3 discrete lanes (0, 1, 2); remappable digital left/right, initially arrows and gamepad D-pad. One press requests one adjacent-lane transition over 0.5s (10-tick at 20Hz linear interpolation, lateral collision overlap |x - 1.0| < 0.4); edge clamping and in-flight transition lockout return rejected; no held repeat; same-tick opposites cancel.

Auto-forward and steering remain active through planning, resolution and reward until terminal state, subject to pause; only crowd/counter input locks. No streamer counter confirmation/override; no valid crowd result means abstain.

HUD: one progress meter, hazard timer, one plain-language action/consequence preview; no high-velocity chat reading. INV-01 reserves position, physics and collision to the deterministic engine.

### D-02 — survival_contract

One localized Little Italy center-lane obstacle and clear_lane; maximum 1 obstacle/turn and 3/match; no overlap. Hazard proposal/admission is half-open [0,15.000s); one accepted human-origin hazard committed before t=15 creates the fixed center-lane warning for the entire [15,20) interval and one deduplicated bounty increment. Warning/counter/increment bind to committed hazard ID. Proposal/model result at or after t=15 expires for that turn; no backdating or rollover. No accepted hazard by cutoff means no hazard, warning or increment. Active first 3s resolution.

Collision once/obstacle: 20% forward-speed reduction for 2s; zero HP damage/stun/steering loss/displacement. No stacking, refresh or residual. Caps: 2s slowdown/turn, 6s/match; equivalent free-speed travel loss at most 0.4s/turn and 1.2s/match over the 100.0-unit 5-segment route ([0,25), [25,50), [50,75), [75,95), [95,100]) at nominal speed 100/88 units/s (88.0s nominal, 89.2s with max 3 collisions < 90.0s deadline).

clear_lane removes before collision; missing quorum uses bounded uncountered branch. No HP/death/respawn/checkpoints. INV-02 cumulative harm limits remain mandatory; later fixtures must establish reachability from every admitted state.

Wipe means not delivered strictly before 90s active deadline; no automatic retries or carried state/pool. A new explicit match resets all state.

### D-03 — audience_fairness

Live eligibility requires authenticated platform subject at account level with linked chat/button identity; reject unlinked input. This is not one-human proof. Offline actors are labeled fixtures.

Freeze eligible roster at planning start; joins/leaves next turn; reconnect retains identity/influence. S1 K=2: stable-sort subjects then alternate assignment; squads display groupings, not equal electoral blocks.

Each eligible subject weight 1, max 1 influence/turn across channels. First valid receipt wins atomically; zero replacements. Transport dedupe is separate.

clear_lane requires ceil(0.60*N) frozen-roster votes and at least 1 eligible vote; otherwise abstain, which wins ties. Bots have weight/quorum/vote/bounty contribution 0 and remain labeled. Account-level quota does not prove human-level fairness or prevent Sybils.

Counter votes remain open in the half-open planning interval [0,20), bound to the committed hazard ID; general input cutoff remains t=20.

### D-04 — reward_contract

Fictional Hype only. Pool starts 0; each distinct accepted human-origin hazard committed before planning t=15 adds 20, max 1 increment/turn, cap 60, multiplier 1. Deduplicate by committed hazard ID; no committed hazard means no increment. Counter/avoidance preserves increment; harm adds no bonus.

Reward displays outcome/pending pool only; no interim payout. Delivery performs exactly one final settlement, 50/50 streamer/audience, and immediately ends active simulation; any collision, including same-time pre-deadline collision, halves total once before splitting. Wipe/deadline/build-drop settles 0.

Audience eligibility: at least 1 accepted counter vote that match, even if aggregate quorum fails; danger creation alone earns none. Equal exact rational audience shares; no rounding redistribution; absent audience share withheld without carry.

Bots/fixtures add and earn 0; fixture arithmetic is synthetic only. Residual safe-danger farming risk remains; caps do not prove grief resistance.

### D-05 — clock_contract

90s active match; 20s planning/5s resolution/exactly 5.0s reward, max 3 turns; presentation may say approximately 5s reward. Without earlier terminal state, turns end at t=30,60,90; turn 3 reward is [85,90), then process deadline, never turn 4. Auto-forward and steering continue in reward until terminal state, subject to pause. 100.0-unit route at nominal free speed 100/88 units/s (88.0s nominal, 89.2s with max 3 collisions); diegetic booth waypoints at 35.0% (twitch_booth), 60.0% (codex_booth), 80.0% (aws_booth), and 100.0% (fictional_main_stage). 20Hz authoritative target, not measured runtime. No real-world deadline claim.

Monotonic host clock, integer nanoseconds, authoritative sequence; replay uses logical time/sequence. Planning half-open: receipt exactly t=20 expires. Zero post-cutoff grace; client timestamps cannot backdate.

Equal-time ordering: deadline first, phase-close, pause request, authoritative sequence-ordered commands, effects/settlement. Pause cannot suspend a reached deadline. Admitted effects: clear_lane removal, collision adjudication, delivery detection, one final settlement. Same-time pre-deadline collision is recorded before delivery and halves settlement once. Delivery strictly precedes deadline; equality wipes for zero settlement.

Model timeout min(dispatch+2s, applicable admission close): planning t=15 for hazards, t=20 for general input/counter votes. No retry; cutoff/late results expire without backdating, rollover or tick blocking. Local validation remains required; statuses applied/expired/rejected/duplicate.

Pause freezes all simulation clocks/effects, rejects commands, invalidates pending model work; resume anchor reset, no catch-up.

Two prior ambiguities are explicitly resolved for S1: “locked input” means crowd/counter input only; streamer steering remains active. INV-04's one-human aspiration is not an identity guarantee: the selected live accounting unit is an authenticated linked account subject, and offline actors remain labeled fixtures.

Under the requester's Same-Day Deterministic Remediation Grant ([DECISIONS.md](DECISIONS.md)), D-06 (`failover_contract`, `DECISION-01`: stage-operator phase-boundary failover at `turn_tick in {0, 400, 500}` and pre-recovery `(tick, turn, phase, state_hash)` equality), D-07 (`hotfix_contract`, `DECISION-02`: dual-gated `CODEX_BOOTH_TRUSTED_V1` + operator-approved turn-boundary manifest restricted to `slowdown_fraction` and `slowdown_duration_ticks` with rollback), D-08 (`submission_and_coverage_honesty`, `DECISION-03`: simulation-versus-live readiness split, non-sponsor diegetic booth labeling, synthesized opt-in audio, and mechanical `not_observed` derivation for unrendered features), and D-09 (`DECISION-04` / `ISSUE-SIM-01..03`: steering lockout/clamping, `100/88` speed calibration, and `35.0/60.0/80.0/100.0` booth placement) are recorded as `delegated_for_s1_remediation_provisional`. Live external Twitch channel integration, rendered browser/mobile capture, and the 3-minute public demo video remain deferred under `before_live_submission`. Legacy `100+25/voter` reward formulas remain retired.

## Separate gates

Plan rehearsal evaluates completeness and contradictions. The offline slice needs explicit authorization, concrete initial-state/geometry/transition fixtures, reachability and deterministic expected outcomes before product development. Submission readiness separately needs actual Twitch functionality, Codex build/session evidence, permitted assets and the required demo. Passing one gate does not satisfy another.

**Next gate:** fresh version-bound independent review (`plan_review` / `gpt-6-astra`) of the frozen Revision 5 simulation evidence bundle. D-01 through D-05 are selected and D-06 through D-09 are recorded in [DECISIONS.md](DECISIONS.md); live gameplay remains disabled. No later phase starts automatically.

## Revision record

- Revision 1: restored v1 review omissions and separated authority/evidence gates without selecting mechanics.
- Revision 2 (2026-11-01): recorded five user-proposed partial contracts, explicit open selections and retirement of legacy bounty formulas. No new gameplay authorization, independent review or implementation verification.

- Revision 3 (2026-11-01): selected D-01 through D-05 for S1 as unverified design inferences, recorded primary-source limits, resolved steering/account-assurance ambiguities and separated selected decisions from unresolved later gates. No gameplay execution or new independent review.
- Revision 4 (2026-11-01): resolved exactly the three S1 REVISE findings: exact reward timeline and single terminal settlement, total boundary/effect priority, and hazard commitment strictly before t=15 with complete [15,20) warning and committed-ID binding. Other selected values and later gates are preserved; no new Astra verdict or gameplay evidence.
- Revision 5 (2026-11-01): synchronized `ISSUE-SIM-01` (discrete lanes `0, 1, 2`, `0.5s`/`10`-tick linear interpolation, `|x - 1.0| < 0.4` collision overlap, edge clamping `rejected`, in-flight transition lockout `rejected`), `ISSUE-SIM-02` (`100.0`-unit 5-segment route, nominal free speed `100/88` units/s for `88.0s` nominal and `89.2s` max-collision completion < `90.0s` deadline), `ISSUE-SIM-03` / `DECISION-04` (diegetic booth waypoints at `35.0%` `twitch_booth`, `60.0%` `codex_booth`, `80.0%` `aws_booth`, `100.0%` `fictional_main_stage`), and delegated decisions `DECISION-01..03` (`D-06` phase-boundary failover, `D-07` 2-key signed turn-boundary hotfixes, `D-08` simulation-vs-live submission readiness split) bound to [DECISIONS.md](DECISIONS.md) against baseline Revision 4 (`a6967a24601f259be027ed7fbebed5ad6e0784d4a7f7b7f6c0a2c3967e47e6ed` MD / `1b43be51add9d6c5e1cc2b6378e66a7f48fb76985435693b3dcf303ad6234937` JSON).
