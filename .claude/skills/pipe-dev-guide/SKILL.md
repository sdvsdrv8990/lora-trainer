---
name: pipe-dev-guide
description: Always load first when working on the video pipeline app. Defines project identity, layer map, module boundaries, and non-negotiable implementation rules.
---

# pipe-dev-guide

## First Read

Before any work on the pipeline app, read:

- `PRODUCTION_PIPELINE.md` — step-by-step workflow and gate conditions
- `docs/pipeline/ARCHITECTURE.md` — layer structure, module map, GitHub deps, data flow
- `.planning/STATE.md` — current session state

## Project Identity

This is a Python CLI app that orchestrates video production via Claude.ai.
It is NOT a media player, a standalone editor, or an AI training tool.

It IS:
- an MCP server that Claude.ai web controls
- a wrapper around espeak-ng TTS, FFmpeg, Diffusers (stub default), and optionally DaVinci Resolve
- a state machine that advances through 7 pipeline steps
- a swappable-engine platform (TTS and image generation are always config-driven)

## Current Working Surface

The currently working implementation is the MCP bridge in `pipeline/`.
It exposes **95 verified tools**. Verified count via MCP SDK `tools/list`: **95**.

**Project / workspace tools (8):**
`pipeline_check_project`, `pipeline_create_project`, `pipeline_delete_project`,
`pipeline_get_state`, `pipeline_set_state`, `pipeline_read_file`, `pipeline_write_file`, `pipeline_list_files`

**Config tools (2):**
`pipeline_save_project_config`, `pipeline_get_project_config`

**Scenario / voiceover tools (4):**
`pipeline_submit_scenario`, `pipeline_start_voiceover`, `pipeline_get_voiceover_status`, `pipeline_stop_voiceover`

**Timeline / transcription / subtitle tools (5):**
`pipeline_build_timeline`, `pipeline_get_timeline`, `pipeline_transcribe_scenes`,
`pipeline_export_subtitles`, `pipeline_align_scene`

**Legacy prompt/image path (5):**
`pipeline_submit_prompts`, `pipeline_get_prompts`, `pipeline_generate_images`, `pipeline_get_generation_status`, `pipeline_list_images`

**Asset library tools (8):**
`pipeline_list_assets`, `pipeline_search_assets`, `pipeline_upload_asset`, `pipeline_delete_asset`,
`pipeline_generate_asset`, `pipeline_get_asset_stats`, `pipeline_list_engine_profiles`, `pipeline_switch_engine_profile`

**Character tools (3):**
`pipeline_generate_character`, `pipeline_get_character_status`, `pipeline_list_characters`

**Scene layout / compositing tools (6):**
`pipeline_submit_scene_layouts`, `pipeline_render_frames`, `pipeline_get_render_frames_status`,
`pipeline_list_frames`, `pipeline_preview_frame`, `pipeline_update_frame_layout`

**Registry tools (10):**
`pipeline_get_global_registry`, `pipeline_get_project_registry`, `pipeline_add_registry_row`,
`pipeline_update_registry`, `pipeline_delete_registry_row`, `pipeline_add_registry_column`,
`pipeline_add_registry_sheet`, `pipeline_query_registry`, `pipeline_get_global_stats`, `pipeline_export_registry`

**Analytics / video structure tools (9):**
`pipeline_set_video_structure`, `pipeline_get_video_structure`, `pipeline_add_emotion_map`,
`pipeline_import_platform_stats`, `pipeline_create_experiment`, `pipeline_update_experiment`,
`pipeline_get_analytics`, `pipeline_get_insights`, `pipeline_compare_videos`

**Audio import tools (2):**
`pipeline_search_free_audio`, `pipeline_save_free_audio`

**Competitor intelligence tools (11):**
`pipeline_add_competitor_channel`, `pipeline_update_competitor_channel`, `pipeline_get_competitor_channel`,
`pipeline_list_competitor_channels`, `pipeline_add_competitor_video`, `pipeline_update_competitor_video`,
`pipeline_get_competitor_video`, `pipeline_list_competitor_videos`, `pipeline_import_transcript`,
`pipeline_get_competitor_index`, `pipeline_query_competitor_data`

**Channel config + skills tools (8):**
`pipeline_save_channel_config`, `pipeline_get_channel_config`, `pipeline_update_channel_config`,
`pipeline_list_channels`, `pipeline_create_channel_skills`, `pipeline_update_channel_skill`,
`pipeline_get_channel_skill`, `pipeline_list_channel_skills`

**FFmpeg assembly tools (4):**
`pipeline_assemble_scenes`, `pipeline_concat_scenes`, `pipeline_get_render_status`, `pipeline_get_output_file`

**Remotion / DaVinci v2 path tools (9):**
`pipeline_render_scene`, `pipeline_render_all_scenes`, `pipeline_get_remotion_status`, `pipeline_stop_render`,
`pipeline_update_scene_event`, `pipeline_move_event`, `pipeline_preview_scene_event`,
`pipeline_list_scene_events`, `pipeline_export_davinci`

**Lipsync tools (1):**
`pipeline_generate_lipsync`

Do not assume planned tools from `PRODUCTION_PIPELINE.md` already exist. When adding a
future pipeline step, update the skill docs and verification evidence in the same change.

## Layer Map

| Layer | Module | Responsibility |
|---|---|---|
| 0 | `src/entities/` | Pydantic models: project, scenario, state, config, timeline, prompts, layout |
| 1 | `src/mcp/server.py` | MCP tool server — exposes 95 `pipeline_*` tools |
| 2 | `src/project/manager.py` + `state.py` + `config.py` | Workspace, state.json, project_config.json |
| 3 | `src/scenario/builder.py` | Validates structured tts_input → `md/tts_input.json` |
| 4 | `src/tts/` | Abstract engine + espeak adapter |
| 5 | `src/audio/analyzer.py` | ffprobe → `md/timeline.json` (durations) |
| 5.5 | `src/audio/transcriber.py` | stable-whisper (faster-whisper backend) → enriches `timeline.json` words[] + segments[]; saves `md/stable_result_scene_NNN.json` |
| 5.6 | `src/audio/subtitle_exporter.py` | Loads stable-ts JSON → SRT/VTT/ASS/TSV/TXT without re-transcribing; `align_scene()` re-aligns corrected text |
| 5.7 | `src/audio/audio_import.py` | Freesound search + download; `_TEMP_STORE` for two-step import |
| 6 | `src/images/prompts.py` | Saves/loads `md/image_prompts.json` |
| 6.1 | `src/images/engine.py` + `adapters/` | Abstract ImageEngine + stub/diffusers adapters |
| 6.2 | `src/images/batch.py` | Generation loop, `md/generation_status.json` |
| 6.3 | `src/images/assets.py` | Asset library v2: G-/P- role-suffixed IDs, semantic/emotion tags, overuse detection |
| 6.4 | `src/images/compositor.py` | SVG→PNG rendering; character_composite / asset_composite layer types |
| 6.5 | `src/images/layout_store.py` | Saves/loads `md/scene_layout.json` |
| 6.6 | `src/images/render_jobs.py` | Background rendering thread pool |
| 6.7 | `src/images/character_jobs.py` | Character PNG generation + status tracking |
| 6.8 | `src/images/engine_profiles.py` | Profile switching; persists to `config/engines.yaml` |
| 7 | `src/workflow/instructions.py` | 50+ instruction templates + `get_workflow_guidance()` |
| 8 | `src/registry.py` | global_registry.json + project_registry.json; fcntl locking; group sheets |
| 9 | `src/assembly/ffmpeg.py` | Assembles scenes + concat → `renders/<name>_draft.mp4` |
| 10 | `src/competitor/manager.py` | Competitor channel/video storage; engagement formula computation |
| 11 | `src/channel/manager.py` | Channel DNA (channel_config.json) + 5 skill .md files |
| 12 | `src/davinci/exporter.py` | DaVinci Resolve final export (planned — zero code) |

## Module Boundaries

- `mcp/server.py` only dispatches to other modules — no business logic inside.
- `tts/engine.py` and `images/engine.py` contain only abstract base classes — no engine code.
- Engine-specific code lives exclusively in `adapters/`.
- `project/state.py` is the only place that reads or writes `state.json`.
- `project/config.py` is the only place that reads or writes `project_config.json`.
- `audio/analyzer.py` reads audio files and writes `md/timeline.json` — never derives timings from tts_input.
- `audio/transcriber.py` enriches `timeline.json` words[] + segments[] — reads and writes the same file, never changes durations; always saves `md/stable_result_scene_NNN.json` alongside.
- `audio/subtitle_exporter.py` reads `md/stable_result_scene_NNN.json` — never re-transcribes; writes to `md/subtitles/`.
- `images/batch.py` writes `images/frame_{frame_id:04d}.png` — naming is by frame_id, not scene_id.
- `assembly/ffmpeg.py` reads `md/timeline.json` and `md/image_prompts.json` — never re-derives timings from audio.

## Non-Negotiables

1. No `utils.py`, no `helpers.py`, no grab-bag modules.
2. Swapping TTS or image engine = config change only, never code change.
3. The app never advances pipeline step — only Claude does via `pipeline_set_state`.
4. Every MCP tool returns `{"ok": bool, ...}` — never raise to Claude.
5. `state.json` is written before any tool returns.
6. JSON field names must exactly match `PRODUCTION_PIPELINE.md` schemas.

## Claude.ai Connector Rules

Claude.ai web connects through the URL printed by `bash pipeline/start.sh`:

```text
https://<trycloudflare-host>/mcp
```

The connector depends on three early handshake pieces:

1. `/.well-known/oauth-protected-resource/mcp` returns protected resource metadata.
2. `/.well-known/oauth-authorization-server` returns authorization metadata with registration, authorization, token, and S256 PKCE support.
3. `POST /mcp` can complete MCP `initialize`, then `tools/list` returns the expected tools.

Do not break these invariants:

- Do not use a bare `GET /mcp` as readiness proof; stateful Streamable HTTP may return `400 Bad Request: Missing session ID`.
- Do not hide OAuth metadata for every `127.0.0.1` request. `cloudflared` also reaches uvicorn from loopback while preserving the public Host header.
- Do hide OAuth metadata for direct local `Host: localhost` or `Host: 127.0.0.1`, so Claude Code can keep using non-OAuth localhost.
- Do not set `resource_server_url` to only the tunnel origin. It must include `/mcp`, otherwise Claude.ai looks for the wrong protected-resource metadata path.
- After auth or schema changes, remove and re-add the Claude.ai custom integration because hosted Claude can cache metadata.

## Completion Evidence

For any code change provide at least one of:
- unit test result (`pytest tests/unit/`)
- dry-run MCP tool call log
- official MCP Python SDK `initialize -> tools/list` output for MCP protocol changes
- explicit reason why runtime verification was not possible

## Two-Phase Work Protocol

This project is developed from a **cloud Claude Code session** (no local runtime) and
verified on the **user's local PC** where the pipeline server actually runs.

### Phase 1 — Cloud Session (write code, commit, push)

Safe to do here:
- Read, edit, create source files
- Static validation: `python3 -m py_compile`, `bash -n`
- Count tools with `grep -c "@mcp.tool()"` 
- `git add`, `git commit`, `git push` (using PAT remote URL)

NOT possible here:
- `python main.py start` — heavy runtime deps not installed
- MCP SDK `tools/list` verification — requires running server
- Claude.ai connector reconnect — requires browser UI

### Phase 2 — Local PC (run, verify, reconnect)

After each significant push:
1. `git pull origin <branch>`
2. `bash pipeline/start.sh`
3. Run MCP SDK snippet (expected count: **95**) — see `pipe-planning-gate` for the command
4. If count matches: remove and re-add Claude.ai custom integration
5. Test changed tools via Claude.ai web

### Git Push in Cloud Sessions

Cloud environment blocks git push over standard HTTPS. Use PAT in remote URL:
```bash
git remote set-url origin https://TOKEN@github.com/sdvsdrv8990/lora-trainer.git
git push -u origin <branch>
git remote set-url origin https://github.com/sdvsdrv8990/lora-trainer.git
```
