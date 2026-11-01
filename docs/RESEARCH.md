# Necessary research · 2026-10-31

- [Harness² primary repository](https://github.com/google-research/harness2): documented task-level Propose–Probe–Compose refinement and persistent improvement evidence. Use a lightweight local evidence harness, outside game runtime. No dependency installed and no claim of benchmark performance.
- [Twitch Extensions reference](https://dev.twitch.tv/docs/extensions/reference/): onAuthorized supplies JWT identity; onContext exposes hlsLatencyBroadcaster. A production ingress must verify JWTs; video latency is variable, so the requested 20/5 windows are a design buffer, not a guarantee of synchronization.
- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs): strict JSON schema output constrains structure; local authoritative rules remain necessary. Optional adapter uses Responses text.format json_schema, strict=true; model ID is explicit environment configuration.
- Local inspection: Python 3.14.4 and Node 24.21.0 available; SQLite is bundled with Python. Runtime uses no third-party dependencies. Workspace is empty and `.git` is a read-only placeholder, so no commits or branch history are available.
