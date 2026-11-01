# Decisions

## ADR-001 — Dependency-free local runtime
Use Python >=3.11 standard library for fixed-step engine, HTTP and SQLite; plain canvas ES module for client. Avoid package downloads for stage resilience. JSON Schema QA and Playwright are optional development tools. No framework/build step required.

## ADR-002 — Separate proposals from authority
An asynchronous bounded worker receives chat and telemetry diffs. Structured model output is only a proposal. Strict contract, captured-round and phase checks precede execution. OpenAI timeouts never hold the simulation lock. Live adapter exists but is not credential-tested.

## ADR-003 — Reproducibility over probabilistic demo behavior
Use SHA-256 cohort assignment, Fraction vote math, fixed action tie order and deterministic bot policy. Pin fixture output digest. Earned pool credits are simulated; no payment service is invoked.

## ADR-004 — Small evidence harness instead of full Harness² dependency
Harness² describes task-level Propose–Probe–Compose refinement plus persistent evidence-supported lessons. Adopt task selection, scoped context, probe/checkpoint/history concepts in a local CLI. No recursive model optimizer or benchmark infrastructure needed for this demo. This is an equivalent scoped workflow, not a Harness² implementation.

## ADR-005 — Scope and verification honesty
Browser buttons simulate Extension controls. Real Twitch authentication/EventSub, Extension packaging, AWS/IVS API integration and cash payouts are future work. Sandbox socket denial is an environmental release blocker; in-process HTTP transport checks complement but cannot replace real startup and browser E2E.

## ADR-006 — San Diego is the sole target setting
On 2026-11-01, the user approved San Diego as the game setting. The current planning target maps a stylized route through Little Italy/North Embarcadero, the Embarcadero waterfront, Gaslamp Quarter, and the San Diego Convention Center before a fictional Main Stage. Earlier location concepts were removed from the repository. Active runtime labels, map copy, and district names were migrated before simulation; that migration does not claim that route geometry or gameplay has been verified.

## ADR-007 — Same-Day Deterministic Evidence Remediation & Delegated Decisions (D-06, D-07, D-08, Booth Placement)
On 2026-11-01, following the rejected simulation checkpoint (`docs/planning/SIMULATION-EVIDENCE-AUDIT.md`), the requester granted explicit authorization for fresh simulation runs under new run roots and delegated resolution of `D-06` (failover authority), `D-07` (data-only hotfix trust), `D-08` (submission vs simulation readiness separation), and diegetic booth placement/clarifications (`ISSUE-SIM-01..03`). Full evidence-backed records, options, blast radius, and reversal costs are recorded in [`docs/planning/DECISIONS.md`](docs/planning/DECISIONS.md).

