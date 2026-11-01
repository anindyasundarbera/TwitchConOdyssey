---
id: TASK-009
title: Booth telemetry and privacy-bounded evidence
workstream: W6
objective: O3
contract_version: v1.0
status: GATED
risk: MEDIUM
parallel: PARALLEL_SAFE
dependencies:
  hard: [TASK-005]
  integration: [TASK-006, TASK-010]
  gates: [G-A, G-B, G-C]
owned_paths:
  - "booth/telemetry paths (PROVISIONAL — finalize via codebase-memory index)"
protected_paths:
  - artifacts/simulations/full-game/**
  - evidence/remediation-kernel-20261101/**  (W1-owned history; new evidence files only via accepted packets)
execution_context:
  source_of_truth:
    - docs/planning/S1-SIMULATION-PROFILE.md   (booth waypoints 35/60/80/100)
    - docs/planning/DECISIONS.md
    - EVIDENCE.md                              (repo evidence conventions)
---

# TASK-009 — Booth telemetry and privacy-bounded evidence

## Gates

G-A, G-B, G-C as in TASK-006.

## Binding acceptance criteria (handoff §8.2/§8.3)

1. Telemetry is privacy-bounded: no unnecessary personal data; identity fields carry
   pseudonymous subject handles only as required by D-03 accounting; retention and
   redaction rules documented.
2. Every gameplay outcome event is attributable: match ID, committed hazard ID,
   command sequence reference, and logical tick linkage sufficient to audit
   settlement — without embedding chat content or credentials.
3. Fixture/simulation activity is never represented as live human participation in
   any emitted event, metric, or evidence artifact (INV-BOT-ISOLATION,
   INV-FIXTURE-LABEL); fixture-origin events carry an explicit origin label.
4. Telemetry cannot mutate gameplay state; it observes canonical engine/stream
   outputs only.
5. Booth waypoint events derive from the selected geometry only
   (35.0/60.0/80.0/100.0), never re-derived from memory.
6. Evidence output format matches repo conventions (manifest + per-artifact SHA-256)
   so TASK-010 can package and TASK-011 can verify.

## Verification contract (post-gates)

- Event-linkage audit test: for each terminal outcome, telemetry chain reconstructs
  the outcome from engine traces within authorized execution scope.
- Integrity review for all evidence/telemetry artifacts (hashes, no PII leakage,
  origin labels correct).

## Return format

§14 format; include accepted packet hash and G-A directive ID.
