# Prerequisites, Assumptions, and Plan Gaps

Before the first state transition, prerequisites were identified and classified:

### 1. Deterministic Clarifications (Resolved in Simulation Support)
- **Geometry & Coordinate Bounds:** 3 discrete lanes: 0 (left), 1 (center), 2 (right), width = 1.0 unit.
- **Lane Transition:** 0.5s duration = 10 ticks at 20 Hz. Linear interpolation across lateral position.
- **Edge Clamping:** Inputs moving left from lane 0 or right from lane 2 fail closed without moving.
- **Transition Lockout:** Inputs received during an active transition are rejected until transition completes.
- **Same-tick Opposites:** Simultaneous left + right requests cancel out.
- **Base Free Speed:** 100.0 distance units over 88.0s nominal free travel (~1.1364 units/s), leaving 2.0s buffer so maximum 3 collisions (1.2s delay) arrive at 89.2s strictly before the 90.0s deadline.
- **Obstacle Placement:** Fixed center lane (lane 1), active during first 3.0s of resolution (ticks 0..60).
- **Collision Envelope:** Avatar lateral overlap within |x - 1.0| < 0.4 during active hazard ticks triggers collision once per obstacle.
- **Booth Progression:**
  - Twitch Booth: waterfront / Marina (progress 35.0%)
  - Codex Live Hotfix Booth: Gaslamp Quarter (progress 60.0%)
  - AWS / Amazon IVS Booth: San Diego Convention Center (progress 80.0%)
  - Main Stage: arrival threshold (progress 100.0%)

### 2. Product Decisions (Deferred to Human Approval in HUMAN-DECISIONS.md)
- D-06: Live failover authority
- D-07: Data-only hotfix signing/trust/activation design
- D-08: Submission readiness & live demonstration evidence

### 3. Evidence and Implementation Gaps
- Live Twitch/IVS network latency and mobile rendering readability remain unobserved in deterministic local execution.
