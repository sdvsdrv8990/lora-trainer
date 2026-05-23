# MCP Tool Reference

The pipeline server exposes **97 tools** via MCP Streamable HTTP at `/mcp`.
All tools are named `pipeline_*` and return JSON with a consistent `{"ok": bool, ...}` shape.

Actual count (source of truth): `grep -c "@mcp.tool()" pipeline/src/mcp/server.py`

---

## Response Shape

Every tool returns JSON. Success includes `data` and `instructions`:

```json
{"ok": true, "data": { ... }, "instructions": "What Claude should do next."}
```

Every failure returns:

```json
{"ok": false, "error": "human-readable message"}
```

Tools tied to a specific pipeline step also include `"step": N` in error responses.
No tool raises an unhandled exception to Claude — all errors are caught and returned as `ok: false`.

---

## Tool List

### Workspace (8 tools)

| Tool | What it does |
|---|---|
| `pipeline_check_project` | Check if channel / scenario directories exist |
| `pipeline_create_project` | Create full workspace directory tree; optionally seed from channel_config |
| `pipeline_delete_project` | Delete scenario workspace; remove empty channel directory |
| `pipeline_get_state` | Return current `state.json` |
| `pipeline_set_state` | Update `state.json` — **Claude calls this to advance steps** |
| `pipeline_read_file` | Read a file at a relative path inside the workspace |
| `pipeline_write_file` | Write a file at a relative path inside the workspace |
| `pipeline_list_files` | List entries in a directory inside the workspace |

### Project Config (2 tools)

| Tool | What it does |
|---|---|
| `pipeline_save_project_config` | Save `project_config.json` to the scenario root |
| `pipeline_get_project_config` | Return saved `project_config.json` |

### Voiceover (4 tools)

| Tool | What it does |
|---|---|
| `pipeline_submit_scenario` | Accept `tts_input` JSON array; write `md/tts_input.json` + `scenario.txt` |
| `pipeline_start_voiceover` | Start TTS generation from `md/tts_input.json` (background or sync) |
| `pipeline_get_voiceover_status` | Return generation progress from `md/voiceover_status.json` |
| `pipeline_stop_voiceover` | Request cancellation of a running voiceover job |

### Timeline and Transcription (5 tools)

| Tool | What it does |
|---|---|
| `pipeline_build_timeline` | Run ffprobe on all scene audio; write `md/timeline.json` with durations |
| `pipeline_get_timeline` | Return full `md/timeline.json` |
| `pipeline_transcribe_scenes` | Run stable-whisper on all scenes; enrich `timeline.json` with `words[]` and `segments[]`; save `md/stable_result_scene_NNN.json` |
| `pipeline_export_subtitles` | Export SRT/VTT/ASS/TSV/TXT from saved stable-ts JSON (no re-transcription) |
| `pipeline_align_scene` | Re-align corrected text to audio; update `timeline.json` in-place for one scene |

### Legacy Image Path (5 tools)

| Tool | What it does |
|---|---|
| `pipeline_submit_prompts` | Accept image prompt JSON; write `md/image_prompts.json` |
| `pipeline_get_prompts` | Return a specific prompt batch by batch_id |
| `pipeline_generate_images` | Generate PNGs via active image engine; save `images/frame_{frame_id:04d}.png` |
| `pipeline_get_generation_status` | Return progress from `md/generation_status.json` |
| `pipeline_list_images` | List expected frames and which exist on disk |

### Scene Layout / Compositor (6 tools)

| Tool | What it does |
|---|---|
| `pipeline_submit_scene_layouts` | Save `md/scene_layout.json`; routes v1 (layers) or v2 (events) schema |
| `pipeline_render_frames` | Render frames: v2 → Remotion; v1 → Pillow compositor |
| `pipeline_get_render_frames_status` | Return render progress from `md/render_frames_status.json` |
| `pipeline_list_frames` | List expected frame PNGs and which exist |
| `pipeline_preview_frame` | Render one frame synchronously; return file path |
| `pipeline_update_frame_layout` | Replace layers for one frame without full resubmit (v1 only) |

### Asset Library (8 tools)

| Tool | What it does |
|---|---|
| `pipeline_list_assets` | List assets from `global_assets/` and/or project scope |
| `pipeline_search_assets` | Search by name, type, role, semantic tags, or emotion tags |
| `pipeline_upload_asset` | Upload SVG; auto-generate role-suffixed ID (`G-CHR-001-BODY`) |
| `pipeline_delete_asset` | Delete asset by ID; scope inferred from ID prefix |
| `pipeline_generate_asset` | Generate PNG via image engine and optionally trace to SVG |
| `pipeline_get_asset_stats` | Return usage counts and overuse warnings for one asset |
| `pipeline_list_engine_profiles` | List available image engine profiles; show active |
| `pipeline_switch_engine_profile` | Switch active image profile; takes effect on next render |

### Character Generation (3 tools)

| Tool | What it does |
|---|---|
| `pipeline_generate_character` | Generate character PNG via image engine; trace to SVG; save to `global_assets/characters/main/` |
| `pipeline_get_character_status` | Return status from `md/character_status.json` |
| `pipeline_list_characters` | List all characters in `global_assets/characters/main/` |

### FFmpeg Assembly (4 tools)

| Tool | What it does |
|---|---|
| `pipeline_assemble_scenes` | Build one MP4 per scene (frames + audio) into `renders/scenes/` |
| `pipeline_concat_scenes` | Concatenate scene clips into `renders/<scenario>_draft.mp4` |
| `pipeline_get_render_status` | Return assembly/concat status from `md/render_status.json` |
| `pipeline_get_output_file` | Return path, size, and duration of draft render |

### Registry (10 tools)

| Tool | What it does |
|---|---|
| `pipeline_get_global_registry` | Return `global_registry.json` (full or one sheet) |
| `pipeline_get_project_registry` | Return project-scoped registry (full or one sheet) |
| `pipeline_add_registry_row` | Append a row to a registry sheet |
| `pipeline_update_registry` | Update one field in a registry row by ID |
| `pipeline_delete_registry_row` | Delete a registry row by ID |
| `pipeline_add_registry_column` | Add a column to a sheet (dynamic schema, no code change) |
| `pipeline_add_registry_sheet` | Add a new named sheet to a registry |
| `pipeline_query_registry` | Filter/sort registry rows by column value |
| `pipeline_get_global_stats` | Return aggregate row counts across all global sheets |
| `pipeline_export_registry` | Export registry as clean JSON |

### Video Structure and Analytics (9 tools)

| Tool | What it does |
|---|---|
| `pipeline_set_video_structure` | Save Hook Engine structure to the project registry |
| `pipeline_get_video_structure` | Return saved video structure (modules, reset_points, hook_type) |
| `pipeline_add_emotion_map` | Append emotion timeline entries to the `emotion_map` sheet |
| `pipeline_import_platform_stats` | Import YouTube/TikTok stats into the `performance` sheet |
| `pipeline_create_experiment` | Create an A/B experiment record in the global registry |
| `pipeline_update_experiment` | Update experiment with results, winner, and insight |
| `pipeline_get_analytics` | Return aggregated analytics from the global registry |
| `pipeline_get_insights` | Return insights with minimum evidence count |
| `pipeline_compare_videos` | Compare two videos side-by-side on key metrics |

### Audio Import (2 tools)

| Tool | What it does |
|---|---|
| `pipeline_search_free_audio` | Search Freesound for background music or SFX |
| `pipeline_save_free_audio` | Download and register a Freesound result in the asset library |

### Competitor Intelligence (13 tools)

| Tool | What it does |
|---|---|
| `pipeline_add_competitor_channel` | Add a competitor channel record |
| `pipeline_update_competitor_channel` | Update competitor channel metadata |
| `pipeline_get_competitor_channel` | Return a competitor channel record |
| `pipeline_list_competitor_channels` | List all tracked competitor channels |
| `pipeline_add_competitor_video` | Add a competitor video; server computes engagement metrics |
| `pipeline_update_competitor_video` | Update competitor video fields (dot notation supported) |
| `pipeline_get_competitor_video` | Return full competitor video data |
| `pipeline_list_competitor_videos` | List all videos for a competitor channel |
| `pipeline_import_transcript` | Import a transcript (Tactiq / YouTube / manual) |
| `pipeline_get_transcript` | Return the stored transcript for a competitor video |
| `pipeline_add_competitor_index_row` | Add a row to the global competitor intelligence index |
| `pipeline_get_competitor_index` | Return the competitor intelligence index (hooks, thumbnails, pacing, patterns) |
| `pipeline_query_competitor_data` | Query competitor index with field filters and numeric ranges |

### Channel Config and Skills (8 tools)

| Tool | What it does |
|---|---|
| `pipeline_save_channel_config` | Save `channel_config.json` (the channel DNA file) |
| `pipeline_get_channel_config` | Return `channel_config.json` for a channel |
| `pipeline_update_channel_config` | Merge updates into `channel_config.json` (dot notation) |
| `pipeline_list_channels` | List all channels with config summaries |
| `pipeline_create_channel_skills` | Create 5 skill template files from channel config |
| `pipeline_update_channel_skill` | Write or overwrite one channel skill file |
| `pipeline_get_channel_skill` | Return one channel skill file content |
| `pipeline_list_channel_skills` | List all skill files with timestamps |

### Remotion / DaVinci (9 tools)

| Tool | What it does |
|---|---|
| `pipeline_render_scene` | Render one scene MP4 via Remotion (v2 layout required) |
| `pipeline_render_all_scenes` | Render all scenes via Remotion in sequence |
| `pipeline_get_remotion_status` | Return per-scene Remotion render progress |
| `pipeline_stop_render` | Cancel an active Remotion render job |
| `pipeline_update_scene_event` | Modify one field in a v2 scene event (dot notation for nested fields) |
| `pipeline_move_event` | Shift an event to a new time; re-sort the events array |
| `pipeline_preview_scene_event` | Extract PNG frame at a given time from rendered scene MP4 via FFmpeg |
| `pipeline_list_scene_events` | List all animation events for a scene |
| `pipeline_export_davinci` | Write FCPXML 1.10 to `renders/<scenario>_davinci.fcpxml` |

### Lipsync (1 tool)

| Tool | What it does |
|---|---|
| `pipeline_generate_lipsync` | Run rhubarb-lip-sync on a scene audio file; write `md/lipsync_scene_NNN.json` |

---

## State Gate Rules

Tools that start a pipeline step verify the previous step is `complete` before proceeding.
If not complete, the tool returns `{"ok": false, "error": "Step N not yet complete."}`.

Only `pipeline_set_state` may advance `current_step`. The app sets `step_status: in_progress` and `step_status: complete` on the **current** step only.

Approximate step-to-tool mapping:

| Step | Key tools |
|---|---|
| 0/1 | `pipeline_create_project`, `pipeline_save_project_config` |
| 2 | `pipeline_submit_scenario`, `pipeline_start_voiceover` |
| 3 | `pipeline_build_timeline`, `pipeline_transcribe_scenes` |
| 4 | `pipeline_submit_scene_layouts`, `pipeline_render_frames` |
| 5 | `pipeline_assemble_scenes`, `pipeline_concat_scenes` |
| 6 | `pipeline_export_davinci` |

---

## Verification Snippet

Run against a running server (`bash pipeline/start.sh`) from `pipeline/`:

```bash
venv/bin/python -c "exec('import anyio\nfrom mcp import ClientSession\nfrom mcp.client.streamable_http import streamablehttp_client\nasync def main():\n    async with streamablehttp_client(\"http://127.0.0.1:8765/mcp\", headers={\"Host\": \"localhost:8765\"}) as (read, write, _):\n        async with ClientSession(read, write) as session:\n            await session.initialize()\n            result = await session.list_tools()\n            print(\"count\", len(result.tools))\nanyio.run(main)')"
```

Do not use `GET /mcp` as a health check — stateful Streamable HTTP may return `400 Bad Request: Missing session ID`.
