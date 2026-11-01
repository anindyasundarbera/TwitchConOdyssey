---
id: TASK-006
title: Gameplay core implementation (authoritative engine boundary)
workstream: W3
objective: O3
contract_version: v1.0
status: GATED
risk: HIGH
parallel: PARALLEL_WITH_ISOLATION
dependencies:
  hard: [TASK-005]
  integration: [TASK-007, TASK-008]
  gates: [G-A, G-B, G-C]
owned_paths:
  - server/engine.py                       (PROVISIONAL — finalize via codebase-memory index)
  - "core modules under coordination/ or server/ only if explicitly assigned by the accepted packet"
protected_paths:
  - artifacts/simulations/full-game/**
  - coordination/deterministic_kernel.py   (kernel purity; changes need their own packet + ledger rebind)
  - config/directive-policy.json
execution_context:
  source_of_truth:
    - docs/planning/S1-SIMULATION-PROFILE.md   (D-01..D-05 selected rules)
    - config/directive-policy.json             (ledger revision ≥10 selected_decisions)
    - docs/planning/DECISIONS.md               (DECISION-01..04)
    - docs/planning/gameplan-v2.json           (revision 5)
  simulators_for_reference_only:
    - coordination/full_game_simulator.py
    - coordination/run_full_game_simulation.py
---

# TASK-006 — Gameplay core implementation

## Gates (all must hold before any code edit)

- **G-A**: explicit user gameplay authorization recorded as a new directive-ledger
  entry. `simulation_and_plan_ready: true` and this plan's existence are NOT
  authorization.
- **G-B**: compiler accepts your fresh packet for the exact owned paths after G-A.
- **G-C**: path assignment finalized through codebase-memory index discovery; if the
  index is unavailable, record the blocker and stop — no broad exploration fallback.

## Binding acceptance criteria (handoff §8.1; values ONLY from source_of_truth)

1. The engine alone owns physics and mutable state (INV-01); presentation, bots,
   fixtures, models, telemetry cannot directly mutate gameplay state.
2. One canonical command schema across fixture and live modes; validate
   identity/linkage, command type, sequence, timing, pause/terminal status, and
   dedup before applying any command (statuses applied/expired/rejected/duplicate).
3. Model/provider calls never block rendering or simulation ticks and never gain
   authority over physics or outcomes (INV-ASYNC-MODEL); timeouts/cutoffs per D-05
   (t=15 hazard admission close, t=20 general close; late results expire).
4. Boundary rules exactly per selected ledger decisions: deadline-priority total
   order (deadline, phase-close, pause, sequence-ordered commands, effects);
   delivery strictly before 90s deadline (equality ⇒ wipe, zero settlement);
   half-open planning/warning intervals; hazard commitment [0,15) with warning
   binding the committed hazard ID over [15,20); counter window [0,20).
5. Settlement at most once, only at terminal delivery; collision halves once;
   wipe/deadline/build-drop settles zero; new matches carry no state.
6. Caps: max 1 obstacle/turn, 3/match; 20%×2s slowdown per collision; 2s/turn and
   6s/match slowdown caps; ≤0.4s/turn and ≤1.2s/match free-speed loss; no HP, stun,
   stacking, refresh, displacement, permanent control loss (INV-02 family).
7. Preserve logical ticks in state transitions and trace records; pause freezes all
   clocks/effects, rejects commands, no catch-up, cannot suspend a reached deadline.
8. Data/hotfix changes validated per DECISION-02 (signed turn-boundary activation),
   never relaxing hard invariants.
9. Pure deterministic kernel stays separately testable; deterministic state
   transitions independent of model/provider/transport I/O.

## Verification contract (when gates open)

- Targeted tests for every boundary, validator, state transition, adapter rejection —
  executed ONLY when gameplay-test authorization exists (G-A scope permitting);
  until then this task may do contract/fixture design and offline validators only.
- No live Twitch services, no credentials, no server startup.
- Any change to `required_paths`-bound files requires the same-transaction ledger
  rebind procedure from TASK-005.

## Return format

§14 format; include the accepted packet hash, G-A directive ID, and pre/post
rejected-run tripwire values.
