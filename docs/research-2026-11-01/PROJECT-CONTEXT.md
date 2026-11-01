# TwitchCon Odyssey — shared research context

Date: 2026-11-01. Scope: evidence and fact-checking, plus lightweight context storage. No game implementation, tests, deployments, external messages, credential access, or architecture certification. The user explicitly authorized web research, subagents, and cheaper model choices in this turn. The previous kickoff was planning-only; its product constraints remain the baseline.

## Product intent — supplied by the user, not implementation evidence

A stream-first action game follows a streamer racing through stylized San Diego (Little Italy/North Embarcadero, the waterfront/Marina, Gaslamp Quarter, and the San Diego Convention Center) to deliver a game build to a fictional Main Stage before a deadline. Thesis: "The enemy is not chat or AI. The enemy is unstructured scale." The compressed game route is not a surveyed convention floor plan.

Turns: 20 seconds planning with continuous movement; 5 seconds input-locked resolution; about 5 seconds reward. Viewers use one-click Extension buttons or short chat triggers; natural-language messages can propose actions. Each eligible viewer has at most one unit of influence per turn. N viewers feed K configurable rival squads, with bounded cohort weighting, visible bot backfill and defensive balancing. Bots cannot impersonate humans or create farmable bounty. Hard limits prevent stun-lock, unavoidable death, permanent control loss, or unbounded damage. Human-created danger increases a collective bounty; survival rewards streamer and audience, wipes reduce/withhold reward. Formulas unresolved.

OpenAI Chat-to-Action is intended to propose schema-constrained commands. Authoritative engine validates phase, policy, budget, cooldown, placement, physics and idempotency; no waiting for models in the game loop. Codex Live Hotfix Booth is intended to diagnose bounded incidents, propose data/rules-DSL patches, run deterministic fixtures, and produce validated manifests for boundary activation. No executable code hot-loading. Actual supported products/interfaces and feasibility are research questions, not established facts.

Booth concepts: Twitch Moderation Forcefield converts fictional spam obstacles into Hype, without punishing real users; Codex booth converts validated glitches into recovery; AWS/Amazon IVS Scale Boost turns fictional congestion into a speed lane. Sponsor status, brand rights and capability wording require sources.

Offline requirement: --offline-fixture; canonical commands shared by live/fixture drivers, deterministic seeds/time, safe boundary failover, uninterrupted render/simulation, explicit replay label, synthetic/sanitized data, health/state comparison before live recovery.

Public demo <=3 minutes. Bullet-time shows actual sanitized message, recorded tool call, measured latency, validation and execution. Intended authoritative loop: 20 Hz, unverified. Distinguish API routing, Codex work, engine validation, fixture replay. Original/licensed adaptive audio. Promotional claims to check: November 2 submission, November 15 TwitchCon San Diego showcase, top five at Codex Booth stage.

## Development contract

Phases 0 charter; 1 evidence (current); 2 repository/architecture; 3 offline slice; 4 audience; 5 OpenAI/Codex; 6 booths/route; 7 resilience; 8 polish; 9 submission. Separate explicit authorization for each phase. No unapproved features. Preserve goals/plans/decisions/assumptions/claims/evidence/progress/risks separately. Fixtures and documentation do not prove live integration.

## Research work rules

Use official primary sources, open the supporting pages, cite exact URLs and retrieval date, record conflicts/gaps. Separate documented capability from proposed game mapping and untested feasibility. Do not copy long passages; respect each web source's word limit. Do not inspect source code. Read applicable AGENTS.md before writing. Other agents share the workspace: edit only your assigned new research file; never revert others' changes. Return <=250 words to the coordinator, with file path and decisive findings. Do not spawn further agents.
