# 06_DIVERGENCES — Divergence Analysis

Recorded: 2026-11-02T00:36:00+05:30  
Remediation ID: `20261101T234500Z`

## 1. Divergence Summary

| Category | Planned vs Actual | Divergence Detected | Resolution / Justification |
|---|---|---|---|
| **Kernel Location** | `coordination/deterministic_kernel.py` | NONE | Pure module with zero I/O, no wall clock, no model/service dependencies. |
| **Consumer Rewiring** | `server/engine.py` & `coordination/full_game_simulator.py` | NONE | Both rewired to call the shared kernel functions. |
| **Tick Ordering** | Deadline wipe evaluated first; commands apply strictly < 1800; equality wipe wins | NONE | Implemented and verified by `TST-01..TST-03` and `TST-09..TST-10`. |
| **Warning Interval** | Half-open `[300, 400)` bound to committed hazard ID | NONE | Implemented and verified by `TST-04..TST-08`. |
| **Invariant Evaluation** | Dedicated validators for 6 pipeline invariants; per-property checks for scenarios | NONE | Implemented and verified by `TST-16..TST-20`. |
| **Historical Preservation** | Run `full-game-20261101T174648Z-2647e033` unchanged | NONE | Verified 100% byte-for-byte identical (tree SHA-256 `b79455d3...`, review `937dd798...`). |
| **Independent Review** | `codex_subagent/gpt-6-astra` at `high` reasoning effort | NONE | Observed subagent review returned `READY`; recorded in `INDEPENDENT-REVIEW.md`. |
| **Readiness Gate** | Evidence-derived `ready: true`, `submission_ready: false` | NONE | Maintained strictly separated in `DEVELOPMENT-READINESS.json`. |

## 2. Intentional Oracle Synchronizations

As noted in Astra's review of the prior run (`"Movement precedes clock advancement; existing oracles encode the early timestamp"`), 11 scenarios in `coordination/run_full_game_simulation.py` that run until delivery previously recorded arrival at tick `1759` (or `400`, `1767`, `1775`, `35`) because delivery was evaluated before incrementing the tick counter.

With the tick counter incrementing as each 50ms interval concludes, arrival occurs at tick `1760` (or `401`, `1768`, `1776`, `36`). These 11 oracle expectations were synchronized to match the corrected integer tick semantics. All 46 scenario matrix contracts now pass with 100% oracle and invariant agreement.
