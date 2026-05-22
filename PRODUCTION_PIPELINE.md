# Production Pipeline — Architecture and Workflow

## What This Document Is

A complete description of the end-to-end video production pipeline controlled by Claude AI.
This is the reference document for any AI or developer working on this system.
It describes how the components connect, what each step does, what triggers the next step, and what the gate conditions are.

**Related documents:**
- `docs/pipeline/ARCHITECTURE.md` — layer-by-layer implementation structure, GitHub dependencies, module map

---

## Development Skills

Load skills in this order before writing any pipeline app code:

| When | Skill |
|---|---|
| Always first | `/pipe-dev-guide` |
| Before any code change | `/pipe-planning-gate` |
| Writing/modifying TTS or image engine adapters | `/pipe-adapter-pattern` |
| Writing/modifying MCP tools in `src/mcp/server.py` | `/pipe-mcp-tools` |
| Adding/modifying Pydantic entities or config | `/pipe-entities` |
| Writing any test | `/pipe-test-patterns` |

---

## System Components

```
Claude.ai Web (browser)
    │
    │  MCP tools / commands
    ▼
CLI App (console, this project)
    │
    ├── Project Manager     ← creates/manages projects and channels
    ├── Prompt Writer       ← generates image prompts as MD files
    ├── Voiceover Processor ← measures exact audio duration
    ├── Image Generator     ← generates images using prompt MD + timing data
    └── FFmpeg Assembler    ← combines images + audio into video
```

---

## Production Trigger

**Entry point:** User writes a scenario inside Claude.ai web and says "send to production" (or equivalent phrase).

Claude.ai web recognizes this intent and dispatches the pipeline by sending commands to the CLI app via MCP.

**The CLI app must be running in console before the user triggers production.**
Claude cannot start the app. The app must already be listening.

---

## Step 0 — Project Resolution

Before any production work starts, the CLI app resolves which project the scenario belongs to.

**Logic:**

**Case 1 — Project and sub-project both exist:**
- CLI opens the existing sub-project as the active workspace.
- All subsequent files (voiceover, images, MD files, renders, final video) are saved inside it.
- Claude receives the existing project context and continues without creating new directories.

**Case 2 — Project exists, sub-project is missing:**
- CLI creates the missing sub-project directory.
- CLI automatically creates the full folder structure inside it.
- CLI opens the new sub-project as the active working directory.

**Case 3 — Neither project nor sub-project exists:**
- CLI creates the channel project directory.
- CLI creates the scenario sub-project directory.
- CLI creates the full folder structure.
- CLI assigns the sub-project as the active workspace.

**Case 4 — Claude lacks the data needed to resolve the project:**

Claude asks clarifying questions:
- "What is the channel name?"
- "What is the scenario name?"
- "Should I use an existing project or create a new one?"
- "Where should the materials be saved?"

No production step starts until project resolution is complete and confirmed.

---

## Step 1 — Project and Sub-Project Creation

If the project or sub-project does not exist, the CLI app creates the directory structure using its built-in commands.

**Project structure:**
```
projects/
└── <channel_name>/              ← one directory per channel
    └── <scenario_name>/         ← one sub-project per scenario
        ├── audio/               ← voiceover, music, SFX
        ├── images/              ← scene images
        ├── prompts/             ← image generation prompts
        ├── md/                  ← JSON data files (tts_input, timeline, image_prompts, voiceover_status)
        ├── renders/             ← intermediate renders
        ├── final/               ← finished videos
        ├── state.json           ← current pipeline step and status
        └── project_config.json  ← project settings agreed by Claude and user
```

**Gate condition:** Step 2 does not start until `state.json` is written with `step: 1, status: complete`.

---

## Step 1.5 — Project Config

Before writing the scenario, Claude conducts a dialogue with the user to agree on project settings and saves them via `pipeline_save_project_config`.

**`project_config.json` schema:**
```json
{
  "project": {
    "title": "Project title",
    "description": "Short description",
    "created_at": "2026-05-20T19:00:00"
  },
  "style": {
    "type": "slideshow | animation | mixed",
    "mood": "noir | dramatic | neutral | ...",
    "visual_references": ["reference descriptions"]
  },
  "frame_rules": {
    "mode": "dynamic | fixed | manual",
    "default_duration_sec": 5,
    "min_duration_sec": 1,
    "max_duration_sec": 15,
    "change_triggers": ["location change", "character change", "speech pause > 1s", "..."]
  },
  "audio": {
    "tts_engine": "espeak",
    "default_emotion": "neutral",
    "default_speed": 1.0,
    "pause_between_scenes_sec": 0.5
  },
  "prompts": {
    "batch_size": 50,
    "style_prefix": "black and white, noir, cinematic, ...",
    "negative_prompt": "..."
  }
}
```

`frame_rules.mode` values:
- `dynamic` — Claude decides where to cut based on timings and meaning
- `fixed` — new frame every N seconds
- `manual` — user specifies cut points manually

`prompts.batch_size` is not hardcoded. Claude and the user agree: for animations usually 10–20, for slideshows may be 100+.

**Gate condition:** Scenario work does not start until `project_config.json` is saved.

---

## Step 2 — Scenario Preparation and Voiceover

### 2.1 — Full Scenario Creation

Claude:
1. Writes the complete scenario in full.
2. Splits it into scenes.
3. Cleans the text:
   - removes repetitions
   - removes random artifacts
   - removes stray characters
   - fixes broken phrases
4. Verifies that transitions between scenes are logical.
5. Confirms the final version with the user.

**Gate condition:** Step 2.2 does not start until the user confirms the scenario.

---

### 2.2 — Voiceover Data Preparation

After the scenario is confirmed, Claude produces a structured list of scenes and sends it via `pipeline_submit_scenario`. The server validates, saves `tts_input.json` as-is, and builds `scenario.txt` by joining scene texts. **No text splitting happens on the server — Claude forms scenes in dialogue with the user.**

A scene is an atomic video unit: a text fragment (voiceover) + image or animation + music. One chapter may have any number of scenes — this is a creative decision between Claude and the user.

**JSON format (per scene):**
```json
{
  "scene_id": 12,
  "chapter": "Chapter 3. The Secret",
  "text": "You can't even imagine what this symbol hides.",
  "tts": {
    "emotion": "mystery",
    "pause_before": 0.4,
    "pause_after": 0.8,
    "stress": ["imagine", "hides"],
    "speed": 0.92
  },
  "metadata": {
    "notes": "any Claude notes about this scene"
  }
}
```

File is written to `projects/<channel>/<scenario>/md/tts_input.json`.
Plain text is written to `projects/<channel>/<scenario>/md/scenario.txt`.

---

### 2.3 — Separation of Scenario Text and Technical Data

The CLI app must:
- Clearly distinguish clean scenario text from technical TTS instructions.
- Never send service instructions directly into the voiceover engine.
- Maintain separate fields: `text`, `tts`, `metadata`.

---

### 2.4 — Voiceover Generation

The CLI app generates audio using the configured TTS engine.

**Default engine:** espeak-ng (configured in `config/engines.yaml`).

**Requirement:** swapping TTS engines must require no code changes — only config changes.

Engine is selected via `config/engines.yaml`:
```yaml
tts:
  engine: "espeak"
  model: "espeak-ng"
  voice: "ru"
  speed_wpm: 150
```

Generated audio files are written to `projects/<channel>/<scenario>/audio/scene_<NNN>.mp3`.

**Gate condition:** Step 3 does not start until all audio files are generated and present on disk.

---

## Step 3 — Audio Analysis and Synchronization

After audio generation is complete, Claude calls `pipeline_build_timeline` to measure durations, then `pipeline_get_timeline` to read the full data.

**Process:**
1. `pipeline_build_timeline` — measures every `audio/scene_NNN.mp3` with ffprobe, writes `md/timeline.json`.
2. `pipeline_get_timeline` — returns the full timeline so Claude can plan the visual track.

### 3.1 — Timeline Format

File written to `projects/<channel>/<scenario>/md/timeline.json`.

**JSON format (per scene):**
```json
[
  {
    "scene_id": 12,
    "chapter": "Chapter 3. The Secret",
    "audio_file": "/abs/path/to/audio/scene_012.mp3",
    "start": 0.0,
    "end": 4.2,
    "duration": 4.2,
    "text": "You can't even imagine what this symbol hides.",
    "words": [
      {"word": "You", "start": 0.1, "end": 0.3},
      {"word": "can't", "start": 0.4, "end": 0.7}
    ]
  }
]
```

`words` — word-level timings if Whisper is available; otherwise an empty array. Claude uses word-level pauses as cut triggers in `dynamic` frame mode.

Claude receives: cumulative start/end offsets, scene durations, and word timings for visual track planning.

**Gate condition:** Step 4 does not start until Claude confirms it has received and processed the timeline.

---

## Step 4 — Compositing and Frame Generation

With exact timings in hand, Claude designs the visual track and generates rendered frames.

### 4.1 — Asset Management

Claude builds and manages a library of SVG assets (characters, backgrounds, props) stored in `global_assets/` (shared across projects) and `md/project_assets/` (scenario-specific).

Asset IDs follow the v2 format: `{G|P}-{TYPE}-{group:03d}-{seq:03d}-{ROLE}` (e.g. `G-CHR-001-001-BODY`).

**Asset roles:** BASE (reference), BODY, FACE, EYES (character parts), CTX (context/background), PART (asset part), COMP (cached composite), LORA (LoRA trigger), PROP (prop).

Assets carry semantic and emotion tags for search (`pipeline_search_assets` supports role/semantic/emotion/category filters).

---

### 4.2 — Scene Layout Design

Claude calls `pipeline_submit_scene_layouts` with a `SceneLayout` JSON describing every frame:

```json
{
  "frames": [
    {
      "frame_id": "frame_001",
      "scene_id": 12,
      "duration": 4.2,
      "canvas": {"width": 1080, "height": 1920, "background_color": "#1a1a1a"},
      "layers": [
        {"id": "bg", "type": "asset", "asset_id": "G-BG-001-001-BASE", "x": 0, "y": 0, "scale": 1.0},
        {
          "id": "char", "type": "character_composite",
          "group_id": "G-CHR-001",
          "components": [
            {"role": "BODY", "asset_id": "G-CHR-001-001-BODY", "z_index": 0},
            {"role": "FACE", "asset_id": "G-CHR-001-001-FACE", "z_index": 1},
            {"role": "EYES", "asset_id": "G-CHR-001-001-EYES", "z_index": 2}
          ],
          "save_as_comp": true
        }
      ]
    }
  ]
}
```

Layer types: `asset`, `character` (legacy), `character_composite` (BODY+FACE+EYES stacked), `asset_composite` (PARTs stacked), `generated`, `speech_bubble`, `text`.

---

### 4.3 — Frame Rendering

`pipeline_render_frames` compiles the layout into PNG frames in `renders/frames/`. SVG assets are rasterized via cairosvg (or Pillow fallback). Composite layers are composited by z_index with optional color substitution. COMP assets are cached automatically when `save_as_comp: true`.

Usage counters are incremented on each render so overuse can be detected.

`pipeline_preview_frame` renders a single frame synchronously for fast layout verification.

---

### 4.4 — Legacy Prompt Path (still available)

For text-to-image workflows, Claude may use: `pipeline_submit_prompts` → `pipeline_generate_images` → assembly. This path uses `md/image_prompts.json` and generates PNG files via the configured diffusers/stub engine.

Engine is configured in `config/engines.yaml` and switchable via `pipeline_switch_engine_profile` without code changes.

---

### 4.5 — Registry and Analytics

Claude maintains structured data across all projects in `global_registry.json` (global) and `project_registry.json` (scenario-level):

- Standard sheets: assets, scenes, hooks, emotion_map, performance, insights, experiments
- Dynamic sheets and columns can be added via `pipeline_add_registry_sheet` / `pipeline_add_registry_column`
- `pipeline_set_video_structure` records the Hook Engine model (hook type, modules, reward type)
- `pipeline_add_emotion_map` records per-scene emotion timeline
- `pipeline_create_experiment` / `pipeline_update_experiment` track A/B tests
- `pipeline_get_analytics` / `pipeline_get_insights` / `pipeline_compare_videos` return aggregated data

**Gate condition:** Step 5 does not start until all frames exist in `renders/frames/` and Claude sends a full-completion signal.

---

## Step 5 — Preliminary Assembly

The CLI app assembles a preliminary synchronized video using FFmpeg.

**Inputs:**
- All images from `images/frame_{frame_id:04d}.png` (one per frame in `image_prompts.json`)
- All audio files from `audio/scene_<NNN>.mp3`
- Timing data from `md/timeline.json`

**Process:**
1. `pipeline_assemble_scenes` — for each scene, build one `renders/scenes/scene_NNN.mp4` clip:
   - Each frame image is held for its duration (`frame.duration` seconds).
   - Audio from `audio/scene_NNN.mp3` is synced to the frame sequence via ffmpeg.
   - Single-frame scenes use `-loop 1`; multi-frame scenes use `filter_complex concat`.
2. `pipeline_concat_scenes` — concatenate all scene clips into `renders/<scenario_name>_draft.mp4`.
3. `pipeline_get_output_file` — return absolute path, size, and duration of the draft file.

**Gate condition:** Step 6 does not start until the draft render file exists and FFmpeg exits with code 0.

---

## Step 6 — Final Editing in DaVinci Resolve

> **Status: planned — not implemented.** No code exists for this step. `pipeline_export_davinci` is not in the tool registry. This section describes the intended design.

After the preliminary render, the project would be handed off to DaVinci Resolve via the Python Scripting API.

**Planned DaVinci Resolve operations:**
- Final editing
- Transitions
- Visual effects
- Color grading
- Motion effects
- Subtitles
- Sound design
- Final export

**Planned output:** finished video written to `projects/<channel>/<scenario>/final/<scenario_name>.mp4`.

**Gate condition (planned):** Pipeline complete when the final video file exists and DaVinci Resolve reports successful export.

---

## Gate System Rules

These rules apply to every step in the pipeline.

1. **No step starts until the previous step signals completion.** Claude sends an explicit signal; the app does not auto-advance.
2. **State is persisted in `state.json`** at the end of each step. If the pipeline crashes, it resumes from the last completed step.
3. **If a step fails**, the app writes the error to `state.json` and waits. Claude receives the error and decides whether to retry, fix, or abort.
4. **Claude is the orchestrator.** The CLI app executes commands; Claude makes decisions.

**`state.json` shape:**
```json
{
  "channel": "channel_name",
  "scenario": "scenario_name",
  "current_step": 4,
  "step_status": "complete",
  "last_updated": "2026-05-19T14:00:00Z",
  "errors": []
}
```

**Step index reference:**

| Value | Step |
|---|---|
| 0 | Project resolution |
| 1 | Project/sub-project creation |
| 2 | Scenario creation and voiceover |
| 3 | Audio analysis and synchronization |
| 4 | Image generation |
| 5 | Preliminary FFmpeg assembly |
| 6 | DaVinci Resolve final export |

---

## Claude.ai Web ↔ CLI App Interface

Claude.ai web connects to the CLI app via **MCP tools** exposed by the CLI app.

The CLI app runs a local MCP server that Claude.ai web can connect to.

**MCP tools the CLI app exposes (83 total):**

| Tool | Step | Description |
|---|---|---|
| `pipeline_check_project` | 0 | Check if a project/sub-project exists for a given channel and scenario |
| `pipeline_create_project` | 1 | Create project and sub-project directory structure; accepts channel_id to seed config |
| `pipeline_delete_project` | 0/1 | Delete a scenario workspace and clean up an empty channel |
| `pipeline_get_state` | any | Return current `state.json` for a sub-project |
| `pipeline_set_state` | any | Update `state.json` — used by Claude to advance or reset a step |
| `pipeline_read_file` | any | Read a relative file inside the scenario workspace |
| `pipeline_write_file` | any | Write a relative file inside the scenario workspace |
| `pipeline_list_files` | any | List files inside the scenario workspace |
| `pipeline_save_project_config` | 1.5 | Save `project_config.json` (agreed by Claude and user) to workspace root |
| `pipeline_get_project_config` | any | Return saved `project_config.json` |
| `pipeline_submit_scenario` | 2 | Accept structured `tts_input` (JSON array of scenes) and write `md/tts_input.json` |
| `pipeline_start_voiceover` | 2 | Start voiceover generation from `md/tts_input.json` |
| `pipeline_get_voiceover_status` | 2 | Return scenario/voiceover workflow status |
| `pipeline_stop_voiceover` | 2 | Request cancellation of a running voiceover job |
| `pipeline_build_timeline` | 3 | Measure audio durations with ffprobe and write `md/timeline.json` |
| `pipeline_get_timeline` | 3 | Return full `md/timeline.json` for visual track planning |
| `pipeline_transcribe_scenes` | 3.5 | Run faster-whisper on all scene audio files and enrich `timeline.json` with word-level timings |
| `pipeline_submit_prompts` | 4 | Accept Claude-formed image prompts JSON and write `md/image_prompts.json` (legacy path) |
| `pipeline_get_prompts` | 4 | Return a specific prompt batch by batch_id for image generation (legacy path) |
| `pipeline_generate_images` | 4 | Generate frame images from `md/image_prompts.json` via the configured engine (legacy path) |
| `pipeline_get_generation_status` | 4 | Return current image generation progress from `md/generation_status.json` |
| `pipeline_list_images` | 4 | List expected frame files and which exist on disk |
| `pipeline_list_assets` | 4 | List assets in global or project scope with overuse warnings |
| `pipeline_search_assets` | 4 | Search assets by role, semantic tags, emotion tags, or category |
| `pipeline_upload_asset` | 4 | Upload SVG asset; assigns v2 ID (G-CHR-001-001-BODY); accepts semantic/emotion tags |
| `pipeline_delete_asset` | 4 | Delete an asset from the index and disk |
| `pipeline_generate_asset` | 4 | Generate SVG asset via diffusers + vtracer |
| `pipeline_get_asset_stats` | 4 | Return file size, existence, and usage stats for an asset |
| `pipeline_list_engine_profiles` | 4 | List available image engine profiles |
| `pipeline_switch_engine_profile` | 4 | Switch active engine profile; persists to engines.yaml |
| `pipeline_generate_character` | 4 | Generate character PNG via image engine + SVG trace; background threading |
| `pipeline_get_character_status` | 4 | Return last character generation status |
| `pipeline_list_characters` | 4 | List all characters in global_assets/characters/main/ |
| `pipeline_submit_scene_layouts` | 4 | Accept SceneLayout JSON and write `md/scene_layout.json` |
| `pipeline_render_frames` | 4 | Render all layout frames to PNG; increments usage counters; background threading |
| `pipeline_get_render_frames_status` | 4 | Return render progress from `md/render_status.json` |
| `pipeline_list_frames` | 4 | List rendered frame files |
| `pipeline_preview_frame` | 4 | Render a single frame synchronously for layout verification |
| `pipeline_update_frame_layout` | 4 | Update layers in an existing frame without full resubmit |
| `pipeline_get_global_registry` | 4 | Return global_registry.json (all sheets) |
| `pipeline_get_project_registry` | 4 | Return project_registry.json (all sheets) |
| `pipeline_add_registry_row` | 4 | Add a row to a registry sheet |
| `pipeline_update_registry` | 4 | Update a field in a registry row |
| `pipeline_delete_registry_row` | 4 | Delete a row from a registry sheet |
| `pipeline_add_registry_column` | 4 | Add a column to a registry sheet (dynamic schema) |
| `pipeline_add_registry_sheet` | 4 | Add a new sheet to a registry (dynamic schema) |
| `pipeline_query_registry` | 4 | Filter registry rows by a field value |
| `pipeline_get_global_stats` | 4 | Return aggregate stats from global_registry.json |
| `pipeline_export_registry` | 4 | Export a registry sheet as CSV |
| `pipeline_set_video_structure` | 4 | Record Hook Engine model (hook type, modules, reset_points, reward_type) |
| `pipeline_get_video_structure` | 4 | Return saved video structure |
| `pipeline_add_emotion_map` | 4 | Add per-scene emotion timeline entries |
| `pipeline_import_platform_stats` | 4 | Import platform retention/engagement stats |
| `pipeline_create_experiment` | 4 | Create an A/B experiment entry |
| `pipeline_update_experiment` | 4 | Record result, winner, and insight for an experiment |
| `pipeline_get_analytics` | 4 | Return aggregated analytics with optional filters |
| `pipeline_get_insights` | 4 | Return insights with sufficient supporting evidence |
| `pipeline_compare_videos` | 4 | Compare performance data for two videos side by side |
| `pipeline_search_free_audio` | 4 | Search Freesound for music/SFX (returns import_ids for save step) |
| `pipeline_save_free_audio` | 4 | Download and register a Freesound result into the asset index |
| `pipeline_add_competitor_channel` | CI | Add a competitor channel record |
| `pipeline_get_competitor_channel` | CI | Return a competitor channel record |
| `pipeline_list_competitor_channels` | CI | List all competitor channels |
| `pipeline_add_competitor_video` | CI | Add a competitor video; applies engagement formulas automatically |
| `pipeline_update_competitor_video` | CI | Update competitor video fields (dot notation) |
| `pipeline_get_competitor_video` | CI | Return a competitor video record |
| `pipeline_list_competitor_videos` | CI | List all videos for a competitor channel |
| `pipeline_import_transcript` | CI | Store a transcript for a competitor video |
| `pipeline_get_transcript` | CI | Return a competitor video transcript |
| `pipeline_get_competitor_index` | CI | Return the global competitor index (hooks/thumbnails/pacing/patterns) |
| `pipeline_query_competitor_data` | CI | Filter the global competitor index by field value |
| `pipeline_save_channel_config` | CH | Save channel_config.json (channel DNA) |
| `pipeline_get_channel_config` | CH | Return channel_config.json |
| `pipeline_update_channel_config` | CH | Update channel config fields (dot notation) |
| `pipeline_list_channels` | CH | List all channels with config |
| `pipeline_create_channel_skills` | CH | Create 5 skill .md template files for a channel |
| `pipeline_update_channel_skill` | CH | Write/update a channel skill file (SCENARIO_WRITER etc.) |
| `pipeline_get_channel_skill` | CH | Return a channel skill file |
| `pipeline_list_channel_skills` | CH | List all skill files for a channel |
| `pipeline_assemble_scenes` | 5 | Build one MP4 clip per scene (frames + audio) into `renders/scenes/` |
| `pipeline_concat_scenes` | 5 | Concatenate scene clips into `renders/<scenario>_draft.mp4` |
| `pipeline_get_render_status` | 5 | Return assembly and concat status from `md/render_status.json` |
| `pipeline_get_output_file` | 5 | Return path, size, and duration of the draft render file |

**Step column key:** CI = Competitor Intelligence (pre-production), CH = Channel Config (pre-production), 4 = Frame generation / registry / analytics.

Every tool response includes a top-level `instructions` field with guidance for Claude on what to do next.

Planned future tools: `pipeline_export_davinci`. Add to this table only when implemented and verified through MCP `tools/list`.

**The CLI app never advances the pipeline on its own.** Only Claude calls `pipeline_set_state` to advance steps. The CLI app executes, Claude decides.

---

## What Is NOT In Scope

- The CLI app does not decide which step to run next — Claude does.
- The CLI app does not generate prompts — Claude does.
- The CLI app does not know about channel strategy or scenario content — Claude does.
- LoRA model training (separate tool: `lora-trainer`) is a prerequisite, not part of this pipeline.

---

## Open Questions (To Be Resolved)

- [ ] How does Claude.ai web discover the local MCP server address? (localhost port? config file?)
- [ ] What is the channel configuration format? (dimensions, style, language, voice profile)
- [ ] Where is the TTS/image engine config stored? (project-level YAML, global config, env vars?)
- [ ] How does DaVinci Resolve receive the project — via a shared folder, a Resolve project file, or a Python script that builds the timeline from scratch?
- [ ] What is the subtitle source for DaVinci Resolve — generated from `md/timing_report.json` or a separate file?
- [ ] How are batches of fewer than 50 scenes handled at the end of a scenario?
