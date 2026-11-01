# Delegated Product Decisions & Remaining External Submission Gates

Recorded in [`docs/planning/DECISIONS.md`](../../../docs/planning/DECISIONS.md) (SHA-256 `639bebcaba808e75697641fd5810b7f2e7e130f4bf4b63eb690259892fcf81f1`) under requester delegation (`remediation_rerun_and_decision_delegation`):

1. **DECISION-01 (`D-06`: Failover Authority & Recovery Acceptance) — `DELEGATED_ACCEPTED` (`PROVISIONAL`)**
   - Stage-operator-confirmed failover (`operator.failover`) restricted to phase boundaries (`turn_tick in {0, 400, 500}`); automatic client takeover rejected; `operator.recover` requires `health_ok=True` and exact `expected_state_hash` match.

2. **DECISION-02 (`D-07`: Data-Only Hotfix Trust & Signing) — `DELEGATED_ACCEPTED` (`PROVISIONAL`)**
   - `booth.hotfix` restricted to `slowdown_fraction` (`[0.0, 0.20]`) and `slowdown_duration_ticks` (`[0, 40]`) with trusted signature (`CODEX_BOOTH_TRUSTED_V1`), monotonic `patch_version`, `expiry_tick`, and turn-boundary activation/rollback.

3. **DECISION-03 (`D-08`: Simulation vs Live Submission Readiness Split) — `DELEGATED_ACCEPTED` (`PROVISIONAL`)**
   - Separates `simulation_and_plan_ready` from `submission_ready: false`; labels all booths as non-sponsor diegetic metaphors; derives unrendered visual/audio/live capabilities honestly as `not_observed`.

4. **DECISION-04 (`D-09` / `ISSUE-SIM-01..03`: Steering Lockout, `100/88` Speed, Booth Waypoints) — `DELEGATED_ACCEPTED` (`PROVISIONAL`)**
   - Synchronized across Revision 5 of `GAMEPLAN-v2.md`, `gameplan-v2.json`, `S1-SIMULATION-PROFILE.md`, and `config/directive-policy.json` Revision 9.

### Remaining External Gate (Non-Blocking for Offline-Slice Development, Blocking for Final Live Submission):
- `live_submission_external_capture` (`gate: "before_live_submission"`): Live external Twitch channel integration, rendered browser/mobile viewport capture, and under-3-minute public demo video recording remain deferred until separate live-submission authorization.
