# Delegated Remediation & Product Decisions

Recorded: 2026-11-01T17:36:28+05:30  
Authority: Delegated by requester under Same-Day Deterministic Remediation Planner v2.0 Profile (`config/directive-policy.json` directive `remediation_rerun_and_decision_delegation`).  
Checkpoint Baseline: `docs/planning/SIMULATION-EVIDENCE-AUDIT.md` (`adcc2692789d29aae24b35acb522ea494c96748c5a20a04605461dcc52f3a798`)

```
AUTHORIZATION: rerun + decision delegation
Granted by: requester (direct instruction)
Granted at: 2026-11-01T17:36:28+05:30
Scope: one or more fresh simulation runs under new, non-existing run roots;
       and resolution of D-06, D-07, D-08, booth placement and other blocking
       product choices by recorded decision.
Explicitly excluded: modification of the rejected run; product development;
       gameplay execution beyond the authorized simulation; publication.
Supersedes: the checkpoint's "do not rerun without new explicit authorization" clause.
```

---

## DECISION-01 (D-06) — Failover Authority, Commit Boundary, Replay Identity, and Recovery Acceptance

1. **Exact Question (from `docs/planning/gameplan-v2.json:167-170` & `docs/planning/SIMULATION-EVIDENCE-AUDIT.md:116-128`):**
   > "Failover owner, pending-command/reward commit boundary, replay identity and health/state recovery acceptance."
2. **Options Considered:**
   - **Option A (Chosen): Stage-operator-confirmed failover strictly at phase-close boundaries (`tick % 600 in {0, 400, 500}`), rejecting mid-resolution takeover, requiring canonical `state_hash` and `sequence` equality before live recovery, and explicitly labeling replay/offline fixture envelopes.**
   - **Option B: Automatic client-side mid-turn failover.** Consequence: creates split-brain state divergence between the authoritative server tick and client interpolation during the 5s resolution window, violating `INV-01` and `INV-06`.
   - **Option C: Leave unresolved.** Consequence: blocks `AUDIT-06` and `AUDIT-07`, keeping `DEVELOPMENT-READINESS.json.ready` permanently `false`.
3. **Evidence Used:**
   - `docs/planning/GAMEPLAN-v2.md:17,95` (`INV-06` safe boundary handover, single authoritative writer, health/state comparison before live recovery)
   - `docs/planning/gameplan-v2.json:166-170,299-306` (`D-06`, `INV-06`)
   - `coordination/full_game_simulator.py:156-160,298-326` (phase boundary hash recording)
   - `coordination/run_full_game_simulation.py:1237-1270,1490-1493` (`SCEN-OFF-02`, `SCEN-OFF-03`)
4. **Chosen Value:**
   - **Failover Owner:** Stage operator (`actor_id="stage_operator"`, command `operator.failover`), never automatic client takeover.
   - **Commit Boundary:** Only at exact phase boundaries (`turn_tick in {0, 400, 500}`, i.e., start of planning, resolution, or reward). Any failover command or takeover attempt mid-phase (`turn_tick not in {0, 400, 500}`) is rejected (`status="rejected"`). Pending uncommitted commands in the queue at failover are discarded without rollover; committed hazard/bounty state from `[0, 15s)` is preserved if failover occurs at `turn_tick == 400`.
   - **Replay Identity:** Offline fixture commands carry `provenance="fixture"` and `execution_mode="offline_fixture"` in metadata while producing identical canonical state hashes to live-adapter fixtures for identical command streams.
   - **Recovery Acceptance:** Returning to live mode (`operator.recover`) requires pre-recovery health check passing AND exact match of `(tick, turn, phase, canonical_hash(get_canonical_state()))`. Any mismatch rejects live recovery and keeps the engine on the deterministic offline fixture driver.
5. **Consistency with Thesis & Invariants:**
   - Upholds "The enemy is not chat or AI. The enemy is unstructured scale" by ensuring transport/provider outages never stall the 20/5/5 cadence (`INV-05`) or split authority (`INV-01`, `INV-06`). Preserves `INV-BOT-ISOLATION` and human-only bounty (`D-04`) by keeping offline fixture provenance explicit (`INV-07`).
6. **Blast Radius:**
   - Affects `sdc/clock_and_sim.py` (or `coordination/full_game_simulator.py`), `SCEN-OFF-01..03` oracles, `GAMEPLAN-v2.md`, `gameplan-v2.json`, and `config/directive-policy.json`.
7. **Reversal Cost:**
   - **1 bounded session** (update `D-06` rule parameters in `GAMEPLAN-v2.md` / `gameplan-v2.json` / `config/directive-policy.json` and re-run the 3 offline/failover scenarios). Fully reversible before the freeze point.
8. **Status:** `DELEGATED_ACCEPTED`, `PROVISIONAL` (requester retains veto at freeze point; flagged `ESCALATE` in final report per §1 because D-06 is a product-gate resolution).

---

## DECISION-02 (D-07) — Data-Only Hotfix Trust, Permitted DSL, Signer/Version Rules, and Rollback Boundary

1. **Exact Question (from `docs/planning/gameplan-v2.json:171-175` & `docs/planning/SIMULATION-EVIDENCE-AUDIT.md:116-128`):**
   > "Hotfix approver, permitted DSL, trusted signer/base/version/expiry rules and activation/rollback boundary."
2. **Options Considered:**
   - **Option A (Chosen): Stage-operator + trusted-key dual-gated manifest (`booth.hotfix`) restricted to a 2-key numeric tuning allowlist (`slowdown_fraction` in `[0.05, 0.20]`, `slowdown_duration_ticks` in `[1, 40]`), bound to exact `base_state_hash`, monotonic `patch_version`, and `expiry_tick`, activating strictly at turn boundary (`turn_tick == 0`) with automatic rollback on invariant violation.**
   - **Option B: Arbitrary JSON path patching or immediate mid-turn activation.** Consequence: allows patches to alter physics/HP invariants or cause non-deterministic mid-resolution drift (`INV-09` violation).
   - **Option C: Leave unresolved.** Consequence: blocks `AUDIT-06` and `AUDIT-07`, keeping `DEVELOPMENT-READINESS.json.ready` `false`.
3. **Evidence Used:**
   - `docs/planning/GAMEPLAN-v2.md:19,95` (`INV-09` data/rules only, turn-boundary activation, cannot relax hard safety invariants)
   - `docs/planning/gameplan-v2.json:171-175,328-333` (`D-07`, `INV-09`)
   - `coordination/full_game_simulator.py:276-288,313-315` (`booth.hotfix` handling)
   - `coordination/run_full_game_simulation.py:1272-1319,1494-1497` (`SCEN-HOT-01`, `SCEN-HOT-02`)
4. **Chosen Value:**
   - **Hotfix Approver & Signer:** Codex Booth proposal (`actor_id="codex_booth"`) must carry a deterministic manifest binding `{patch_version, base_plan_revision, target_turn, expiry_tick, patch_data, signature}` where `signature` matches the canonical SHA-256 HMAC/binding over the manifest with trusted key ID `CODEX_BOOTH_TRUSTED_V1` and stage-operator approval flag `operator_approved=True`.
   - **Permitted DSL:** Strictly flat JSON object with keys in `{"slowdown_fraction", "slowdown_duration_ticks"}` only. Any other key (e.g., `hp_system`, `unbounded_slowdown`, `pool`, `lane`, `base_speed`) or out-of-range value (`slowdown_fraction > 0.20` or `< 0.0`, `slowdown_duration_ticks > 40` or `< 0`) is rejected before staging.
   - **Version & Expiry Rules:** `patch_version` must be strictly greater than `applied_hotfix_version`; `expiry_tick` must be `>= next_turn_start_tick`. Stale base revision or expired tick rejects the command.
   - **Activation & Rollback Boundary:** Staged in `pending_hotfix` during planning/resolution/reward; activates strictly at the next turn boundary (`turn_tick == 0`). Prior rules are snapshotted in `previous_hotfix_rules`; if post-activation invariant check fails or `operator.rollback_hotfix` is submitted, rules revert atomically at the boundary.
5. **Consistency with Thesis & Invariants:**
   - Preserves `INV-01` (engine authority), `INV-02` (safety caps: slowdown never exceeds 20% / 2s), and `INV-09` (no executable code hot-loading, turn-boundary activation).
6. **Blast Radius:**
   - Affects `sdc/clock_and_sim.py` (`booth.hotfix` validation and turn-boundary activation), `SCEN-HOT-01..02` plus negative tests for stale version/signer/expiry/rollback, `GAMEPLAN-v2.md`, `gameplan-v2.json`, and `config/directive-policy.json`.
7. **Reversal Cost:**
   - **1 bounded session** (update `D-07` schema in simulator and plan files). Fully reversible before the freeze point.
8. **Status:** `DELEGATED_ACCEPTED`, `PROVISIONAL` (flagged `ESCALATE` in final report per §1).

---

## DECISION-03 (D-08) — Submission Readiness & Live Demonstration Scope Separation

1. **Exact Question (from `docs/planning/gameplan-v2.json:176-180` & `docs/planning/SIMULATION-EVIDENCE-AUDIT.md:67-85,116-128`):**
   > "Actual Twitch participation path, live demonstration evidence and brand/audio permissions."
2. **Options Considered:**
   - **Option A (Chosen): Separate `simulation_and_plan_ready` (S1 deterministic simulation & candidate plan gate) from `live_submission_ready` (external Twitch/video/audio gate); require all offline/simulation artifacts to label Twitch/AWS/Codex booths as non-sponsor diegetic metaphors, use synthesized opt-in Web Audio only (zero third-party copyrighted audio), and mark unrendered visual/audio/live features as `not_observed` or `blocked_by_implementation` in simulation coverage.**
   - **Option B: Claim 100% live/visual/audio readiness from state-label simulation.** Consequence: directly violates `AUDIT-04`, `AUDIT-07`, `INV-08`, and `INV-10`.
   - **Option C: Leave D-08 completely undefined for the simulation gate.** Consequence: `DEVELOPMENT-READINESS.json` cannot distinguish between "ready to begin bounded development of the offline slice" and "ready for live hackathon submission."
3. **Evidence Used:**
   - `docs/planning/SIMULATION-EVIDENCE-AUDIT.md:67-85,116-129` (`AUDIT-04`, `AUDIT-07`)
   - `docs/planning/GAMEPLAN-v2.md:18,95,99-101` (`INV-08`, separate gates for plan rehearsal, offline slice, and submission readiness)
   - `docs/research-2026-11-01/HACKATHON.md:14-18` (rules require under-3-minute demo, Twitch connection, Codex session provenance, and trademark/media permission)
   - `EVIDENCE.md:15-20` (sandbox denies sockets; audio is synthesized and opt-in)
4. **Chosen Value:**
   - **Participation Path & Provenance:** Offline simulation uses deterministic seeded fixtures (`provenance="fixture"`) and never claims live Twitch EventSub or Extension JWT execution. Live Twitch adapter remains gated on external credentials outside the sandbox.
   - **Brand & Audio Permissions:** All in-game booths (Twitch Moderation Forcefield, Codex Live Hotfix, AWS/IVS Scale Boost) are explicitly labeled as **fictional, non-sponsor diegetic game metaphors** (`INV-08`). Audio uses only procedural/synthesized Web Audio oscillators (`client/app.js`), requiring zero third-party music licenses.
   - **Honest Feature Coverage Accounting (`AUDIT-04`):** In the headless deterministic simulation pipeline, features requiring a live render capture, acoustic output, or live external network (`FEAT-14-READABILITY-AND-HUD`, acoustic/voiceover portion of `FEAT-13-ADAPTIVE-AUDIO`, rendered 3-minute video capture of `FEAT-15-PUBLIC-DEMO-TIMELINE`, and visual overlay of `FEAT-12-BULLET-TIME-PRESENTATION`) must be derived mechanically as `not_observed` (or `partially_observed_state_only` with `coverage_state: "not_observed"` for unrendered claims), never fabricated as 100% `passed/covered`.
   - **Readiness Gate Split (`AUDIT-07`):** `DEVELOPMENT-READINESS.json` computes `ready` (eligibility to start bounded offline-slice development) from: (a) all S0/S1/blocking-S2 simulation & plan issues closed, (b) D-01..D-07 + deterministic clarifications synchronized in Revision 5 with bound SHA-256, (c) all 18 invariants passing, (d) golden replay verified, and (e) genuine Astra/high `INDEPENDENT-REVIEW.md` returning `READY`. Simultaneously, `submission_ready` is explicitly `false` until live Twitch capture and <3-min video are recorded outside the sandbox.
5. **Consistency with Thesis & Invariants:**
   - Directly enforces `INV-07`, `INV-08`, `INV-10`, `AUDIT-04`, and `AUDIT-07`: no synthetic or unrendered check is ever misrepresented as visual, acoustic, or live-service evidence.
6. **Blast Radius:**
   - Affects `sdc/evidence_pipeline.py` (feature status derivation and readiness computation), `FEATURE-INVENTORY.json`, `COVERAGE.json`, `DEVELOPMENT-READINESS.json`, `GAMEPLAN-v2.md`, `gameplan-v2.json`, and `config/directive-policy.json`.
7. **Reversal Cost:**
   - **1 bounded session.** Fully reversible before the freeze point.
8. **Status:** `DELEGATED_ACCEPTED`, `PROVISIONAL` (flagged `ESCALATE` in final report per §1).

---

## DECISION-04 (D-09 / AUDIT-06) — Diegetic Booth Placement, Steering Transition Lockout/Clamping, and Nominal Route-Speed Calibration (Revision 5 Synchronization)

1. **Exact Question (from `docs/planning/SIMULATION-EVIDENCE-AUDIT.md:100-115,165`):**
   > "`PLAN-CHANGELOG.md` proposes steering lockout/clamping, nominal speed, and booth placement, but the current plan remains revision 4... The booth placements are also a third design change not represented by either of the two recorded issues. Required correction: decide whether each candidate change is a deterministic clarification or human product decision. Record every change as an issue/decision, then synchronize approved changes across all current plan and policy records."
2. **Options Considered:**
   - **Option A (Chosen): Record all three items explicitly (`ISSUE-SIM-01` steering lockout/clamping as deterministic clarification of D-01; `ISSUE-SIM-02` nominal route speed `100/88` units/s as deterministic clarification of D-02/D-05; `ISSUE-SIM-03` / `DECISION-04` diegetic booth progress waypoints `35.0 / 60.0 / 80.0 / 100.0` and bounded effects as delegated product decision), and synchronize all three into Revision 5 of `GAMEPLAN-v2.md`, `gameplan-v2.json`, `S1-SIMULATION-PROFILE.md`, `CONTEXT-v2.md`, `STATUS.md`, and `config/directive-policy.json` Revision 8.**
   - **Option B: Remove booth waypoints from the simulator.** Consequence: breaks `FEAT-08`, `FEAT-09`, `FEAT-10`, `SCEN-E2E-04`, and `SCEN-HOT-01..04`.
   - **Option C: Keep `GAMEPLAN-v2.md` at Revision 4 while claiming Revision 5 in simulation outputs.** Consequence: fails `AUDIT-06` and `AUDIT-07`.
3. **Evidence Used:**
   - `docs/planning/SIMULATION-EVIDENCE-AUDIT.md:100-115,165` (`AUDIT-06`)
   - `coordination/full_game_simulator.py:39-49,200-214,289-295,378-383,446-463` (implemented constants and booth triggers)
   - `coordination/run_full_game_simulation.py:1647-1733` (`ISSUES.json` and `PLAN-CHANGELOG.md`)
   - `docs/planning/SAN-DIEGO-ROUTE.md` & `docs/planning/GAMEPLAN-v2.md:6-10` (5-segment San Diego route order)
4. **Chosen Value:**
   - **Item 4A (`ISSUE-SIM-01` — Deterministic Clarification to `D-01`):**
     - Discrete lanes `0, 1, 2` (width `1.0` unit, center `1`).
     - Transition duration `0.5s` (`10` ticks at `20 Hz`), linear lateral interpolation; collision overlap envelope `|lateral_pos - 1.0| < 0.4`.
     - Edge clamping: `left` from lane `0` or `right` from lane `2` returns `rejected` without movement.
     - Transition lockout: `streamer.steer` received while `transition_remaining_ticks > 0` returns `rejected` (no queueing or overwrite).
   - **Item 4B (`ISSUE-SIM-02` — Deterministic Clarification to `D-02` / `D-05`):**
     - Route distance is `100.0` units across 5 districts: Little Italy `[0, 25)`, Waterfront/Marina `[25, 50)`, Gaslamp Quarter `[50, 75)`, San Diego Convention Center `[75, 95)`, Fictional Main Stage `[95, 100]` (arrival at `100.0`).
     - Nominal free speed is exact rational `Fraction(100, 88)` units/second (`5 / 88` units/tick at `20 Hz`, `~1.13636` units/s). With 0 collisions, arrival occurs at `t = 88.0s` (tick `1760`). With maximum 3 collisions (`3 * 0.4s = 1.2s` equivalent travel loss), arrival occurs at `t = 89.2s` (tick `1784`), strictly before the `90.0s` (`1800`-tick) deadline (`INV-02` reachability/headroom).
   - **Item 4C (`ISSUE-SIM-03` / `DECISION-04` — Delegated Product Decision on Diegetic Booth Placement & Effects):**
     - **Twitch Booth (`twitch_booth`):** Placed at progress `35.0%` (Waterfront/Marina). Sets `twitch_forcefield_active = True` (diegetic visual/state marker; converts in-game obstacle metaphor without real chat moderation or live Hype inflation beyond `D-04` human-hazard rules).
     - **Codex Live Hotfix Booth (`codex_booth`):** Placed at progress `60.0%` (Gaslamp Quarter). Unlocks diagnostic telemetry and turn-boundary data-only hotfix staging (`D-07`).
     - **AWS / Amazon IVS Booth (`aws_booth`):** Placed at progress `80.0%` (San Diego Convention Center). Sets `ivs_scale_boost_active = True`; explicit `booth.boost` fixture/command applies bounded `+10%` forward speed for `40` ticks (`2.0s`) without altering safety caps or claiming real AWS sponsorship.
5. **Consistency with Thesis & Invariants:**
   - Aligns the 5-segment San Diego journey (`GAMEPLAN-v2.md:7`) with concrete progress intervals and ensures 3-collision survival headroom (`D-02`, `INV-02`) while keeping booth effects strictly bounded and engine-owned (`INV-01`, `INV-08`).
6. **Blast Radius:**
   - Updates `GAMEPLAN-v2.md` (to Revision 5), `gameplan-v2.json` (to Revision 5), `S1-SIMULATION-PROFILE.md`, `CONTEXT-v2.md`, `STATUS.md`, `config/directive-policy.json` (to Revision 8), `tests/test_gameplan_rules.py`, and `ISSUES.json` (3 triaged issues instead of 2).
7. **Reversal Cost:**
   - **1 bounded session.** Fully reversible before the freeze point.
8. **Status:** `DELEGATED_ACCEPTED`, `PROVISIONAL` (flagged `ESCALATE` in final report for the booth placement/effect portion per §1).
