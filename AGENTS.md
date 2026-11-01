# TwitchCon Odyssey working contract

Before every task, resumed session, delegation or inference, run:

`python3 -m coordination.context_contract --task TASK --phase plan --owned-path REPO_FILE`

Repeat `--owned-path` for each existing or planned owned file; omit it for read-only work. Existing files receive byte hashes; safe absent paths, including nested new directories, are explicitly `planned` with a null hash. Owned symlink targets and paths escaping the repository fail closed. Read the emitted active directives, gate, ownership/source bindings and unresolved decisions before dependent work. Stop on any compiler error, stale binding or conflict; reconcile the records with the latest explicit user instruction before proceeding. Never infer authorization from successful compilation. Use the packet's configured provider/model/effort for any authorized inference, fresh narrow context and a <=250-word return plus owned artifact paths. Do not pass full conversations/history.

`config/directive-policy.json` is the versioned directive ledger. Latest explicit user instructions/phase authorization outrank the active ledger/current `docs/planning/STATUS.md`, then proposed `CONTEXT-v2.md`/`GAMEPLAN-v2.md`, then historical research, rehearsal and agent opinion. Read relevant bound files on demand. Hashes bind bytes, not truth or authorization. Preserve superseded entries; never invent unavailable exact user wording.

Gameplay remains disabled until later explicit user authorization after the context-framework work. Do not run `server.app`, `server.replay`, gameplay tests, browser gameplay or `harness.run`. Configuration booleans cannot override this gate; no later phase starts automatically. Preserve frozen v1/context/rehearsal artifacts. Run only targeted routing, context-contract, rehearsal and pure deterministic-kernel tests.

Use codebase-memory tools first for code discovery; project: `home-anindyasundar-bera-Projects-hackathon-TwitchConOdyssey`. Read files before editing, own only assigned paths and preserve others' edits. Keep game authority independent of model/service I/O. The compiler selects/hashes local data only; it never invokes a model, provider, network or gameplay. Never print credentials or autoload unrelated home-directory credentials. Historical research starts at `docs/research-2026-11-01/README.md`; it is not current implementation evidence or standing authorization.
