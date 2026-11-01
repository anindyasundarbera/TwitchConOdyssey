# Model configuration evidence

Retrieved 2026-11-01. Research used only official OpenAI documentation: searched the GPT-6/GPT-6.1 pricing/catalog topic, then opened the requested [pricing](https://platform.openai.com/docs/pricing) and [models](https://platform.openai.com/docs/models) pages. They redirect to [current pricing](https://developers.openai.com/api/docs/pricing) and [current model catalog](https://developers.openai.com/api/docs/models).

## 1. GPT-6 and GPT-6.1 text models

All five GPT-6/GPT-6.1 entries on the current All models page, sorted by Standard input price. Four appear in the flagship section; GPT-6 Sol appears under More models and points to GPT-6.1 Sol as its newer version, but is not labeled deprecated. Prices are USD per million text tokens, uncached input, Standard short context (at most 272,000 input tokens). These API prices do not measure Codex subscription usage or establish account access.

| Model / exact API ID | Standard input | Standard output | Batch input | Batch output | API context tokens | Supported reasoning efforts | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) / `gpt-6-luna` | $0.10 | $0.50 | $0.05 | $0.25 | 1,050,000 | none, low, medium, high, xhigh, max | Current flagship; no preview/deprecation label |
| [GPT-6.1 Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra) / `gpt-6.1-terra` | $1.00 | $5.00 | $0.50 | $2.50 | 1,050,000 | none, low, medium, high, xhigh, max | Current flagship; no preview/deprecation label |
| [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol) / `gpt-6-sol` | $2.00 | $10.00 | $1.00 | $5.00 | 1,050,000 | none, low, medium, high, xhigh, max | Current; newer version available; no deprecation label |
| [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol) / `gpt-6.1-sol` | $2.00 | $10.00 | $1.00 | $5.00 | 1,050,000 | low, medium, high, xhigh, max | Current flagship; no preview/deprecation label |
| [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) / `gpt-6-astra` | $10.00 | $50.00 | $5.00 | $25.00 | 1,050,000 | low, medium, high, xhigh, max | Current flagship; no preview/deprecation label |

Each linked model page states 128,000 maximum output tokens and explicitly says Batch/Flex costs 50% of Standard. Status reports the observed catalog/deprecation labeling, not a claim of account availability.

**Pricing display resolution:** the extracted pricing page flattens the Standard, Flex/Batch, Fast and Ultrafast tabs into consecutive tables. The first flagship table is Standard; the second has half those prices and belongs to Flex/Batch. Each model's dedicated page independently confirms its Standard price and 50% Batch reduction. The cheaper second table is therefore not the Standard rate. Prompts above 272,000 input tokens cost 2× input/cache and 1.5× output for the full request; those long-context rates are excluded here. Cache, regional and speed-tier adjustments are excluded.

## 2. User-directed mapping and escalation

| Subagent responsibility | Model | Reasoning effort |
| --- | --- | --- |
| Planner / orchestrator | `gpt-6.1-sol` | high |
| Complex coding / debugging | `gpt-6.1-sol` | high |
| Research synthesis / long-doc | `gpt-6.1-sol` | medium |
| Everyday writing / summarization | `gpt-6.1-terra` | medium |
| Visual interpretation / forms | `gpt-6.1-terra` | low/medium |
| Extraction / classification | `gpt-6-luna` | low |
| Routing / triage / batch | `gpt-6-luna` | low |
| Hardest end-to-end / ambiguous | `gpt-6-astra` | high |

Exact stored rule: `Luna→Terra→Sol→Astra, max 2 retries per tier`.

Operational interpretation follows the user's failed-acceptance-check condition: after two failed acceptance checks at the current tier, move exactly one tier upward; never skip a tier. Start at the mapped model. Stop after two failures at Astra. This is a recorded policy, not automatic escalation execution. `low/medium` preserves the user's visual-task preference as text; an actual inference request must select one supported effort, `low` or `medium`, before execution.

## 3. Existing configuration update

After steps 1–2, codebase-memory discovery located `coordination/model_router.py`; its `DEFAULT_POLICY` selects `config/model-policy.json`. The file was read before editing and extended using its existing JSON conventions. No second routing configuration was created. The catalog, user mapping, literal escalation rule and ISO-8601 timestamp are stored there using the requested model and role field names; existing task budgets and provider identities remain. Added generic task aliases make the mapping available through existing profiles, including Terra. Executable visual task aliases select `low` or `medium` explicitly.

Plan-only scope, disabled gameplay, disabled GPT-4o/OSS and `automatic_escalation: false` remain. No provider setup, inference, critique, gameplay, retry loop or automatic phase transition was run. Catalog research and read-only validation are the evidence produced here.

Validation observed: a Python standard-library check parsed the JSON and passed assertions for the exact requested object keys, five price-sorted catalog IDs, all eight role mappings and the literal escalation string. The five focused model-router unit tests also passed. No gameplay modules were imported or run.
