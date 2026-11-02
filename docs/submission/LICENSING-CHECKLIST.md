# Licensing, trademark and audio checklist

Status: **incomplete**. This is an honest checklist, not legal advice or a
clearance claim. No repository `LICENSE` file exists in this tree.

| Item | Status | Required action / evidence |
| --- | --- | --- |
| Repository source license | **Missing** | Owner must select a license, add `LICENSE`, and bind its hash in the readiness record. Do not infer a license from the public Devpost rules. |
| Third-party Python runtime dependencies | Clear | `pyproject.toml` declares no runtime dependencies; the app uses the standard library. |
| Third-party JavaScript runtime dependencies | Clear | The client is plain HTML/CSS/JS; Node is used only for optional tests. |
| Web fonts, icon packs, stock images | Clear | No external font/image assets are referenced. The page uses a system font stack and canvas-drawn art. |
| Audio files | Clear | All demo audio is synthesized at runtime with the Web Audio API; no audio file is committed. |
| Twitch name, marks and chat content | Nominative use only | Refer to Twitch factually. Do not use official Twitch logos or imply endorsement. Raw chat is never packaged; only hashes/metadata are retained. |
| OpenAI / Codex name and marks | Nominative use only | Refer to the recorded Codex session factually. Do not use OpenAI/Codex logos or imply endorsement. |
| San Diego place names | Factual place references | Little Italy, North Embarcadero, Gaslamp Quarter and the convention center are real places. The main stage and game events are fictional. |
| Fictional Hype / credits | Clear | In-game Hype and credits are fictional and have no monetary value or transfer. |
| Final video footage | **Missing** | The final under-180-second video does not exist. It must show observed live Twitch operation plus sanitized Codex evidence; no fixture footage may be presented as live. |
| Final video audio | **Not cleared** | Use only synthesized or owned audio. A track with unknown provenance must not be used. |
| Devpost rules and platform terms | **Unverified** | Re-check the current Devpost rules and Twitch/YouTube terms before submission. The demo must remain accessible and under three minutes; unlisted is acceptable, private is not. |
| Dataset / user data | Clear for the current tree | No dataset, raw chat log, token or unhashed handle is packaged. A future live run must retain only consented, sanitized evidence. |
| Contributor / asset provenance | **Incomplete** | Record the provenance of every new asset added after this checklist. |

## Stop conditions

Do not publish, upload or submit while any row above is missing or unverified.
`submission_ready` remains `false` until the licensing and audio predicates are
evidenced and the independent review returns READY.
