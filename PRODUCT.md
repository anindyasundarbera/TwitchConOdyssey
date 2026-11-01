# TwitchCon Odyssey: San Diego Crisis

**Current setting:** San Diego is the user-approved target setting. The proposed stylized route and first slice are documented in [GAMEPLAN-v2.md](docs/planning/GAMEPLAN-v2.md) and [SAN-DIEGO-ROUTE.md](docs/planning/SAN-DIEGO-ROUTE.md). V2 restores requirements after the v1 plan rehearsal; it is not yet approved or gameplay-tested.

**Planning status:** This product target is not gameplay evidence. Active runtime labels, map copy, and district names now use San Diego; route geometry and mechanics remain unverified until the separately authorized simulation phase. Superseded city references remain only in frozen history and decision records.

## Objective
A credential-free, trailer-ready local co-op game: a streamer delivers a build across a stylized San Diego while viewers in configurable rival squads influence bounded counter-moves and sabotage. The full route ends at the San Diego Convention Center and a fictional Main Stage; the first proposed slice covers Little Italy only.

## Product targets beyond the first slice
- R01: Fixed 20 Hz authoritative simulation; 20-second planning, 5-second input-locked resolution, and about 5-second reward windows; stale/closed votes rejected.
- R02: Stable N→K assignment with configurable K, at most one influence unit per eligible viewer, fractional choices, normalized squad influence, deterministic tie handling, visible bot backfill and bounded counter-moves.
- R03: Strict chat proposals, adversarial/ambiguous rejection in mock mode, asynchronous bounded provider adapter, local schema and rule validation.
- R04: Ordered offline fixture, no external credentials/network, pinned deterministic replay reaches the fictional Main Stage. The planned San Diego route is Little Italy/North Embarcadero → Embarcadero waterfront/Marina → Gaslamp Quarter → San Diego Convention Center; first slice is Little Italy only. The map is stylized, not geographic GIS.
- R05: Canvas client displays phase, integrity, progress, crisis, squad votes, sponsor controls, simulated bounty, pipeline inspector and adaptive synthesized audio.
- R06: SQLite append-only events, snapshots including player/cohort/vote state; trace chat/proposal/validation/execution; deterministic accepted-event replay.
- R07: Requirements/tasks/context/evaluation/checkpoint schemas; independent evaluation gate, task selection, compact context and checkpoint provenance; failures become tasks.
- R08: Mock API startup, client/server contract and browser end-to-end gameplay verified where execution environment permits. Environmental blockers must remain visible and fail release gate.

The existing `harness/requirements.json` mappings describe the legacy prototype and have not been reconciled or rerun against this revised plan. The first proposed offline slice is one district, one hazard and one counter; full-route, audience, hotfix and presentation targets do not all belong in that slice. See v2 for separate plan, offline-slice and submission gates. Blocked checks are never passes.

## Offline-slice scope boundaries
Local single-match demo. One-click browser controls simulate Extension input; no registered Twitch Extension, EventSub subscription, real payouts, AWS provisioning, source-code hot-patching or public deployment. Live OpenAI parsing is optional and requires credentials; no live call is needed for acceptance. Sponsor names describe proposed fictional game abilities, not actual API execution or sponsorship. Map is stylized, not a geographically accurate GIS twin. Bounty is a simulated accounting ledger; its formulas remain open. Bullet time freezes the inspector only. Adaptive synthesized or licensed audio is opt-in.

These local/offline boundaries do not establish hackathon readiness. Actual Twitch functionality, Codex build/session evidence and the required permitted demo need their own later verification. The original hard constraints also remain: bots cannot create farmable bounty; cumulative effects cannot cause stun-lock or unbounded damage; model I/O cannot block authority; live/fixture provenance must remain truthful.

## Rules
The current intent is one influence unit per eligible viewer per turn, configurable N→K squads, visible bot backfill, and bounded moves that cannot create unavoidable death or permanent control loss. Human-created in-game danger increases a collective simulated bounty; survival rewards the streamer and audience, while wipes reduce or withhold rewards. The exact controls, action effects, wipe definition, bounty formula, and reward split are unresolved and require plan review.

**Legacy values are not approved current rules:** older product text specified four fixed squads, a 20-second planning plus 5-second resolution loop with no 5-second reward window, fixed shield/patch/sabotage values, and credits of 100 per round plus 25 per voter. Those values conflict with the current 20/5/5 target, configurable K, and unresolved bounty/reward formulas. Do not treat them as authoritative.
