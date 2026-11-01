# Plan Changelog — Synchronized Revision 5

- **Base Revision:** Revision 4 (2026-11-01)
- **Synchronized Revision:** Revision 5 (2026-11-01)
- **Authoritative Plan SHA-256 (`docs/planning/GAMEPLAN-v2.md`):** `d7da3bc1d390a7f1ec37412c9b8d9c455eb54f43e9eefc26b95dc76b43df6752`
- **Authoritative Machine Plan SHA-256 (`docs/planning/gameplan-v2.json`):** `6e20481549e188472a8369041760495a15d033a97fa3aa8898bf7d04f3b13147`
- **Delegated Decision Ledger (`docs/planning/DECISIONS.md`):** `639bebcaba808e75697641fd5810b7f2e7e130f4bf4b63eb690259892fcf81f1`

### Synchronized Remediation Changes:
1. **`ISSUE-SIM-01` (`D-01` Steering Interpolation, Transition Lockout & Edge Clamping):**
   - Transition duration is `0.5s` (`10` ticks at `20 Hz`) across discrete lanes `[0, 2]`.
   - Lateral movement is clamped to `[0, 2]`; edge steering inputs fail closed (`rejected`).
   - Steering inputs received while `transition_remaining_ticks > 0` are rejected (`transition_lockout`).
   - Same-tick opposite steering inputs cancel out.

2. **`ISSUE-SIM-02` (`D-02` / `D-05` Base Travel Speed & Route Calibration):**
   - Route length is `100.0` distance units across the 5 San Diego districts (`[0,25), [25,50), [50,75), [75,95), [95,100]`).
   - Nominal free speed is exact rational `100/88` units/s (`88.0s` nominal arrival; `89.2s` with max 3 collisions, strictly preceding the `90.0s` deadline).

3. **`ISSUE-SIM-03` (`DECISION-04` Diegetic Booth Waypoints):**
   - Twitch Booth (`twitch_booth`): progress `35.0%` (Embarcadero Waterfront / Marina).
   - Codex Live Hotfix Booth (`codex_booth`): progress `60.0%` (Gaslamp Quarter).
   - AWS / Amazon IVS Booth (`aws_booth`): progress `80.0%` (San Diego Convention Center).
   - Fictional Main Stage (`fictional_main_stage`): progress `100.0%`.

4. **`DECISION-01..03` (`D-06` Failover, `D-07` Hotfix Allowlist/Signing, `D-08` Readiness Scope Separation):**
   - Recorded in `docs/planning/DECISIONS.md` and synchronized across `GAMEPLAN-v2.md` Revision 5, `gameplan-v2.json` Revision 5, `S1-SIMULATION-PROFILE.md`, and `config/directive-policy.json` Revision 9.
