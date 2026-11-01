# OpenAI capability and durable-context evidence

Retrieved: **2026-11-01**. Research only; official pages below were searched and opened. No APIs, installations, implementations, or tests were run. Product mappings and context recommendations are proposals, not verified integration behavior. This note follows `PROJECT-CONTEXT.md`; existing README capability claims were not independently certified.

## Chat-to-Action: schemas constrain proposals

**Documented.** Function calling connects models to application tools. Explicit `strict: true` constrains generated arguments to a supported schema: every object needs `additionalProperties: false`, every property must be required, and nullable types can represent optional values. Unsupported strict schemas are rejected. Set strict explicitly: Responses can normalize schemas or fall back to best-effort mode; Chat Completions defaults differ. `parallel_tool_calls: false` permits zero or one tool call per response; it does not enforce viewer influence across turns. Fine-tuned models have an additional multiple-call strictness limitation. [Function calling](https://developers.openai.com/api/docs/guides/function-calling)

**Documented limits.** Structured Outputs supports a JSON Schema subset; unsupported constructs include `allOf`, `not`, and conditional composition. Refusals can arrive outside the requested schema, and incomplete responses require handling. Schema-valid content can still be mistaken or hallucinated for unrelated input. Function calling suits tools; structured response formatting suits user-facing structured text. Plain JSON mode guarantees less than schema adherence. [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

**Proposed game mapping.** Expose a small proposal vocabulary, including a no-action outcome, then independently validate identity, phase, eligibility, one-influence accounting, budget, cooldown, placement, physics, and idempotency. Neither schema adherence nor disabling parallel calls establishes these rules. Reject stale, incomplete, refused, invalid, or late responses without blocking simulation. The intended 20 Hz loop and latency envelope remain untested.

## Codex Hotfix Booth: documented components, custom game contract

| Interface | Documented capability | Booth use proposed |
| --- | --- | --- |
| Codex SDK | TypeScript starts/continues/resumes local threads; Python controls local app-server over JSON-RPC. | Bounded incident job outside simulation. |
| Noninteractive CLI | `codex exec --json` emits JSONL lifecycle/item events; `--output-schema` constrains the final response. | Simplest inspectable job runner and manifest proposal. |
| App-server | Custom clients manage threads, turns, approvals, and streamed items. | Rich live inspector if CLI evidence is insufficient. |

Sources: [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk), [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), [Codex App Server](https://learn.chatgpt.com/docs/app-server). The SDK page says the old `codex mcp-server` interfaces were removed; do not base a new plan on them.

**Actual evidence is obtainable.** CLI JSONL includes command executions, changes, MCP calls, messages, and completion/failure. App-server `commandExecution` items can include command, working directory, status, output, exit code, and duration; output deltas and final item events support an inspector. `command/exec` also returns stdout/stderr/exit status. A completed agent turn is not proof that required fixtures passed. Dynamic client tools are documented as experimental. App-server authentication has use-case restrictions; its documentation directs commercial/hosted use toward the separate supported sign-in path. [App-server](https://learn.chatgpt.com/docs/app-server)

**Proposed evidence contract.** Record sanitized incident input, fixture identifier/seed, patch hash, actual runner events, fixture assertions and exit status, validation result, and measured wall time. Keep replay evidence visibly labeled. A prose claim of “tests passed” is insufficient. The game must supply deterministic fixtures and a trusted validator; this research produced no such run.

**Permissions.** Codex has filesystem read/write/deny and command-network controls. Hosted search, apps/connectors, MCP, and browser/computer use have separate controls; a command-network deny is not a universal capability deny. Approvals and sandboxing address different boundaries. [Permissions](https://learn.chatgpt.com/docs/permissions), [Agent approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security)

**Proposed containment.** Restrict a Booth job to incident snapshots and candidate data/rules files in a disposable workspace, with only the required fixture runner available. Enforce permitted paths, tools, and outputs outside prompts. Independently parse and validate the DSL, then let a trusted component sign an accepted manifest. Signing keys, policy checks, rollback, game-turn activation, and exclusion of executable hot-loading are custom application behavior, not documented Codex guarantees. A Codex `turn/completed` means an agent turn ended, not that a game boundary was reached.

## Lean durable context

**Documented.** Codex loads layered `AGENTS.md` guidance before work; closer directory instructions override broader ones, with a default combined 32 KiB cap. Keep that scarce instruction space for stable constraints and navigation. [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

Subagents work in agent threads and return summaries; documentation recommends keeping noisy exploration/test output out of the main thread and warns that parallel work consumes more tokens. It recommends `gpt-6-luna` for narrow lighter tasks and `gpt-6.1-sol` for demanding, ambiguous work. A separate thread does not by itself prove that no parent history was copied: this runtime supports explicit fresh dispatch, which must be selected deliberately. [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

Skills load metadata first and full instructions when selected, illustrating progressive disclosure. [Build skills](https://learn.chatgpt.com/docs/build-skills)

**Recommended project protocol, not a built-in memory feature:**

1. Keep `AGENTS.md` short: phase authorization, invariant rules, evidence standards, file ownership, and links to current task/context files.
2. Store product intent, current plan/status, decisions, assumptions/claims, evidence, and risks as distinct Markdown sections or small linked files. Each claim carries status, source/date, and verification gap. Link logs rather than copying them into instructions.
3. Dispatch each narrow agent fresh where supported, supplying a bounded packet: objective, allowed scope, relevant context links, authoritative facts, acceptance criteria, owned output, and stop condition. Include explicit instructions to read those files; ordinary task Markdown is not automatically injected by AGENTS discovery.
4. Return a short summary with findings, exact evidence links, changed file, unresolved claims, and next action. Coordinator updates canonical status; summaries do not replace primary evidence. Resume full history only when continuity is necessary.

Start with plain Markdown and filename/text search. Add retrieval/vector indexing only after measured corpus/search failures; add MCP when an external system or reusable tool connection is needed. Neither is required for this small evidence packet. This is a project recommendation, not an OpenAI product requirement.

For model routing, start Luna on extraction/link checks and Sol on synthesis or conflicting evidence; compare identical tasks and keep the lightest setting meeting the quality bar. Official guidance describes Luna as cost-effective and Sol as balancing capability/cost; no exact prices or account entitlements are inferred. [Using GPT-6](https://developers.openai.com/api/docs/guides/latest-model), [Model selection](https://developers.openai.com/api/docs/guides/model-selection)
