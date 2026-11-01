# Plan Changelog — Revision 5 Candidate

- **Base Revision:** Revision 4 (2026-11-01)
- **Candidate Revision:** Revision 5 (2026-11-01)
- **Author:** Principal Simulation Orchestrator
- **Scope:** Minimal deterministic clarifications required to make selected S1 mechanics executable without changing product scope.

### Clarifications Recorded:
1. **D-01 Steering Interpolation & Edge Clamping:**
   - Transition duration is exactly 0.5s (10 ticks at 20 Hz).
   - Lateral movement is clamped to lanes [0, 2].
   - Inputs received while a transition is in flight are rejected (no queueing or overwrite).
   - Same-tick opposite inputs cancel out.

2. **D-05 Base Travel Speed & Route Calibration:**
   - Base free speed is calibrated to complete the 100-unit route in 88.0 seconds nominal (~1.1364 units/s).
   - Three maximum collisions (20% slowdown for 2s each = 0.4s travel loss per turn = 1.2s total delay) complete at t=89.2s, strictly before the 90.0s deadline.

3. **Diegetic Booth Placement:**
   - Twitch Booth: progress 35.0% (waterfront / Marina).
   - Codex Live Hotfix Booth: progress 60.0% (Gaslamp Quarter).
   - AWS / Amazon IVS Booth: progress 80.0% (San Diego Convention Center).
   - Fictional Main Stage: progress 100.0%.
