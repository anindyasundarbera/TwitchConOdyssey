# S1 independent planning review

**Verdict: REVISE**

Recorded 2026-11-01; review revision 1. Scope: document coherence for a later bounded deterministic simulation. This is an independent planning critique, not gameplay validation, implementation evidence or authorization. No gameplay, runtime, live-service or external browsing work was performed.

Reviewed [selected profile](S1-SIMULATION-PROFILE.md), [plan revision 3](GAMEPLAN-v2.md), [plan data](gameplan-v2.json), [platform evidence](research/S1-PLATFORM-EVIDENCE.md), [systems evidence](research/S1-SYSTEMS-EVIDENCE.md) and [directive ledger revision 6](../../config/directive-policy.json). Source versions are bound by context-contract packet `d33eca606639dd55297ab937e365d497e1982f642d0b75a386c0dd2fe938a85d`; profile SHA-256 `d5216ff1c73f08153003f38077f67c59813b52b05e27d1a89a937c0636117266`. Later edits require fresh review; this verdict does not transfer automatically.

## Critical findings

1. **D-05 lacks a complete deterministic timeline.** Approximately five seconds of reward is a presentation target, not an exact transition rule. Specify authoritative reward boundaries, movement/steering during reward, and behavior after the third turn if the deadline has not arrived. Distinguish reward display from the single delivery settlement. The 90-second cap and three-turn maximum are compatible, but do not resolve these choices.
2. **D-05 ordering is partial.** Pause/deadline/phase-close share a priority group without an internal tie rule. Effects/settlement likewise does not explicitly settle collision versus delivery at the same pre-deadline logical time; that can change the collision-halved award. Define these orders or explicitly exclude such admitted states. Preserve the selected strict deadline, half-open receipt cutoff and counter-before-collision rule. Pause cannot make a reached deadline disappear.
3. **D-02 warning and hazard admission need one consistent contract.** The final five seconds of planning promise a warning, while planning/model admission continues until cutoff. State whether the fixed center-lane warning is unconditional/conditional before a hazard is accepted, or specify when the warned hazard becomes committed and how later proposals are handled. Do not silently shorten the warning, backdate acceptance, roll late work forward or add an unselected cutoff. Bind accepted hazard identity to its warning and bounty increment.

These are missing selections, not requests to change existing numerical values. D-01 through D-05 are consistently marked selected/unverified, but that status alone does not close these outcome-relevant ambiguities.

## Non-blocking risks and preserved boundaries

- Steering explicitly remains active during resolution. Bounded, nonstacking slowdown and zero control loss support recovery; actual avoidance and deadline headroom still depend on geometry and admitted states.
- Below the selected frozen-roster participation threshold, the counter cannot pass; departed accounts remain in that turn's denominator. This is coherent abstention, not evidence of successful audience agency. Safety must hold without a counter.
- First-valid-receipt wins prevents replacement and bounds account influence; it does not equalize transport or model-processing latency. Authentication proves neither unique humans nor absence of account automation. Display squads add no electoral assurance.
- Safe-danger farming remains possible. Collision halving creates a shared loss and no further Hype penalty after the first collision; it may encourage blame or deliberate reward denial. Equal shares remain vulnerable to multiple-account participation. These are simulation questions, not proven exploits or grief resistance.
- Current selections separate evidence from design inference and retain the gameplay gate. Earlier research candidate wording is superseded; its unselected traversal target and activation interval must not become defaults. Bot/fixture exclusion is a required provenance rule, not demonstrated bot detection.

## Prerequisites for later simulation

- Resolve the critical findings in the profile and synchronized plan/ledger records, preserving superseded history and obtaining fresh version-bound review.
- Specify route/lane and collision geometry, free speed, initial state, finish detection, transition interpolation and admission while already transitioning, lane edges and same-tick inputs. Establish safe avoidance from every admitted hazard state and completion headroom against the selected cumulative slowdown bound.
- Define the canonical receipt/admission point for raw chat, model proposals and buttons; quota interaction between hazard proposals and counter votes; rejected-input handling; and trusted origin tags. Fixtures must remain explicitly synthetic, with no participant minting or human-assurance claim.
- Prepare deterministic expected outcomes for low/empty rosters, threshold edges, reconnects, cross-channel races, duplicate hazards, exact rational settlement, no eligible audience, cumulative harm, coincident boundaries, pause/resume, late models and replay. Use scripted actors and bound seeds/data; do not execute them under this review.
- Obtain separate explicit bounded gameplay-simulation authorization. Failover, hotfix and submission gates remain separate. A future READY verdict would mean sufficient coherence to simulate, never validated gameplay.

## Changelog

- Revision 1: initial independent review of the selected S1 profile; no design values changed.
