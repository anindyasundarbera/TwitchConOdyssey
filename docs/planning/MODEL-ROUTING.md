# Shared planning model routing

`config/model-policy.json` explicitly maps tasks to model/provider/effort and input/output budgets.
`coordination.model_router.choose_model(task, scope="plan")` returns that decision and the SHA-256
of the exact policy bytes. Unknown tasks, disabled profiles, invalid budgets and every gameplay scope
or gameplay/chat action task fail closed. There is no fallback, escalation, network client, environment
loading or provider setup. Development is a selectable planning task; development execution scope is
not enabled. Future gameplay requires separate authorization and implementation.
Use explicit `--policy PATH` (or the Python `policy_path=` argument) for a nondefault policy;
ambient `MODEL_POLICY_PATH` is not read.

```bash
python3 -m coordination.model_router --task plan_streamer --scope plan
python3 -m coordination.plan_rehearsal prepare --plan docs/planning/gameplan-v1.json > /tmp/role-packets.json
python3 -m coordination.plan_rehearsal prepare --plan docs/planning/gameplan-v1.json --role security --role review
python3 -m coordination.plan_rehearsal aggregate --plan docs/planning/gameplan-v1.json --manifest /tmp/role-packets.json --result /tmp/streamer.json --result /tmp/viewer.json --result /tmp/character.json --result /tmp/attacker.json --result /tmp/stage_operator.json --result /tmp/security.json --result /tmp/review.json
```

Preparation creates bounded prompts for the selected roles. Optional repeated `--context PATH` adds
explicit documents and their hashes. The plan must be a JSON object. The sole product setting is San Diego;
dated location research is background only. The caller passes each packet's prompt and routing
decision to the supported Codex agent tool, including its explicit model and reasoning effort. This CLI
does not spawn agents. `infer(task, prompt, executor, scope="plan")` is the same reusable selection boundary
for an injected callback `executor(prompt=..., decision=...)`; it calls once and propagates errors. It records
prompt/output hashes. Output-token limits are passed to the executor; only the input-character budget is
enforced locally. Callback executors must enforce their supported output limit. Codex spawn tools may not
support that limit; disclose that limitation. Budgets do not measure dollar spend.

Each actual role result must contain exactly `role`, `plan_hash`, `model`, `findings`, and
`runtime_executed: false`. Each finding contains exactly `id`, `severity` (`low`, `medium`, `high`,
`critical`), `scenario`, `gap`, and `recommendation`. Findings are capped at 30 per role and 2,000 characters
per field; IDs must be unique within a role. Aggregation requires exactly one result for every selected
role and rejects stale plan/context/policy hashes, changed models, extra fields and runtime claims.
Review JSON is caller-supplied and does not independently authenticate the agent identity. Canonical
result-content hashes and expected providers accompany reviews. The report
separates scripted schema/hash checks from submitted agent reviews; neither proves gameplay behavior.
No gameplay module, server, replay, or simulation harness is imported or invoked.
The helper is an explicit routing/scope contract, not a sandbox for arbitrary callback code. Callers must
supply an appropriately restricted executor; setting a task label does not contain its side effects.

Targeted verification only:
`python3 -m unittest tests.test_model_router tests.test_plan_rehearsal -v`.

## Planned allocation

| Work | Profile | Model / effort |
| --- | --- | --- |
| Extraction, classification, routing, triage, route mapping | `economy` | `gpt-6-luna` / low |
| Scoped writing and streamer/viewer/character/stage-operator reviews | `writing` | `gpt-6.1-terra` / medium |
| Visual interpretation with explicit acceptance checks | `visual_low` or `visual_medium` | `gpt-6.1-terra` / low or medium |
| Research synthesis and adversarial plan review | `research` | `gpt-6.1-sol` / medium |
| Orchestration, complex debugging, security and development planning | `engineering` | `gpt-6.1-sol` / high |
| Hardest ambiguous end-to-end or final principal gate | `principal_review` | `gpt-6-astra` / high |

`gpt-6-sol` is retained in the catalog but receives no new work because GPT-6.1 Sol is the current Sol allocation. Astra is not a default reviewer. Escalation remains manual: two failed acceptance checks at the current tier permit exactly one step upward.

## Token-saving strategy

1. Run thousands of game actors through deterministic scripts rather than LLM agents. Agents may analyze compact results, but they are not load actors.
2. Generate reusable viewer-message corpora once, identified by RNG seed and SHA-256; do not pay to regenerate unchanged input populations.
3. Send fresh compact task packets instead of the full conversation. Include stable instructions, task-specific paths, ownership, hashes and one acceptance check.
4. Send state diffs and summaries instead of complete event histories. Detailed evidence remains in owned artifacts that agents read only when needed.
5. Use Luna for high-volume narrow work, Terra for scoped writing/visual/stakeholder work, Sol only for technical ambiguity or synthesis, and Astra once at the final gate.
6. Group compatible perspectives in one bounded agent call when independence is not an acceptance requirement.
7. Cache plan, policy and result hashes so unchanged context is not regenerated. Reuse a stable instruction prefix where supported.
8. Prohibit automatic escalation, retries and silent model fallback. Each helper invocation calls its executor once and propagates failure. Human-gated escalation follows the recorded two-failure, one-tier-at-a-time rule.
9. Reject oversized packets before inference. Current caps are 24k characters for Luna, 24k for Terra, 32k for Sol and 40k for Astra. Output caps are 1.8k, 1.8k, 2.4k and 3k tokens respectively. Character caps are locally enforced; output-token caps require executor support.

This follows official OpenAI guidance to reduce requests and tokens and choose a smaller adequate model. Batch/Flex pricing is an API option for eligible asynchronous work, not a claim that Codex-agent execution uses API Batch.
