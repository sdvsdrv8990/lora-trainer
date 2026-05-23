# Production Pipeline — Architecture and Workflow

## What This Document Is

A complete description of the end-to-end video production pipeline controlled by Claude AI.
This is the reference document for any AI or developer working on this system.
It describes how the components connect, what each step does, what triggers the next step, and what the gate conditions are.

**Related documents:**
- `docs/pipeline/ARCHITECTURE.md` — layer-by-layer implementation structure, GitHub dependencies, module map
- `REMOTION_INTEGRATION.md` — Remotion setup, scene schema v2 (events-based), component guide
- `DAVINCI_WORKFLOW.md` — how to open FCPXML in DaVinci, what to do after import

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

### v1 path (Pillow compositor — slideshow/static frames)

```
Claude.ai Web (browser)
    │  MCP tools
    ▼
CLI App (console)
    ├── Project Manager     ← creates/manages projects and channels
    ├── Voiceover Processor ← espeak-ng → scene_NNN.mp3
    ├── Audio Analyzer      ← ffprobe → timeline.json durations
    ├── Transcriber         ← faster-whisper → timeline.json words[]
    ├── Pillow Compositor   ← SVG assets → PNG frames
    └── FFmpeg Assembler    ← frames + audio → draft.mp4
```

### v2 path (Remotion — event-driven animation)

```
Claude.ai Web (browser)
    │  MCP tools
    ▼
CLI App (console)
    ├── Project Manager     ← creates/manages projects and channels
    ├── Voiceover Processor ← espeak-ng → scene_NNN.mp3
    ├── Audio Analyzer      ← ffprobe → timeline.json durations
    ├── Transcriber         ← faster-whisper → timeline.json words[]
    ├── Remotion Renderer   ← scene_layout.json (events) → scene_NNN.mp4
    └── DaVinci Exporter    ← FCPXML → DaVinci Resolve for final edit
```

Schema version is detected automatically from `scene_layout.json`:
- `scenes[].events` present → **v2** (Remotion)
- `frames[].layers` present → **v1** (Pillow)

Claude controls which path by the schema it submits to `pipeline_submit_scene_layouts`.

---

## Design Philosophy

### No hardcoded tool sequence

The CLI app has no internal workflow engine. It executes individual commands and returns structured responses. **Claude decides what to call next.**

Claude makes this decision based on three sources of information:

1. **Tool descriptions** — every MCP tool has a description that explains its preconditions and purpose.
2. **`instructions` field** — every tool response includes an `instructions` field with explicit guidance: what was done, what state the workspace is in, and what to call next.
3. **`state.json`** — current step and status, written by Claude after each completed step. On reconnect, Claude reads `state.json` to know where to resume.

This means the pipeline can be entered at any point, not just from Step 0.

### Three workflow entry points

**Entry point A — Pre-production (no active project)**

Claude uses Competitor Intelligence and Channel Config tools without any production workspace.
This is research mode: analyzing competitors, building channel DNA, writing skills files.
No `channel` or `scenario` context is required for CI/CH tools.

**Entry point B — Full production (new scenario)**

Claude starts from Step 0 (project resolution) and runs the full pipeline through to Step 6.
`state.json` is written at each step. If the session ends, reconnecting Claude reads `state.json` and continues from the last completed step without repeating work.

**Entry point C — Iteration (existing workspace)**

Claude opens an existing workspace and iterates on specific scenes without re-running the full pipeline.
Examples:
- Re-render one scene after editing its events: `pipeline_update_scene_event` → `pipeline_render_scene`
- Preview a specific moment: `pipeline_preview_scene_event`
- Change voiceover for one scene: re-run voiceover for that scene, rebuild timeline, re-render that scene only

The CLI app supports all three entry points equally. There is no mode switch — Claude simply calls the tools it needs.

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
        ├── images/              ← scene images (v1 path)
        ├── prompts/             ← image generation prompts (v1 legacy path)
        ├── md/                  ← JSON data files (tts_input, timeline, scene_layout, lipsync)
        ├── renders/
        │   ├── scenes/          ← scene_NNN.mp4 (Remotion output for v2)
        │   ├── frames/          ← frame PNGs (Pillow output for v1)
        │   └── previews/        ← spot-check PNGs from pipeline_preview_scene_event
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
3. `pipeline_transcribe_scenes` *(optional but recommended)* — runs faster-whisper per scene, enriches `timeline.json` with word-level timings.

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

`words` — word-level timings from faster-whisper; empty array if transcription was skipped. Claude uses word-level pauses as cut triggers in `dynamic` frame mode and as event timing references in v2 animation design.

Claude receives: cumulative start/end offsets, scene durations, and word timings for visual track planning.

**Gate condition:** Step 4 does not start until Claude confirms it has received and processed the timeline.

---

## Step 4 — Compositing and Frame Generation

With exact timings in hand, Claude designs the visual track and submits a scene layout.

### 4.1 — Asset Management

Claude builds and manages a library of SVG assets (characters, backgrounds, props) stored in `global_assets/` (shared across projects) and `md/project_assets/` (scenario-specific).

Asset IDs follow the v2 format: `{G|P}-{TYPE}-{group:03d}-{seq:03d}-{ROLE}` (e.g. `G-CHR-001-001-BODY`).

**Asset roles:** BASE (reference), BODY, FACE, EYES (character parts), CTX (context/background), PART (asset part), COMP (cached composite), LORA (LoRA trigger), PROP (prop).

Assets carry semantic and emotion tags for search (`pipeline_search_assets` supports role/semantic/emotion/category filters).

---

### 4.2 — Scene Layout Design

Claude calls `pipeline_submit_scene_layouts` with a layout JSON. Two schemas are accepted:

**v1 — frames-based (Pillow compositor, slideshow):**
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

**v2 — events-based (Remotion, animation):**
```json
{
  "_schema_version": "v2",
  "scenes": [
    {
      "scene_id": 1,
      "chapter": "Hook",
      "audio_file": "/abs/path/audio/scene_001.mp3",
      "duration": 8.4,
      "fps": 30,
      "canvas": {"width": 1920, "height": 1080},
      "events": [
        {"time": 0.0, "action": "show", "target": "bg", "component": "background",
         "state": {"color": "#F5F5F5"}},
        {"time": 0.5, "action": "show", "target": "worker1", "component": "stickman",
         "state": {"color": "#FFD700", "emotion": "neutral", "pose": "standing"},
         "position": {"x": 400, "y": 200}},
        {"time": 2.1, "action": "trigger_preset", "target": "worker1", "preset": "shake"},
        {"time": 2.1, "action": "change_state", "target": "worker1",
         "state": {"emotion": "shocked"}},
        {"time": 3.0, "action": "show_text", "target": "caption1",
         "value": "€800/month rent increase", "style": "gut_punch",
         "position": {"x": 700, "y": 500}},
        {"time": 6.0, "action": "hide", "target": "caption1"}
      ]
    }
  ]
}
```

Schema version is auto-detected by the server: `events` key → v2, `layers` key → v1.

Full v2 schema reference: `REMOTION_INTEGRATION.md`.

---

### 4.3 — Rendering

`pipeline_render_frames` routes automatically based on the detected schema:

**v1 path** — Pillow compositor:
- Compiles layout into PNG frames in `renders/frames/`
- SVG assets rasterized via cairosvg
- Composite layers composited by z_index with optional color substitution
- COMP assets cached automatically when `save_as_comp: true`
- Usage counters incremented on each render
- `pipeline_preview_frame` renders a single frame synchronously for fast layout verification

**v2 path** — Remotion:
- Each scene is rendered as a standalone MP4 via `ts-node pipeline/remotion/render.ts`
- Output: `renders/scenes/scene_NNN.mp4`
- Per-scene status written to `md/remotion_status.json`
- Use `pipeline_render_scene` for a single scene or `pipeline_render_all_scenes` for the full run
- Use `pipeline_get_remotion_status` to poll progress
- Use `pipeline_preview_scene_event` for a PNG spot-check at a specific second

**Editing a v2 scene without full re-render:**
- `pipeline_update_scene_event` — modify one event field in-place
- `pipeline_move_event` — shift an event's timing
- `pipeline_list_scene_events` — inspect all events for a scene
- After edits: call `pipeline_render_scene` for that scene only. Other scenes are unaffected.

**Lip sync (v2 only):**
- `pipeline_generate_lipsync` — runs rhubarb-lip-sync on scene audio, writes `md/lipsync_scene_NNN.json`
- Output: phoneme-level mouth shape timings (8 shapes + rest)
- Add `lipsync: true` to a stickman event to use mouth animation

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

**Gate condition (v1):** Step 5 does not start until all frames exist in `renders/frames/` and Claude sends a full-completion signal.

**Gate condition (v2):** Step 5 is skipped. After all scenes are rendered by Remotion, proceed directly to Step 6.

---

## Step 5 — Assembly

### v1 path — FFmpeg preliminary assembly

The CLI app assembles a preliminary synchronized video using FFmpeg.

**Inputs:**
- All images from `renders/frames/frame_{frame_id:04d}.png`
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

### v2 path — skip FFmpeg assembly

Remotion already produced `renders/scenes/scene_NNN.mp4` for every scene.
Do **not** call `pipeline_assemble_scenes` or `pipeline_concat_scenes`.
Proceed directly to `pipeline_export_davinci`.

---

## Step 6 — Final Editing in DaVinci Resolve

After Remotion renders all scenes (v2 path), Claude exports an FCPXML timeline for DaVinci Resolve.

**Tool:** `pipeline_export_davinci(channel, scenario, format="fcpxml")`

**Output:** `renders/<channel>_<scenario>_davinci.fcpxml`

The FCPXML references the Remotion-rendered scene MP4s at `renders/scenes/scene_NNN.mp4` and carries:
- Scene order and durations from `md/timeline.json`
- Chapter names from the scenario as clip names
- Correct frame rate (30fps) and resolution (1920×1080)

**In DaVinci Resolve:**
1. File → Import → Timeline → select `.fcpxml`
2. All scenes appear in timeline in correct order with chapter names
3. Add transitions between scenes (Edit page → Effects → Transitions)
4. Add subtitles if needed (Subtitles track → Auto Caption or manual)
5. Color grade if needed (Color page)
6. Deliver → YouTube 1080p preset

Full workflow reference: `DAVINCI_WORKFLOW.md`.

**Gate condition:** Pipeline complete when `pipeline_export_davinci` returns `ok: true` and the `.fcpxml` file exists on disk. DaVinci Resolve handles everything after this point.

**Implementation:** `pipeline/src/davinci/exporter.py` — pure Python, zero external dependencies. Uses only `xml.etree.ElementTree` and `xml.dom.minidom` from the standard library.

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
| 4 | Compositing / Remotion render |
| 5 | FFmpeg assembly (v1 path only) |
| 6 | DaVinci Resolve export |

---

## Claude.ai Web ↔ CLI App Interface

Claude.ai web connects to the CLI app via **MCP tools** exposed by the CLI app.

The CLI app runs a local MCP server that Claude.ai web can connect to.

**Every tool response includes a top-level `instructions` field** with guidance for Claude on what to do next. Claude reads this field and decides the next call. The app never decides for Claude.

**MCP tools the CLI app exposes (95 total):**

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
| `pipeline_submit_scene_layouts` | 4 | Accept SceneLayout JSON (v1 frames or v2 events) and write `md/scene_layout.json` |
| `pipeline_render_frames` | 4 | Route to Pillow (v1) or Remotion (v2) based on schema; background threading |
| `pipeline_get_render_frames_status` | 4 | Return render progress from `md/render_status.json` |
| `pipeline_list_frames` | 4 | List rendered frame files |
| `pipeline_preview_frame` | 4 | Render a single frame synchronously for layout verification (v1) |
| `pipeline_update_frame_layout` | 4 | Update layers in an existing frame without full resubmit (v1) |
| `pipeline_render_scene` | 4v2 | Render a single scene via Remotion; returns status and output path |
| `pipeline_render_all_scenes` | 4v2 | Render all scenes via Remotion with concurrency control; background job |
| `pipeline_get_remotion_status` | 4v2 | Return per-scene Remotion render progress and ETA |
| `pipeline_stop_render` | 4v2 | Cancel a running Remotion render job |
| `pipeline_update_scene_event` | 4v2 | Modify a single event field in scene_layout without full resubmit |
| `pipeline_move_event` | 4v2 | Shift an event's timing within a scene |
| `pipeline_preview_scene_event` | 4v2 | Render a PNG at a specific time in a scene for spot-check |
| `pipeline_list_scene_events` | 4v2 | Inspect all events for a scene with their current values |
| `pipeline_generate_lipsync` | 4v2 | Run rhubarb-lip-sync on scene audio; write `md/lipsync_scene_NNN.json` |
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
| `pipeline_update_competitor_channel` | CI | Update competitor channel fields (dot notation) |
| `pipeline_get_competitor_channel` | CI | Return a competitor channel record |
| `pipeline_list_competitor_channels` | CI | List all competitor channels |
| `pipeline_add_competitor_video` | CI | Add a competitor video; applies engagement formulas automatically |
| `pipeline_update_competitor_video` | CI | Update competitor video fields (dot notation) |
| `pipeline_get_competitor_video` | CI | Return a competitor video record |
| `pipeline_list_competitor_videos` | CI | List all videos for a competitor channel |
| `pipeline_import_transcript` | CI | Store a transcript for a competitor video |
| `pipeline_get_transcript` | CI | Return stored transcript for a competitor video by video_id |
| `pipeline_add_competitor_index_row` | CI | Add a row to a competitor intelligence index sheet (hooks/thumbnails/pacing/patterns) |
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
| `pipeline_assemble_scenes` | 5 | Build one MP4 clip per scene (frames + audio) into `renders/scenes/` — v1 path only |
| `pipeline_concat_scenes` | 5 | Concatenate scene clips into `renders/<scenario>_draft.mp4` — v1 path only |
| `pipeline_get_render_status` | 5 | Return assembly and concat status from `md/render_status.json` |
| `pipeline_get_output_file` | 5 | Return path, size, and duration of the draft render file |
| `pipeline_export_davinci` | 6 | Generate FCPXML 1.10 timeline from Remotion scenes; writes `renders/<name>_davinci.fcpxml` |

**Step column key:**
- CI = Competitor Intelligence (pre-production, entry point A)
- CH = Channel Config (pre-production, entry point A)
- 4 = Frame generation / registry / analytics (both v1 and v2)
- 4v2 = Remotion animation path only (entry points B and C)
- 5 = FFmpeg assembly (v1 path only)
- 6 = DaVinci export (v2 path only)

**The CLI app never advances the pipeline on its own.** Only Claude calls `pipeline_set_state` to advance steps. The CLI app executes, Claude decides.

---

## What Is NOT In Scope

- The CLI app does not decide which step to run next — Claude does.
- The CLI app does not generate prompts — Claude does.
- The CLI app does not know about channel strategy or scenario content — Claude does.
- LoRA model training (separate tool: `lora-trainer`) is a prerequisite, not part of this pipeline.
- DaVinci Resolve color grading, transitions, and final delivery — handled by the user in DaVinci after FCPXML import.
