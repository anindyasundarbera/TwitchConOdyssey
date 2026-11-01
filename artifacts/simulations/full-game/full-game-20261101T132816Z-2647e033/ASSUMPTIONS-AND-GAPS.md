# Prerequisites, Assumptions, and Evidence Gaps

Before tick 0, all deterministic clarifications, delegated product decisions, and capability boundaries were classified:

### 1. Deterministic Clarifications & Delegated Remediation Decisions (Synchronized in Revision 5)
- **ISSUE-SIM-01 (`D-01` Steering Interpolation, Lockout & Edge Clamping):** 3 discrete lanes `0, 1, 2` (width `1.0` unit); `0.5s` (`10`-tick at `20 Hz`) linear interpolation; inputs during an active transition return `rejected`; edge moves from lane `0` left or lane `2` right return `rejected`; same-tick opposite inputs cancel.
- **ISSUE-SIM-02 (`D-02` / `D-05` Route Speed Calibration):** `100.0` distance units across the 5 stylized San Diego districts at exact nominal speed `100/88` units/s (`88.0s` nominal completion; `89.2s` with maximum 3 collisions, strictly before the `90.0s` / `1800`-tick deadline).
- **ISSUE-SIM-03 (`DECISION-04` Diegetic Booth Waypoints):**
  - Twitch Booth (`twitch_booth`): progress `35.0%` (Embarcadero Waterfront / Marina)
  - Codex Live Hotfix Booth (`codex_booth`): progress `60.0%` (Gaslamp Quarter)
  - AWS / Amazon IVS Booth (`aws_booth`): progress `80.0%` (San Diego Convention Center)
  - Fictional Main Stage (`fictional_main_stage`): arrival threshold `100.0%`
- **DECISION-01 (`D-06` Failover & Recovery Boundary):** Stage-operator-confirmed failover (`operator.failover`) valid strictly at safe phase boundaries (`turn_tick in {0, 400, 500}`); live recovery (`operator.recover`) requires health check and exact canonical `state_hash` match.
- **DECISION-02 (`D-07` Data-Only Hotfix Trust & Rollback):** Trusted-key signed `booth.hotfix` restricted to `{"slowdown_fraction", "slowdown_duration_ticks"}` within safety caps (`[0.0, 0.20]` and `[0, 40]`), monotonic version, valid expiry, activating strictly at turn boundary (`turn_tick == 0`) with turn-boundary rollback (`operator.rollback_hotfix`).
- **DECISION-03 (`D-08` Readiness Scope Separation & Honest Coverage):** Separates `simulation_and_plan_ready` from `submission_ready` (`false` until external live Twitch and rendered video capture).

### 2. Unobserved Capabilities in Headless Deterministic Simulation (`AUDIT-04`)
- `FEAT-14-READABILITY-AND-HUD`: Browser/mobile viewport rendering and compressed-video readability are `not_observed` in headless deterministic execution.
- `FEAT-12-BULLET-TIME-PRESENTATION`, `FEAT-13-ADAPTIVE-AUDIO`, `FEAT-15-PUBLIC-DEMO-TIMELINE`: State-machine, tick-progression, and claim-provenance contracts are verified (`partially_observed_state_only`), while visual Canvas interpolation, Web Audio acoustic output/voiceover intelligibility, and rendered 3-minute video capture remain `not_observed` until browser/live verification.
