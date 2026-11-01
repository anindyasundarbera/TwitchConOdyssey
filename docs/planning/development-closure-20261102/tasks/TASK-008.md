---
id: TASK-008
title: Twitch identity linking and canonical command intake
workstream: W5
objective: O3
contract_version: v1.0
status: GATED
risk: HIGH
parallel: PARALLEL_SAFE
dependencies:
  hard: [TASK-005]
  integration: [TASK-006]
  gates: [G-A, G-B, G-C]
owned_paths:
  - "Twitch adapter / intake paths under server/ (PROVISIONAL — finalize via codebase-memory index)"
protected_paths:
  - artifacts/simulations/full-game/**
  - coordination/deterministic_kernel.py
  - config/directive-policy.json
execution_context:
  source_of_truth:
    - docs/planning/S1-SIMULATION-PROFILE.md   (D-03 audience fairness)
    - docs/planning/DECISIONS.md               (DECISION-01 failover, DECISION-02 hotfix trust)
    - docs/planning/GAMEPLAN-v2.md
---

# TASK-008 — Twitch identity linking and canonical command intake

## Gates

G-A, G-B, G-C as in TASK-006. Additional: no live credentials, no Twitch API calls,
no account linking against real services until separate live-integration
authorization. All offline work uses labeled fixtures (weight/quorum/bounty 0).

## Binding acceptance criteria (handoff §8.2, D-03)

1. Live eligibility requires an authenticated platform subject at account level with
   a linked chat/button identity; unlinked input is rejected before the engine; the
   design records explicitly that account-level quota is not one-human proof and
   does not prevent Sybils.
2. At most one influence unit per eligible subject per turn across channels;
   first-valid-receipt wins atomically; transport dedupe is separate from influence
   dedupe; zero replacements.
3. Roster freezes at planning start; joins/leaves apply next turn; reconnect retains
   identity/influence.
4. `clear_lane` quorum: ceil(0.60 × N) frozen-roster votes and ≥1 eligible vote;
   ties/shortfall ⇒ abstain (abstain wins ties); votes bind to the committed hazard
   ID and close at t=20.
5. Bots/fixtures: weight/quorum/vote/bounty contribution 0; always labeled; never
   impersonate a human; never create human-only rewards.
6. Rate limits and rejection statuses use the canonical command schema's
   applied/expired/rejected/duplicate vocabulary end-to-end.
7. Adapter boundary: validation (identity, command type, sequence, timing,
   pause/terminal, dedup) completes before any engine application; adapters never
   mutate state directly.
8. Secrets handling: configuration documented without printing credentials; no
   autoload of unrelated home-directory credentials (directive
   `evidence_independence`).

## Verification contract (post-gates)

- Adapter rejection test matrix (unlinked, duplicate, late, paused, terminal,
  cross-channel double-influence, bot input) — executed only within authorized scope.
- Security review required before merge: identity/linkage, dedup atomicity, rate
  limits, secrets.

## Return format

§14 format; include accepted packet hash and G-A directive ID.
