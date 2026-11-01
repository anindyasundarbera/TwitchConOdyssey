# Durable instructions and bounded context

Researched 2026-11-01. Research only; this note grants no implementation or gameplay authorization.

## Scope and evidence quality

Searched official OpenAI documentation with variants of “Codex AGENTS.md discovery size precedence,” “subagents context reasoning,” “memories,” and “phase build log.” Reviewed current English documentation without publication-date restrictions. Excluded third-party accounts, unopened search snippets and API behavior as proof of local-client behavior. Product documentation below is primary evidence of documented behavior, not an independent reliability study. The cookbook is lower-weight workflow guidance. No project-specific retention benchmark was found or run.

## Documented behavior

**Evidence — instruction discovery.** Codex builds its instruction chain once per run/session: global guidance first, then project-root-to-working-directory guidance. Per directory, discovery prefers `AGENTS.override.md`, then `AGENTS.md`, then configured fallback names; it includes at most one file. Later, deeper guidance overrides earlier guidance. The combined project guidance cap defaults to 32 KiB through `project_doc_max_bytes`; empty files are skipped. Nested files do not remove the combined cap. [AGENTS.md documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

**Evidence — verification.** OpenAI recommends asking a fresh session to summarize its instructions and list active instruction files, repeating from a subdirectory to inspect overrides. Opt-in TUI/session logs can audit loaded sources. Restart after instruction-file changes to rebuild discovery. These checks inspect loading and interpretation; they do not prove perfect future compliance. [Verification guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md#verify-your-setup)

**Evidence — subagents and settings.** Subagents move noisy exploration out of the main thread and return summaries, but comparable multi-agent runs consume more tokens. Without configured model/effort, they inherit the parent settings. Explicit model selection without effort can select that model’s default effort. Custom agent files can override resolved settings, so specify both `model` and `model_reasoning_effort` when exact routing matters. More effort generally increases latency and token usage. [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) The Responses API separately documents bounded subagent contexts and warns that delegation can increase usage; this is supporting API evidence, not proof of every local-client transport detail. [Responses multi-agent](https://developers.openai.com/api/docs/guides/responses-multi-agent)

**Evidence — skills and memories.** Skills initially expose metadata; full instructions load when selected. They suit reusable procedures without putting every procedure into every prompt. [Build skills](https://learn.chatgpt.com/docs/build-skills) Local Codex memories are separate from ChatGPT memory, optional, generated asynchronously and potentially delayed or skipped. OpenAI explicitly places mandatory team guidance in `AGENTS.md` or checked-in documentation rather than relying solely on memory. [Memories](https://learn.chatgpt.com/docs/customization/memories)

**Evidence — phase records.** OpenAI’s cookbook proposes optional separate files for phase scope/acceptance, material context/decisions and observed build progress. It distinguishes plans from execution evidence. This is a recommended convention, not automatic discovery or an enforced phase gate. [Development workflows cookbook](https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex)

## Minimal project design

**Recommendation — preserve exact directives once.** Add a small checked-in directive ledger in a separately authorized change. Each entry should hold an ID, exact user wording, source turn/date when available, scope, active/superseded status and explicit superseding directive. Mark unavailable original wording as unavailable; never reconstruct a quotation from a summary. Hashing binds bytes, not authenticity or authorization.

**Recommendation — keep the entry point small.** Keep only durable rules, the current hard phase gate and mandatory read paths in root `AGENTS.md`. Link the ledger and retain the existing `STATUS.md`, `CONTEXT-v2.md`, `GAMEPLAN-v2.md` entry points. Do not duplicate full transcripts, historical research or frozen rehearsal artifacts there. Relevant ledger entries must actually be read; a path alone does not load its content.

**Recommendation — separate changeable state.** Let STATUS own current authorization/status, compact context own current decisions/open questions, and an observed build log own commands, results and artifact bindings. Archive obsolete context while preserving frozen v1 evidence. These records describe authorization; only explicit user directives change the gameplay gate.

**Recommendation — bounded handoff and preflight.** Start each session by reading the entry points and relevant exact directives. Report active IDs, phase boundary, relevant file hashes and unresolved conflicts before dependent work. Route each task with the existing helper; bind its provider/model/effort and policy hash to the actual executor settings. Give delegated work owned paths, acceptance criteria and short returns, loading other context on demand. Verify instruction discovery after changes. Neither retained chat, memory, a successful routing decision nor an agent’s self-report guarantees exact obedience; preserve reviewable source records and observed evidence.
