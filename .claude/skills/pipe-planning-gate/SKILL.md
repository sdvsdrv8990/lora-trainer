---
name: pipe-planning-gate
description: Load before any pipeline app code change. Forces a micro-plan, scope lock, risk check, and evidence target before editing files.
---

# pipe-planning-gate

Before editing any file in the pipeline app, write a short plan:

1. **Goal** — one sentence describing the change
2. **Layer** — which layer from `docs/pipeline/ARCHITECTURE.md` is touched
3. **Files expected to change** — list them explicitly
4. **Risk area** — choose one: MCP protocol, Claude.ai connector, engine adapter, state machine, entity schema, data format, docs only
5. **Validation command** — the exact command you will run to confirm the change works

## Scope Rules

- Touch the smallest set of files that satisfies the goal.
- Do not refactor neighboring code unless the task requires it.
- Do not change entity schemas and adapter code in the same pass.
- Do not modify `state.json` handling and MCP tool signatures in the same pass.
- If the change touches an engine adapter, confirm the abstract base class is not altered.

## Risk Checklist

**MCP protocol risk:**
- Tool name must remain on the approved list in `PRODUCTION_PIPELINE.md`.
- Return shape must remain `{"ok": bool, "data": {...}}` or `{"ok": false, "error": "..."}`.
- Do not use `GET /mcp` as health or discovery evidence. It can return `400 Bad Request: Missing session ID`.
- Use JSON-RPC `initialize` via `POST /mcp`, then `tools/list`.
- Any public tool schema change must keep Claude.ai-friendly parameter descriptions and simple JSON Schema.

**Claude.ai connector risk:**
- `resource_server_url` must include `/mcp`, producing `/.well-known/oauth-protected-resource/mcp`.
- Tunnel requests arrive from `127.0.0.1`; use the public Host header to distinguish Cloudflare from direct localhost.
- Direct localhost should not expose OAuth discovery to Claude Code.
- Public tunnel Host must expose OAuth discovery to Claude.ai.
- After auth, tunnel, or schema changes, remove and re-add the Claude.ai custom integration before judging the UI state.

**State machine risk:**
- Only Claude may advance `current_step` in `state.json`.
- `state.json` must be written before any tool returns — even on error.

**Engine adapter risk:**
- Adapter changes must not touch `engine.py` (abstract base class).
- Engine selection must remain driven by `engines.yaml` only.

**Entity schema risk:**
- Field renames break JSON contracts with Claude and between modules.
- Add fields; never remove or rename without updating all consumers and `PRODUCTION_PIPELINE.md`.

## Evidence Rules

- MCP tool changes → run the official MCP Python SDK `initialize -> tools/list`, then run the changed tool with a test project and confirm the JSON response shape.
- Claude.ai connector changes → verify `/.well-known/oauth-protected-resource/mcp`, `/.well-known/oauth-authorization-server`, and SDK `initialize -> tools/list`.
- TTS adapter changes → generate one audio file and confirm it exists on disk.
- Audio analyzer changes → confirm `timing_report.json` is written with correct fields.
- Image engine changes → generate one image and confirm it appears in `images/`.
- FFmpeg assembly changes → run against a 2-scene test project and confirm draft render exists.
- Entity schema changes → run `pytest tests/unit/entities/` and confirm no validation errors.

## Known-Good MCP Verification Snippet

Use the project's `pipeline/venv` and a running server. Replace the URL/Host when
testing the real tunnel.

```bash
cd pipeline
venv/bin/python -c "exec('import anyio\nfrom mcp import ClientSession\nfrom mcp.client.streamable_http import streamablehttp_client\nasync def main():\n    async with streamablehttp_client(\"http://127.0.0.1:8765/mcp\", headers={\"Host\": \"localhost:8765\"}) as (read, write, _):\n        async with ClientSession(read, write) as session:\n            await session.initialize()\n            result = await session.list_tools()\n            print(\"count\", len(result.tools))\n            for tool in result.tools:\n                print(tool.name)\nanyio.run(main)')"
```

Expected current count: `95`.
