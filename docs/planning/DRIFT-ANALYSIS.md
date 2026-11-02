# TwitchCon Odyssey — System, Visual, and Architectural Drift Analysis

**Date:** 2026-11-02  
**Status:** Canonical Project Record — Reconciled Post-Overhaul  
**Repository:** `/home/anindyasundar-bera/Projects/hackathon/TwitchConOdyssey`  
**Authorization Context:** `gate_to_game_interface_authorization_20261102` (Directive Ledger Revision 16)  
**Readiness State:** `submission_ready: false` (Preserved — Pending Authorized Live Video Evidence)

---

## 1. Executive Summary

This drift analysis provides an exhaustive, honest architectural record of the design, gameplay, visual, and operational transformations executed to transition TwitchCon Odyssey from an early diagnostic wireframe into a cohesive, fullscreen, synthwave cyberpunk arcade runner.

The analysis evaluates drift across seven critical dimensions:
1. **Authorization Gate Drift:** Transition from a closed gameplay gate to an explicitly authorized local execution scope.
2. **Visual & Aesthetic Drift:** Evolution from an unpolished 2D "Google Maps" wireframe to a 3D perspective synthwave arcade runner.
3. **HUD & Layout Drift:** Reduction of a viewport-blocking 440px text card to an upper-left 300px avionics flight HUD.
4. **Input & Control Ergonomics Drift:** Migration from external HTML page buttons to fully integrated in-game keyboard (`A`/`D`, `ESC`, `M`, `F11`) and mobile touch overlays.
5. **Viewer & Audience Simulation Drift:** Adaptation from theoretical live Twitch EventSub to active, real-time loopback REST simulation (`tools/simulate_demo_match.py`).
6. **Model Routing & AI Verification Drift:** Reconciliation between remote `gpt-6-astra` routing policy and local paired model execution with honest attestation reporting.
7. **Readiness Predicate Audit:** Separation of 30 satisfied local/offline verification invariants from 53 open live/external submission predicates.

---

## 2. Gate and Authorization Drift

| Property | Initial Project State (Rev 14/15) | Post-Overhaul Reconciled State (Rev 16) | Operational Drift Justification |
| :--- | :--- | :--- | :--- |
| **Compiler Gate** | `gameplay_enabled: false` | `gameplay_enabled: true` | Explicit user authorization directive recorded verbatim: *"Everything means including the blocked gate as well then ui and design"*. |
| **Active Directive** | `rehearsal_lock_20261101` | `gate_to_game_interface_authorization_20261102` | Superseded former gate while preserving exact historical byte integrity. |
| **Local Game Service** | Forbidden (`server.app` rejected) | Authorized on loopback `127.0.0.1:8000` | Necessary to validate real runtime engine stepping and websocket/HTTP endpoints. |
| **Browser Gameplay & Capture** | Forbidden | Authorized (Playwright headless & manual) | Validated desktop (1440x1100) and mobile (390x844) viewports. |
| **External & Live Gate** | Forbidden | **Strictly Forbidden** (Unchanged) | Zero credential exposure, no live Twitch calls, no YouTube upload, no Devpost submission. |

### Integrity Tripwire & Anti-Forgery
The gate reconciliation was not achieved via an ad-hoc boolean flip. The compiler (`coordination/context_contract.py`) strictly enforces:
- Exact verbatim user authorization wording present in bound project records.
- Bidirectional supersession pointers between active and historical directives.
- SHA-256 byte hashing of all bound governance documents.

---

## 3. Visual and Aesthetic Architecture Drift

```
[ BEFORE: Utility Wireframe ]                   [ AFTER: Synthwave 3D Runner ]
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│ [440px Diagnostic Grey Card]    │           │ [HUD] 300px Avionics      [☀️]  │
│ - District: Little Italy        │           │  Speed: 100/88 u/s   Sunset Blinds│
│ - Phase: planning               │           │  Hype Pool: 60       Coronado Cbls│
│ - Turn: 1, Tick: 120            │           │                                 │
│ [2D Wireframe Route Line]       │    ───►   │      ══════╦══════             │
│   (o) Runner Dot                │           │            ║ Landmark Gantry    │
│                                 │           │  [Hazard]  ║ Crimson Laser Bar  │
│ [External Buttons Below View]   │           │   ▲ Courier Sprite (Blue Jets)  │
│ [Steer L] [Steer R] [Pause]     │           │ /=============================\ │
└─────────────────────────────────┘           └─────────────────────────────────┘
```

### Key Visual Changes:
1. **Perspective Track Geometry:** Replaced flat 2D lines with a 3D perspective highway utilizing dynamic vanishing point projection, alternating cyan (`#00f0ff`) and magenta (`#ff007f`) racing curb stripes, and high-contrast lane dividers.
2. **Atmospheric Environment:**
   - Giant retro synthwave sun with horizontal Venetian blinds and radial amber/crimson gradients.
   - Dynamic San Diego skyline featuring the architectural sail pavilions of the San Diego Convention Center and Coronado Bridge cable stays.
   - Twinkling starfield with deterministic pseudorandom seed.
   - Animated San Diego Bay water reflections with glowing typography (`S A N  D I E G O  B A Y`).
3. **Courier Runner Presentation:**
   - Replaced the abstract circular point with an athletic cyberpunk courier sprite wearing an illuminated `BUILD` container backpack.
   - Dual blue hover-skate jet flames with dynamic particle trail flicker.
   - Dynamic lateral banking tilt (±0.18 rad) during lane transitions.
   - Deceleration spark aura during turn slowdowns.
4. **Holographic Hazards & Landmark Gantries:**
   - Roadblocks render as holographic security barriers with flashing amber warning strobes, caution chevrons, and red laser bars.
   - Countered hazards visually transition to green pass-through gateways (`✔ CLEAR_LANE COUNTERED`).
   - Waypoint gantries span all three lanes with glowing neon banners for each district (`LITTLE ITALY`, `GASLAMP QUARTER`, `CONVENTION CENTER`, `FICTIONAL MAIN STAGE`).

---

## 4. HUD and Layout Architecture Drift

| Element | Prior Implementation | Overhauled Implementation |
| :--- | :--- | :--- |
| **Viewport Footprint** | Centered 440px wide grey opaque card blocking 65% of canvas track view. | Compact 300px glassmorphism avionics widget anchored to top-left (`padding: 12px`, backdrop blur). |
| **Track Visibility** | Heavily obscured; runner was hidden behind text boxes. | 100% unobstructed view of track, horizon, hazards, and runner. |
| **Controls Placement** | HTML buttons located outside and below the game canvas. | In-game modals, keyboard hotkeys, and translucent on-canvas touch controls for mobile. |
| **Modals & Drawers** | Basic browser alert boxes or unstyled divs. | Synthwave neon-bordered modal dialogs: Start Briefing, Pause/Settings Drawer, Terminal Settlement. |
| **Keyboard Ergonomics** | Arrow keys only. | Dual support: `[A]` / `[D]` and `[←]` / `[→]` for steering; `[ESC]` for pause; `[M]` for sound; `[F11]` for fullscreen. |

---

## 5. Audience Mechanics and Viewer Simulation Drift

### Initial Plan vs. Current Verification Reality
- **Original Architecture:** Required active live Twitch WebSocket EventSub connection, OAuth user tokens, and broadcaster chat channel listening.
- **Current Development Reality:** Live credentials and external network calls remain blocked by gate policy.
- **Drift Resolution:** Developed `tools/simulate_demo_match.py` to drive high-fidelity viewer participation over the authoritative loopback HTTP server:
  - 5 simulated audience personas (`@viewer_neon_fox`, `@viewer_bay_phantom`, `@viewer_pixel_pirate`, `@viewer_gaslamp_pro`, `@viewer_convention_fan`).
  - Active submission of hazard proposals, speed boosts, and `clear_lane` counter-votes via `/api/chat`.
  - Rate limiting enforcement (0.3s cooldown per viewer) and planning window cutoff (half-open $[0, 20)$ interval).
  - Streamer evasion steering commands dispatched via `/api/command`.
  - Complete execution logged to `evidence/ui-readiness/20261102T161855Z/VIEWER-ACTION-SIMULATION.json`.

---

## 6. Model Routing and AI Verification Drift

1. **Policy Allocation:**
   - Policy specifies `codex_subagent` using `gpt-6-astra` (`reasoning_effort: high`) for the independent design and readiness review.
2. **Drift in Execution:**
   - Remote OpenAI serving endpoints are not reachable in this isolated, network-sandboxed environment.
   - Operating under the policy rule: `serving_attestation_unavailable_is_not_a_substantive_blocker: true`.
   - The review was conducted using an independent reviewer subagent (`fc1a9ef0-0302-4f20-afd3-6b41c5efc061` - `astra_reviewer`), maintaining strict separation from the authoring worker agents.
   - All reviews and status reports explicitly note `serving_attestation_available: false` rather than fabricating synthetic provider headers.

---

## 7. Readiness Predicate Audit Matrix

The repository tracks 83 readiness predicates across offline and live dimensions:

| Predicate Category | Total Count | Satisfied (Passed) | Pending / Blocked | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Deterministic Kernel** | 12 | 12 | 0 | Strict physics, 20Hz ticks, collision, scoring. |
| **Context & Gate Contract** | 8 | 8 | 0 | Revision 16 directive ledger, byte hash integrity. |
| **UI & Presentation Shell** | 10 | 10 | 0 | Fullscreen, avionics HUD, 1440x1100 & 390x844 responsive. |
| **Live Twitch EventSub** | 22 | 0 | 22 | Blocked: Requires live Twitch client ID/secret. |
| **Live Broadcast Video** | 18 | 0 | 18 | Blocked: Requires authorized live stream capture (<180s). |
| **Platform Publication** | 13 | 0 | 13 | Blocked: YouTube upload & Devpost final submit. |
| **TOTAL** | **83** | **30** | **53** | `submission_ready: false` enforced. |

---

## 8. Preserved Invariants and Next Actions

1. **Preserved Invariants:**
   - Dirty-worktree modifications by the user remain untouched.
   - No historical v1 or research artifacts were altered.
   - Authoritative game physics and outcome calculation remain 100% deterministic in Python kernel.
   - `submission_ready: false` remains locked until external live broadcast evidence is recorded under separate user instruction.

2. **Next Steps for Final Submission (When Authorized):**
   - Provide real Twitch application credentials in a controlled environment.
   - Conduct live interactive stream with real chat participants.
   - Record observed gameplay video under 180 seconds demonstrating audience counter-votes and delivery settlement.
   - Update submission metadata and hash bindings before running Devpost packaging.
