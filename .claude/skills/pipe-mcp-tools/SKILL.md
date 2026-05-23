---
name: pipe-mcp-tools
description: Load when writing or modifying MCP server tools in src/mcp/server.py. Defines tool naming conventions, response shapes, gate protocol, and error handling rules.
---

# pipe-mcp-tools

## Current Approved Tool List

These are the tools the current working server exposes. Names are fixed — do not rename
without a coordinated migration in code, docs, and Claude.ai connector verification.

| Tool | Group | What it does |
|---|---|---|
| `pipeline_check_project` | workspace | Check if project/sub-project directories exist |
| `pipeline_create_project` | workspace | Create project + sub-project directory tree |
| `pipeline_delete_project` | workspace | Delete a scenario workspace and clean up an empty channel |
| `pipeline_get_state` | workspace | Return current `state.json` |
| `pipeline_set_state` | workspace | Update `state.json` — Claude uses this to advance steps |
| `pipeline_read_file` | workspace | Read a relative file inside the scenario workspace |
| `pipeline_write_file` | workspace | Write a relative file inside the scenario workspace |
| `pipeline_list_files` | workspace | List entries inside the scenario workspace |
| `pipeline_save_project_config` | config | Save `project_config.json` (agreed by Claude and user) |
| `pipeline_get_project_config` | config | Return saved `project_config.json` |
| `pipeline_submit_scenario` | voiceover | Accept structured `tts_input` JSON array and write `md/tts_input.json` |
| `pipeline_start_voiceover` | voiceover | Start voiceover generation from `md/tts_input.json` |
| `pipeline_get_voiceover_status` | voiceover | Return scenario/voiceover status for controlled workflow |
| `pipeline_stop_voiceover` | voiceover | Request cancellation of a running voiceover job |
| `pipeline_build_timeline` | timeline | Measure audio durations with ffprobe, write `md/timeline.json` |
| `pipeline_get_timeline` | timeline | Return full `md/timeline.json` for visual track planning |
| `pipeline_transcribe_scenes` | timeline | Run stable-whisper on scene audio; enrich `timeline.json` words[] + segments[]; save `stable_result_scene_NNN.json` |
| `pipeline_export_subtitles` | timeline | Export SRT/VTT/ASS/TSV/TXT from saved stable-ts JSON without re-transcribing |
| `pipeline_align_scene` | timeline | Re-align corrected text to scene audio; update `timeline.json` words[] in-place |
| `pipeline_submit_prompts` | image-v1 | Accept Claude-formed image prompts JSON, write `md/image_prompts.json` |
| `pipeline_get_prompts` | image-v1 | Return a specific prompt batch by batch_id |
| `pipeline_generate_images` | image-v1 | Generate frame images via configured engine (default: stub) |
| `pipeline_get_generation_status` | image-v1 | Return generation progress from `md/generation_status.json` |
| `pipeline_list_images` | image-v1 | List expected frames and which exist on disk |
| `pipeline_submit_scene_layouts` | compositor | Save scene layout JSON to `md/scene_layout.json` |
| `pipeline_render_frames` | compositor | Render scene frames via SVG compositor (background thread pool) |
| `pipeline_get_render_frames_status` | compositor | Return compositor render progress |
| `pipeline_list_frames` | compositor | List rendered frame PNGs in `images/` |
| `pipeline_preview_frame` | compositor | Return a single frame as base64 PNG for preview |
| `pipeline_update_frame_layout` | compositor | Update one frame's layout record |
| `pipeline_list_assets` | assets | List asset library entries with optional filters |
| `pipeline_search_assets` | assets | Semantic/tag search across asset library |
| `pipeline_upload_asset` | assets | Add an external file to the asset library |
| `pipeline_delete_asset` | assets | Remove an asset from the library |
| `pipeline_generate_asset` | assets | Generate a new asset via configured image engine |
| `pipeline_get_asset_stats` | assets | Return usage stats and overuse warnings for an asset |
| `pipeline_list_engine_profiles` | assets | List available engine profiles from `config/engines.yaml` |
| `pipeline_switch_engine_profile` | assets | Switch active engine profile |
| `pipeline_generate_character` | characters | Generate a character PNG set via configured image engine |
| `pipeline_get_character_status` | characters | Return character generation status |
| `pipeline_list_characters` | characters | List all characters in the workspace |
| `pipeline_assemble_scenes` | ffmpeg | Build one MP4 per scene (frames + audio) into `renders/scenes/` |
| `pipeline_concat_scenes` | ffmpeg | Concat scene clips into `renders/<scenario>_draft.mp4` |
| `pipeline_get_render_status` | ffmpeg | Return assembly/concat status from `md/render_status.json` |
| `pipeline_get_output_file` | ffmpeg | Return path, size, duration of draft render |
| `pipeline_get_global_registry` | registry | Return global_registry.json (all channels/scenarios) |
| `pipeline_get_project_registry` | registry | Return project-scoped registry sheet |
| `pipeline_add_registry_row` | registry | Add a row to a registry sheet |
| `pipeline_update_registry` | registry | Update one or more fields on a registry row |
| `pipeline_delete_registry_row` | registry | Delete a registry row by ID |
| `pipeline_add_registry_column` | registry | Add a column definition to a sheet |
| `pipeline_add_registry_sheet` | registry | Create a new named sheet in the project registry |
| `pipeline_query_registry` | registry | Filter/sort registry rows by column values |
| `pipeline_get_global_stats` | registry | Return aggregate stats across all projects |
| `pipeline_export_registry` | registry | Export registry to CSV/JSON file |
| `pipeline_set_video_structure` | analytics | Save episode/video structure metadata |
| `pipeline_get_video_structure` | analytics | Return saved video structure |
| `pipeline_add_emotion_map` | analytics | Add or update emotion timeline for a scene |
| `pipeline_import_platform_stats` | analytics | Import YouTube/TikTok performance stats |
| `pipeline_create_experiment` | analytics | Create an A/B experiment record |
| `pipeline_update_experiment` | analytics | Update experiment results or status |
| `pipeline_get_analytics` | analytics | Return analytics data for a video |
| `pipeline_get_insights` | analytics | Return Claude-generated insights from analytics |
| `pipeline_compare_videos` | analytics | Compare two videos side-by-side on key metrics |
| `pipeline_search_free_audio` | audio-import | Search Freesound for background music/SFX |
| `pipeline_save_free_audio` | audio-import | Download and save a Freesound result to the workspace |
| `pipeline_add_competitor_channel` | competitor | Add a competitor channel record |
| `pipeline_update_competitor_channel` | competitor | Update competitor channel metadata |
| `pipeline_get_competitor_channel` | competitor | Return a competitor channel record |
| `pipeline_list_competitor_channels` | competitor | List all tracked competitor channels |
| `pipeline_add_competitor_video` | competitor | Add a competitor video record |
| `pipeline_update_competitor_video` | competitor | Update competitor video stats or metadata |
| `pipeline_get_competitor_video` | competitor | Return a competitor video record |
| `pipeline_list_competitor_videos` | competitor | List competitor videos with optional filters |
| `pipeline_import_transcript` | competitor | Import a transcript into a competitor video record |
| `pipeline_get_competitor_index` | competitor | Return searchable index of competitor content |
| `pipeline_query_competitor_data` | competitor | Semantic/keyword query across competitor transcripts |
| `pipeline_save_channel_config` | channel | Save channel DNA config (channel_config.json) |
| `pipeline_get_channel_config` | channel | Return channel config |
| `pipeline_update_channel_config` | channel | Merge updates into channel config |
| `pipeline_list_channels` | channel | List all channels in the workspace root |
| `pipeline_create_channel_skills` | channel | Generate 5 skill .md files from channel config |
| `pipeline_update_channel_skill` | channel | Overwrite one skill .md file |
| `pipeline_get_channel_skill` | channel | Return one skill .md file content |
| `pipeline_list_channel_skills` | channel | List all skill files for a channel |
| `pipeline_render_scene` | remotion | Render one scene via Remotion (v2 path) |
| `pipeline_render_all_scenes` | remotion | Render all scenes via Remotion in sequence |
| `pipeline_get_remotion_status` | remotion | Return Remotion render progress |
| `pipeline_stop_render` | remotion | Cancel a running Remotion render job |
| `pipeline_update_scene_event` | remotion | Update animation event parameters for a scene |
| `pipeline_move_event` | remotion | Shift an animation event's timing |
| `pipeline_preview_scene_event` | remotion | Return a preview frame for a specific event |
| `pipeline_list_scene_events` | remotion | List all animation events for a scene |
| `pipeline_export_davinci` | remotion | Export FCPXML for DaVinci Resolve import |
| `pipeline_generate_lipsync` | lipsync | Generate lipsync animation data for a scene |

Verified count: **95 tools**. Run the MCP SDK snippet to confirm before adding more.

## Planned Tool Names

No tools are currently planned-but-unimplemented. `pipeline_export_davinci` and
`pipeline_generate_lipsync` are in the server. Move new names into the approved list
only when implemented and verified through `tools/list`.

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
