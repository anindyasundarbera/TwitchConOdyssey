# GAMEPLAN v1 — San Diego route and PLAN rehearsal

**Status:** Initial plan, unreviewed. **Approved setting:** San Diego, per the user. **This artifact authorizes planning and role-based critique only.** Gameplay simulation is deferred: do not simulate ticks, moves, state transitions, or claim outcomes. `gameplay_simulation_enabled` remains `false` in the companion JSON.

## Product thesis and route

A streamer carries a build through a stylized San Diego while viewers, the in-game character, an attacker role, and a stage operator coordinate around bounded hazards. The enemy remains unstructured scale. The route is a compressed level sequence, not a street-by-street map or GIS claim:

**Little Italy / North Embarcadero → Embarcadero waterfront / Marina → Gaslamp Quarter → San Diego Convention Center → fictional Main Stage.**

The City describes Little Italy as near the North Embarcadero waterfront. The Convention Center visitor guide places the Embarcadero on the venue’s west side, the Gaslamp Quarter just outside the venue, and MTS Trolley stops in front of the venue. These support the setting and visual anchors, not the exact sequence, walking distance, street geometry, or a real Main Stage. See [SAN-DIEGO-ROUTE.md](SAN-DIEGO-ROUTE.md).

## Loop and slice proposal

Target cadence remains **20 seconds planning, 5 seconds input-locked resolution, about 5 seconds reward**. Movement remains continuous during planning. The first proposed slice covers **Little Italy only**, with one fictional blocked-demo-lane hazard and one proposed clear-lane counter. This gives role reviewers one legible hazard/counter pair. It does not select player controls, exact effects, costs, or formulas.

## Role plans for critique

- **Streamer:** Keep the build moving along the route; weigh a viewer counter-move against progress. Identify which information and control are needed before committing.
- **Viewer:** Submit one bounded action through a one-click control or short chat trigger; natural language may propose an action but never directly executes it. One eligible viewer has at most one unit of influence per turn; squad count `K` is configurable, with bot backfill visible.
- **Character:** Continue movement during planning and encounter the lane hazard through authoritative game rules. Movement inputs, collision response, and recovery are open decisions.
- **Attacker:** Introduce only the single fictional hazard in this slice, inside explicit limits. The role cannot target or punish real viewers, permanently remove control, or cause unavoidable death.
- **Stage operator:** Observe phase, route progress, health, input validation, and the simulated bounty/reward ledger. Keep the stage destination fictional and verify the offline path can present the same plan without external credentials.

## Unexecuted PLAN rehearsal script

This is a review script for adversarial role critique, not a run. Reviewers should inspect whether the plan handles (1) a valid viewer clear-lane proposal, (2) ambiguous or schema-invalid chat, (3) a duplicate or late submission, (4) attacker pressure at the stated safety boundary, and (5) offline presentation when the provider is unavailable. Expected behavior is a requirement to assess, not an observed result: only locally validated, in-phase, idempotent commands may become eligible; closed-phase input is rejected; model output remains a proposal. If the counter wins under a future approved rule set, it should address the hazard; if it does not, the unresolved collision/recovery rule must decide the consequence. No numerical effects or outcomes are assumed here.

The 5-second reward phase exposes a simulated collective bounty: human-created in-game danger increases it, survival rewards the streamer and audience, and a wipe reduces or withholds reward. The formulas remain open. The broader experience keeps the offline deterministic fixture, optional synthesized/adaptive audio, AI chat-to-action proposal/validation boundary, diagnostic Codex Booth (sanitized evidence → data/rules proposal → deterministic fixture → validated manifest at a safe boundary; no executable hot-loading), fictional Twitch moderation-to-Hype and IVS congestion-to-speed-lane concepts, and spectator/bounty roles. Brand rights, platform integration, and real payouts are not implied.

## Decisions still open

Choose movement/control scheme; hazard and counter activation, timing, costs, and effects; wipe definition and recovery; bounty creation, survival/wipe adjustment, and streamer/viewer allocation; `K` and cohort fairness/bot behavior; and the exact phase/reward presentation. Do not reuse legacy fixed four squads, a 25-second total loop, or fixed credit/action values as approved rules. The full route’s exact art and geography also remain proposals.

## PLAN review gates

1. Every role can identify its allowed input, authority boundary, and safe failure behavior.
2. The first slice contains one district, one hazard, and one counter; unresolved mechanics are visible.
3. The plan preserves configurable N→K audience participation, one influence unit per eligible viewer per turn, visible non-rewarding bots, collective simulated bounty, AI/Codex proposal boundaries, offline operation, and opt-in audio.
4. No role report is described as gameplay evidence. Gameplay simulation requires a later explicit authorization after plan gaps are reviewed.

**Sources checked 2026-11-01:** [Convention Center — Getting Here & Around](https://www.visitsandiego.com/attendees/getting-here-around); [City of San Diego — Little Italy](https://www.sandiego.gov/citycouncil/cd3/communities/littleitaly).
