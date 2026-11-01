---
id: TASK-010
title: Submission/demo pipeline and evidence packaging
workstream: W7
objective: O3
contract_version: v1.0
status: GATED
risk: MEDIUM
parallel: SERIAL_REQUIRED
dependencies:
  hard: [TASK-005]
  integration: [TASK-006, TASK-007, TASK-008, TASK-009]
  gates: [G-A, G-B, G-C]
owned_paths:
  - "submission/demo tooling + evidence/ documentation paths (PROVISIONAL — finalize via index)"
protected_paths:
  - artifacts/simulations/full-game/**
  - evidence/remediation-kernel-20261101/**
execution_context:
  source_of_truth:
    - docs/planning/DECISIONS.md               (DECISION-03 submission/live separation)
    - EVIDENCE.md, README.md
    - docs/planning/development-closure-20261102/verification/DEVELOPMENT-CLOSURE-VERIFICATION.md
---

# TASK-010 — Submission/demo pipeline and evidence packaging

## Gates

G-A, G-B, G-C as in TASK-006. Additionally, live external capture (external Twitch
channel integration, rendered viewport capture, 3-minute public demo video) remains
behind the unresolved decision `live_submission_external_capture`
(gate `before_live_submission`) and requires its own explicit authorization —
unreachable in this task without it. External submission and publishing are NEVER in
scope for this plan.

## Binding acceptance criteria

1. Reproducible offline build and fixture-run instructions: single documented
   sequence from clean checkout to local fixture demo; fixtures never require live
   credentials; cleanup instructions included.
2. Demo evidence package: manifest of every artifact with SHA-256; explicit labeling
   of what is fixture-backed simulation evidence versus live-validated evidence
   (nothing in this task produces live-validated evidence).
3. Service configuration and failure-handling documentation (start/verify/stop,
   common failure modes) without credential printing or unrelated-credential
   autoloads.
4. Readiness reporting honestly derived: the packaged record preserves
   `submission_ready: false` and states which `before_live_submission` items remain
   open; no production/live-readiness claims from simulation evidence
   (DECISION-03 separation, INV-CREDIBILITY).
5. Work-package tracking: the five packages (WP-01 core engine, WP-02 HUD/mobile,
   WP-03 Twitch linking, WP-04 booth telemetry, WP-05 demo pipeline) each tracked
   separately with per-package evidence state, matching the sealed readiness
   record's `required_work_packages_order`.

## Verification contract (post-gates)

- Fresh-clone reproduction of the documented build sequence; evidence-package hash
  verification; failure-path walk-through recorded.

## Return format

§14 format; include accepted packet hash, G-A directive ID, and package manifest digest.
