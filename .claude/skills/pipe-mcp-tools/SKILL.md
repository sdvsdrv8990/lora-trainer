---
name: pipe-mcp-tools
description: Load when writing or modifying MCP server tools in src/mcp/server.py. Defines tool naming conventions, response shapes, gate protocol, and error handling rules.
---

# pipe-mcp-tools

## Current Approved Tool List

These are the tools the current working server exposes. Names are fixed — do not rename
without a coordinated migration in code, docs, and Claude.ai connector verification.

| Tool | Step | What it does |
|---|---|---|
| `pipeline_check_project` | 0 | Check if project/sub-project directories exist |
| `pipeline_create_project` | 1 | Create project + sub-project directory tree |
| `pipeline_delete_project` | 0/1 | Delete a scenario workspace and clean up an empty channel |
| `pipeline_get_state` | any | Return current `state.json` |
| `pipeline_set_state` | any | Update `state.json` — Claude uses this to advance steps |
| `pipeline_read_file` | any | Read a relative file inside the scenario workspace |
| `pipeline_write_file` | any | Write a relative file inside the scenario workspace |
| `pipeline_list_files` | any | List entries inside the scenario workspace |
| `pipeline_save_project_config` | 1.5 | Save `project_config.json` (agreed by Claude and user) |
| `pipeline_get_project_config` | any | Return saved `project_config.json` |
| `pipeline_submit_scenario` | 2 | Accept structured `tts_input` JSON array and write `md/tts_input.json` |
| `pipeline_start_voiceover` | 2 | Start voiceover generation from `md/tts_input.json` |
| `pipeline_get_voiceover_status` | 2 | Return scenario/voiceover status for controlled workflow |
| `pipeline_stop_voiceover` | 2 | Request cancellation of a running voiceover job |
| `pipeline_build_timeline` | 3 | Measure audio durations with ffprobe, write `md/timeline.json` |
| `pipeline_get_timeline` | 3 | Return full `md/timeline.json` for visual track planning |
| `pipeline_transcribe_scenes` | 3.5 | Run faster-whisper on scene audio, enrich `timeline.json` words[] |
| `pipeline_submit_prompts` | 4 | Accept Claude-formed image prompts JSON, write `md/image_prompts.json` |
| `pipeline_get_prompts` | 4 | Return a specific prompt batch by batch_id |
| `pipeline_generate_images` | 4 | Generate frame images via configured engine (default: stub) |
| `pipeline_get_generation_status` | 4 | Return generation progress from `md/generation_status.json` |
| `pipeline_list_images` | 4 | List expected frames and which exist on disk |
| `pipeline_assemble_scenes` | 5 | Build one MP4 per scene (frames + audio) into `renders/scenes/` |
| `pipeline_concat_scenes` | 5 | Concat scene clips into `renders/<scenario>_draft.mp4` |
| `pipeline_get_render_status` | 5 | Return assembly/concat status from `md/render_status.json` |
| `pipeline_get_output_file` | 5 | Return path, size, duration of draft render |

Verified count: **26 tools**. Run the MCP SDK snippet to confirm before adding more.

## Planned Tool Names

Future tools: `pipeline_export_davinci`. Treat as planned, not current.
Move into the approved list only when implemented and verified through `tools/list`.

## Response Shape

Every tool returns JSON. Success responses include an `instructions` field.

**Success:**
```json
{"ok": true, "data": { ... }, "instructions": "What Claude should do next..."}
```

**Failure:**
```json
{"ok": false, "error": "human-readable message", "step": 3}
```

- Never raise an unhandled exception to Claude.
- On any caught exception: return `{"ok": false, "error": str(e)}`. Include `"step"` only when the tool is tied to a specific pipeline step.
- `data` contents vary per tool but must match the schemas in `PRODUCTION_PIPELINE.md`.

## Claude.ai-Friendly Tool Schemas

Hosted Claude is stricter than the local SDK about schemas and may show
`This connector has no tools available` if it rejects the discovered tool set.

Rules:

- Every tool argument must have a clear description.
- Prefer simple JSON Schema: `type: string`, `type: object`, required fields, and defaults.
- Use string arguments where practical for web compatibility; parse inside the tool if a number is needed.
- Keep path arguments relative to the scenario workspace and validate traversal with `Path.resolve()`.
- Do not expose broad arbitrary filesystem paths to Claude.ai.
- Do not return unserializable Python objects; use strings, numbers, booleans, lists, and dicts only.
- Do not add one risky tool to the production connector without checking that all tools still appear in `tools/list`.

## State Gate Protocol

Tools that complete a step must:
1. Write `state.json` with `step_status: "complete"` **before** returning.
2. Return `{"ok": true, "data": {"step": N, "status": "complete"}}`.

Tools that start a step must:
1. First call `state.py` to verify the previous step is `"complete"`.
2. If not complete, return `{"ok": false, "error": "Step N not yet complete."}`.
3. Write `step_status: "in_progress"` at the start of the step.

Claude advances the step counter. The app sets `in_progress` and `complete` on the current step only.

## Tool Implementation Rules

- Each tool function in `server.py` does one thing: validate input → call the right module → return JSON.
- No business logic inside `server.py`. Delegate everything to `src/project/`, `src/tts/`, etc.
- Tools are synchronous unless the underlying operation requires async (image generation queue).
- All file paths returned in `data` must be absolute.
- Tool inputs that describe project identity are currently `channel` and `scenario`.
- `pipeline_set_state.step` is intentionally a numeric string in the public schema and is converted to `int` inside the tool.

**Tool function template:**
```python
@mcp.tool()
def pipeline_submit_scenario(channel: str, scenario: str, scenario_text: str) -> dict:
    try:
        ws = _workspace(channel, scenario)
        result = scenario_builder.write_scenario(ws, scenario_text)
        return {"ok": True, "data": result}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 2}
```

## Adding a New Tool Checklist

- [ ] Name matches the approved list (or update the list in this skill and `PRODUCTION_PIPELINE.md`)
- [ ] Delegates to a module in `src/` — no business logic inline
- [ ] Returns `{"ok": bool, ...}` in all code paths
- [ ] Writes or reads `state.json` via `state_manager` only
- [ ] Has a unit test that mocks the underlying service and asserts response shape
- [ ] Every parameter has a description in the generated JSON Schema
- [ ] Official MCP SDK `initialize -> tools/list` returns the new tool and the total expected count

## Remote Connector Debugging

Use this decision tree when Claude.ai connects but reports no tools:

1. Check the terminal log for `Processing request of type ListToolsRequest`.
2. If there is no `ListToolsRequest`, debug OAuth/session discovery first.
3. If there is a `ListToolsRequest`, run the official MCP SDK locally against the same server and confirm tool count.
4. If SDK sees tools but Claude.ai does not, simplify schemas: add argument descriptions, remove unusual types, and re-add the connector in Claude.ai to clear cached metadata.
5. Do not guess from `GET /mcp`; it is not a valid tools discovery check.

For Claude.ai "could not reach" failures, verify:

- `/.well-known/oauth-protected-resource/mcp` returns `200`.
- `/.well-known/oauth-authorization-server` returns `200`.
- protected resource metadata has `"resource": "https://<host>/mcp"`.
- authorization metadata includes `registration_endpoint`, `authorization_endpoint`, `token_endpoint`, and `code_challenge_methods_supported` with `S256`.
- tunnel requests with public `Host: <host>.trycloudflare.com` are not treated as direct localhost.
