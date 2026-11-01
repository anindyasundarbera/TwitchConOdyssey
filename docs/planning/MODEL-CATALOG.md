# Model selection evidence and current execution path

Checked 2026-11-01 using the [requested official catalog](https://developers.openai.com/api/docs/models/all). This is a focused task shortlist, not a copy of the full catalog or proof of API/account access. The executable mapping is `config/model-policy.json`.

| Model/profile | Documented position | Current project use/status |
| --- | --- | --- |
| `gpt-6-luna` / economy | Efficient focused/high-volume model. [Model page](https://developers.openai.com/api/docs/models/gpt-6-luna) | Extraction, classification, routing, triage and route mapping. |
| `gpt-6.1-terra` / writing and visual | Fast, efficient visual reasoning and clear writing. [Model page](https://developers.openai.com/api/docs/models/gpt-6.1-terra) | Scoped writing, visual work and stakeholder plan review. |
| `gpt-6-sol` / catalog only | Previous Sol generation; the model page points to GPT-6.1 Sol as newer. [Model page](https://developers.openai.com/api/docs/models/gpt-6-sol) | No new project allocation. |
| `gpt-6.1-sol` / engineering | Complex work at lower cost than Astra. [Catalog](https://developers.openai.com/api/docs/models/all) | Shared helper implementation, technical synthesis and security review. |
| `gpt-6-astra` / principal_review | Most demanding reasoning work. [Model page](https://developers.openai.com/api/docs/models/gpt-6-astra) | User-requested independent principal review, bounded to the plan. |
| `gpt-4o` / legacy_4o | Marked deprecated; documentation lists structured output support. [Model page](https://developers.openai.com/api/docs/models/gpt-4o) | Retained explicitly as a disabled option. No account access or credentialed execution verified. |
| `gpt-oss-20b` / local_oss | Open-weight model for local/specialized use. [Model page](https://developers.openai.com/api/docs/models/gpt-oss-20b) | Disabled until a compatible inference endpoint is configured and tested. Catalog listing does not provision a local model or hosted API. |

## Availability and budgets

The current Codex agent surface offers GPT-6 Luna, GPT-6 Sol, GPT-6.1 Terra, GPT-6.1 Sol and GPT-6 Astra. It does not offer GPT-4o or gpt-oss as spawn models. Earlier environment checks found no configured execution path for those disabled alternatives; no model was downloaded and no paid API request was made.

The user's alternative "any other lower models" authorizes Luna for this bounded plan exercise. This is an explicit choice, not an undisclosed claim that GPT-4o/gpt-oss ran. API access, Codex access, open-weight hosting, and scripted checks are separate execution surfaces.

Context/output caps in the policy bound packet construction and supplied executors are Luna 24k characters/1.8k output tokens, Terra 24k/1.8k, Sol 32k/2.4k and Astra 40k/3k. The Codex spawn tool has no hard output-token field; role instructions request concise responses, but the policy cannot certify tool-level billing or enforce an external agent's internal token count. No dollar-spend claim is made. Larger models are selected only for designated tasks; no automatic escalation, retry or silent fallback is authorized.

The helper must return the chosen task/profile/model/provider/effort, budget and policy hash before inference. Actual inference requires an explicit executor; tests may use a mock callback only when clearly labeled. Plan review reports must preserve their origin rather than treating generated commentary as a physics, network, fairness or load test.
