# Build-readiness gap register — 2026-11-02

Source of truth for predicates: `python3 -m tools.verify_submission_readiness`
(offline). Baseline at 22:57 +0530: **30 / 83 predicates pass**,
`submission_ready: false`, HEAD `bb02cea7e1c260eb30ea9491e7759761c0f290d4`
(dirty worktree, user-owned).

Requester instruction: "Activate swarms and have them close the gaps and fix the blockers".

## Swarm routing note

Configured route for these tasks is `codex_subagent / gpt-6.1-sol / high`. That
route is not available in this harness; workers run on the coordinator's
inherited model. This is a recorded substitution, not attested routing.

## A. Locally closable (done this session)

| Gap | Owner | Status | Evidence |
|---|---|---|---|
| Stale closed-gate text in `STATUS.md` | Coordinator | Done — append-only note, ledger hash rebound, compiler valid | `docs/planning/STATUS.md`, `config/directive-policy.json` |
| Mislabelled "Astra" review provenance | Coordinator | Done — correction header; review is agent opinion only | `docs/planning/GAME-INTERFACE-ASTRA-REVIEW.md` |
| Modal focus trap / focus restore / no steering behind modals | Worker A | Done — focus trap, tab navigation, inert background | `client/app.js` (lines 40-164, 709-739) |
| Canvas honours `prefers-reduced-motion` | Worker A | Done — disables free-scroll, strobe, runner stride, spark pulse | `client/app.js` (lines 27-38, 343, 443, 488, 497) |
| `hygiene.secret_scan_passed` | Worker B | Done — 1,453 files scanned; zero live secrets | `evidence/build-readiness/20261102/BUILD-READINESS.json` |
| Clean checkout & package verification | Worker B | Done — 55 package artifacts verified (0 pending), 57 test suite passed | `evidence/build-readiness/20261102/README.md` |
| `hygiene.cleanup_performed` | Worker B / Coordinator | Done — candidate scan and offline verification confirmed | `evidence/build-readiness/20261102/BUILD-READINESS.json` |

## B. Needs a user decision (local, no external effect)

| Gap | Why it needs you |
|---|---|
| `candidate.final_head`, `candidate.tracked_diff_sha256` | Freezing requires either a local commit of the dirty (user-owned) worktree or binding the diff hash against `bb02cea`. Untracked files are not covered by `git diff`, so a local commit is the honest freeze. Not done without your OK. |
| `project.audio_licensed` | Depends on the final video's audio. |

## C. Blocked — requires credentials, live services or publication

| Gap | Blocker |
|---|---|
| `live.*` (token validation, EventSub `channel.chat.message`, canonical command applied) | Needs your Twitch credentials and live calls; live calls are forbidden under ledger rev 16 for this scope. |
| `captures.desktop/mobile` with origin `live` | Depends on live session. |
| `video.*` (<180 s, YouTube public/unlisted) | Needs recording + YouTube upload (publication not authorized). |
| `repository.*` (judge-accessible URL, observed accessible) | Needs repository push (not authorized). |
| `review.*` (attested gpt-6-astra READY on frozen candidate) | Needs a frozen candidate and an attested Astra route, which this harness cannot provide. |
