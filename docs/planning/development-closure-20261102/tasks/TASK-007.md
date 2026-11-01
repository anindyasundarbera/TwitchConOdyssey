---
id: TASK-007
title: Presentation and mobile HUD from canonical engine state
workstream: W4
objective: O3
contract_version: v1.0
status: GATED
risk: MEDIUM
parallel: PARALLEL_SAFE
dependencies:
  hard: [TASK-005]
  integration: [TASK-006]
  gates: [G-A, G-B, G-C]
owned_paths:
  - "client/ presentation paths (PROVISIONAL — finalize via codebase-memory index)"
protected_paths:
  - artifacts/simulations/full-game/**
  - server/engine.py                     (read-only to W4)
  - coordination/**
execution_context:
  source_of_truth:
    - docs/planning/S1-SIMULATION-PROFILE.md   (D-01 HUD clause, D-05)
    - docs/planning/GAMEPLAN-v2.md
    - docs/planning/DECISIONS.md
  engine_interface: "canonical state contract delivered by TASK-006 (state diffs/summaries only)"
---

# TASK-007 — Presentation and mobile HUD

## Gates

G-A, G-B, G-C as defined in TASK-006 (identical semantics; index-gated paths).

## Binding acceptance criteria (handoff §8.2)

1. Usable loop presentation: start/readiness, active play, pause, terminal
   delivery/wipe outcome, restart/next-match handling per the selected plan; no
   extra-turn UI after terminal state.
2. HUD renders ONLY from authoritative engine state/diffs: one route progress meter,
   hazard timer bound to the committed hazard ID, one plain-language
   action/consequence preview, current phase and terminal result; no high-velocity
   chat reading requirement (D-01 HUD clause).
3. Mobile controls map 1:1 to canonical commands (adjacent-lane transitions per
   D-01); rejected/late/duplicate/expired feedback is visible and accessible
   (non-color-only, assistive-technology labelable).
4. Fixture and live modes are visibly distinguishable in the UI; fixture activity is
   never rendered as a Twitch user or live human participation (INV-FIXTURE-LABEL).
5. Mobile layout contract: playable at booth-handheld sizes; error/network states
   are explicit and recoverable; no physics or state mutation from presentation.
6. No unsupported promotional or live-service claims anywhere in copy
   (INV-CREDIBILITY).

## Verification contract (post-gates)

- Presentation-state tests per phase/terminal/rejection state, run only with the
  requisite authorization scope; offline fixture rendering tests permitted only
  within accepted packet scope.
- Rejected/duplicate input feedback paths covered explicitly.

## Return format

§14 format; include accepted packet hash and G-A directive ID.
