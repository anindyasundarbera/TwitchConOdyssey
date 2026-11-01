# 00_CONTEXT — Deterministic Kernel Remediation and Evidence Re-Seal Context

## 1. Authoritative Intent & Request Binding

- **Profile:** Contract-Driven Autonomous Delivery Protocol v2.0 × Forensic Reconstruction Discipline
- **Requester Instruction (Normalized Authoritative Intent):**
  "The blocker needs a shared deterministic implementation, so the game engine and simulator cannot drift on clock boundaries. Put the rules in a pure module with no I/O, then have both consumers call the same functions. Fix deadline ordering, warning boundaries, and invariant evidence. Add focused boundary and negative tests first. Regenerate evidence only after checks pass. Keep the sealed run `full-game-20261101T174648Z-2647e033` sealed as `REVISE`. Under a fresh context packet and a new exclusive run root, generate a new bundle, verify source bindings and replays, then request the configured Astra/high review. Readiness stays false unless the new evidence passes and review returns `READY`."
- **Precedence Hierarchy:**
  1. Latest explicit user instruction and phase authorization
  2. Active directive ledger (`config/directive-policy.json`) and current `docs/planning/STATUS.md`
  3. Current proposed plan and context (`CONTEXT-v2.md`, `GAMEPLAN-v2.md`)
  4. Historical research, rehearsal, and agent opinion

---

## 2. Baseline & Working Tree State

- **Baseline Commit SHA:** `0557baadd468b1a0405477d058662c91965542b0`
- **Baseline Commit Tag:** `plan-baseline/remediation-v2.1-pre-construction`
- **Branch:** `main`
- **Git Identity:** Anindyasundar Bera <anindyasundarbera@gmail.com>
- **Directive Ledger Revision:** 9 (`config/directive-policy.json`)
- **Context Packet Hash (Validated):** `c488fda422dc6c659e249691091f4659a571ee59fb7eee51a9765cc81fb5b21b`
- **Working Tree State at Baseline:** Clean across tracked paths; historical simulation runs remain in `artifacts/simulations/full-game/` as untracked preserved directories.

---

## 3. Preserved Historical Record (Before-Manifest)

All prior runs are immutable. In particular, `full-game-20261101T174648Z-2647e033` remains sealed as `REVISE`:

| Run ID | File Count | Aggregate Tree SHA-256 | Review / Status |
|---|---|---|---|
| `full-game-20261101T102226Z-a8e33043` | 116 | `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d` | `REJECT READY` |
| `full-game-20261101T132816Z-2647e033` | 164 | `7b52636fc394a69553ecc615bfd4e623a8cc873d924e9b621cda948b79768e8f` | `READY` (superseded by audit) |
| `full-game-20261101T161936Z-2647e033` | 158 | `0cfc45005e6ed170e49b34cc91e5622bd2e66afe4b646d4138e078e0fd1625bf` | `AUDIT REVISE` |
| `full-game-20261101T164026Z-2647e033` | 157 | `6c4b87f1dc848858f0fd4b1f5482160365f183e1586456d542d37b4b89486448` | `ABORTED` |
| `full-game-20261101T164201Z-2647e033` | 164 | `9c6670af87c8ca711da67b7d3122dde5ba9b25cec5c3894732a4b4792dd3c830` | `REVISE` |
| `full-game-20261101T174648Z-2647e033` | 170 | `b79455d3eb63ae80002750f7ad673935cfb6249094f60935bb7e31892a7ccaa5` | `REVISE` (Sealed) |

### Sealed Run Detail (`full-game-20261101T174648Z-2647e033`)
- **Run Directory:** `artifacts/simulations/full-game/full-game-20261101T174648Z-2647e033/`
- **Total Files:** 170
- **Tree SHA-256:** `b79455d3eb63ae80002750f7ad673935cfb6249094f60935bb7e31892a7ccaa5`
- **Manifest SHA-256:** `4b92fd767304bdcc7faa1553c005d78f3607eab874200fa978996bad8038ee04`
- **Review Artifact (`INDEPENDENT-REVIEW.md`) SHA-256:** `937dd798395976881dcd30a38c5c3719fa4429e0e82c09f1ab18aabd2dd6e6fa`
- **Remediation Result Document (`docs/planning/SIMULATION-REMEDIATION-RESULT-full-game-20261101T174648Z-2647e033.md`) SHA-256:** `cba323eaf09aa8d6d55c6d300a0ebfd0425fbd3c10c9b9f571e802ca5beea914`
- **Stored Snapshot Manifest:** `/tmp/sealed_run_manifest_before.json`

---

## 4. Key Architectural Decisions

| ID | Topic | Value | Evidence / Rationale | Status |
|---|---|---|---|---|
| D-01 | Shared deterministic kernel module location | `coordination/deterministic_kernel.py` | Located alongside existing deterministic primitives (`canonical_commands.py`, `content_cache.py`, `scenario_inputs.py`, `state_transport.py`); pure, no I/O, no model/service dependencies. | ACCEPTED |
| D-02 | Commit strategy | One scoped forward-only commit per RWU | Follows protocol §5.1 / §5.2. Each RWU has clear preconditions, write scope, verification, and confidence labels. | ACCEPTED |
| D-03 | New run root | `artifacts/simulations/full-game/full-game-<timestamp>-<hash>/` | Follows repository evidence convention; unique exclusive root; does not touch previous runs. | ACCEPTED |
| D-04 | Review channel | Configured `codex_subagent/gpt-6-astra` at `high` effort via `coordination.review_boundary` | Conforms to project model policy and governance instructions. | ACCEPTED |
| D-05 | Readiness gate | Passing evidence + `READY` review verdict | Readiness is false unless all property checks pass and review returns `READY`. Submission is a separate unexecuted plan. | ACCEPTED |
| D-06 | Baseline Git state | Commit `0557baadd468b1a0405477d058662c91965542b0` | Sealed prior project work under tag `plan-baseline/remediation-v2.1-pre-construction`. | ACCEPTED |
