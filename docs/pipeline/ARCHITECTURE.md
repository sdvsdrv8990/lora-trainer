# Pipeline App — Implementation Architecture

## What This Document Is

Layer-by-layer implementation blueprint for the video production pipeline CLI app.
Covers: directory structure, module responsibilities, GitHub dependencies per layer, data contracts, and non-negotiable rules.

This document is consumed by all development skills (`pipe-*`) as the ground truth for implementation decisions.

---

## GitHub Dependencies by Layer

| Layer | Responsibility | Library | Repo | License |
|---|---|---|---|---|
| Config & Entities | Validation, serialization | `pydantic` v2 | pydantic/pydantic | MIT |
| Config & Entities | YAML config files | `pyyaml` | yaml/pyyaml | MIT |
| MCP Server | Claude.ai ↔ CLI protocol | `mcp` (official SDK) | modelcontextprotocol/python-sdk | MIT |
| CLI | Entry point, console UI | `typer` + `rich` | tiangolo/typer, Textualize/rich | MIT |
| TTS | Voice synthesis (current) | `espeak-ng` | — | GPL |
| Audio Analysis | Duration measurement | `ffmpeg` (subprocess) | — | — |
| Audio Analysis | Word-level timestamps | `faster-whisper` | SYSTRAN/faster-whisper | MIT |
| Image Generation | Pipeline scaffold + stubs | built-in | — | — |
| Image Generation | Local SDXL / Flux inference | `diffusers` | huggingface/diffusers | Apache 2.0 |
| Video Assembly | Preliminary render | `ffmpeg-python` | kkroening/ffmpeg-python | Apache 2.0 |
| DaVinci Resolve | Final export | DaVinci Python API | BlackmagicDesign (official) | Proprietary |

---

## Directory Structure

```
pipeline/                        ← project root (inside lora-trainer/)
├── main.py                      ← CLI entry point (Typer app)
├── pyproject.toml
├── config/
│   ├── pipeline.yaml            ← step defaults, output paths, gate behavior
│   └── engines.yaml             ← TTS engine + image engine selection
├── src/
│   ├── mcp/
│   │   └── server.py            ← MCP server — exposes pipeline_* tools to Claude.ai
│   ├── project/
│   │   ├── manager.py           ← workspace resolution, directory creation (Cases 1–4)
│   │   └── state.py             ← state.json read/write, step advancement
│   ├── scenario/
│   │   └── builder.py           ← validates scenario, builds tts_input.json per scene
│   ├── tts/
│   │   ├── engine.py            ← abstract TTSEngine base class
│   │   └── adapters/
│   │       └── espeak.py        ← espeak-ng TTS adapter (current); Kokoro planned — see KOKORO_INTEGRATION.md
│   ├── audio/
│   │   ├── analyzer.py          ← ffprobe → md/timeline.json (durations)
│   │   └── transcriber.py       ← faster-whisper → enriches timeline.json words[]
│   ├── images/
│   │   ├── engine.py            ← abstract ImageEngine base class
│   │   ├── batch.py             ← generation loop, md/generation_status.json
│   │   └── adapters/
│   │       ├── stub.py          ← placeholder 1×1 PNG (default until real engine ready)
│   │       ├── diffusers.py     ← local SDXL/Flux via HuggingFace diffusers (planned)
│   │       └── api.py           ← generic HTTP API adapter (planned)
│   ├── assembly/
│   │   └── ffmpeg.py            ← reads timeline.json + image_prompts.json, assembles scenes, concat → renders/<name>_draft.mp4
│   ├── davinci/
│   │   └── exporter.py          ← DaVinci Resolve Python scripting API, timeline build + export
│   └── entities/
│       ├── project.py           ← ProjectConfig, WorkspaceContext
│       ├── scenario.py          ← Scene, TTSInstruction, TTSBatch
│       ├── timing.py            ← AudioSegment, SceneTiming, TimingReport
│       ├── prompts.py           ← ImagePrompt, PromptBatch
│       └── state.py             ← PipelineState, StepStatus
└── tests/
    ├── unit/                    ← per-module unit tests, no real engines
    └── integration/             ← tests with real FFmpeg, real TTS, real image gen
```

---

## Module Responsibilities

### `src/mcp/server.py`
- Exposes exactly the tools defined in `PRODUCTION_PIPELINE.md §CLI App Interface`.
- Each tool maps 1:1 to a pipeline step action.
- Tools only execute; they never decide which step to run next — Claude does.
- Every tool returns a structured JSON response: `{"ok": true, "data": {...}}` or `{"ok": false, "error": "..."}`.

### `src/project/manager.py`
- Implements Cases 1–4 from Step 0.
- Creates directory trees matching the structure in Step 1.
- Never overwrites existing content; only creates missing directories.

### `src/project/state.py`
- Single source of truth for `state.json`.
- Only Claude (via `pipeline_set_state`) may advance the step.
- On crash resume: reads current step and status; app re-enters from last completed step.

### `src/scenario/builder.py`
- Accepts a confirmed scenario from Claude (list of scenes with text).
- Writes `md/tts_input.json` in the format defined in Step 2.2.
- Validates: no empty `text` fields, no missing `scene_id`s, valid TTS field types.

### `src/tts/engine.py`
- Abstract base class `TTSEngine` with method `generate(scene: TTSInstruction) -> Path`.
- Concrete adapters registered via `engines.yaml → tts_engine` key.
- Factory function `get_tts_engine(config) -> TTSEngine` — single instantiation point.

### `src/audio/analyzer.py`
- Reads all `audio/scene_<NNN>.mp3` files.
- Uses ffprobe (subprocess) for exact per-scene duration.
- Writes `md/timeline.json` with cumulative start/end offsets and empty `words: []`.

### `src/audio/transcriber.py`
- Reads `md/timeline.json` and all scene audio files.
- Runs `faster-whisper` per scene to get word-level timestamps.
- Timestamps are absolute (scene offset + whisper relative time).
- Writes enriched `md/timeline.json` with `words[]` populated.

### `src/images/engine.py`
- Abstract base class `ImageEngine` with method `generate(prompt: FramePrompt, output_dir: Path) -> Path`.
- Factory `get_image_engine(config) -> ImageEngine` — reads `engines.yaml → image.engine`.
- Engine selected via `engines.yaml → image.engine` key. Default: `stub`.

### `src/images/adapters/stub.py`
- Placeholder adapter: writes a 1×1 black PNG for each frame.
- Used for end-to-end pipeline testing without a real image generator.

### `src/images/batch.py`
- `generate(workspace, engine, batch_id)` — runs engine per frame, saves `images/frame_{frame_id:04d}.png`.
- Tracks progress in `md/generation_status.json`.
- `read_status(workspace)` — returns current generation status.
- `list_images(workspace)` — returns per-frame existence check.

### `src/assembly/ffmpeg.py`
- `assemble_scenes(workspace)` — reads `md/timeline.json` + `md/image_prompts.json`, builds one MP4 per scene in `renders/scenes/`.
- `concat_scenes(workspace)` — concatenates scene clips into `renders/<scenario_name>_draft.mp4`.
- `read_render_status(workspace)` / `get_output_file(workspace)` — status and final path queries.
- Tracks progress in `md/render_status.json`.

### `src/davinci/exporter.py`
- Connects to running DaVinci Resolve instance via Python scripting API.
- Builds a new timeline from the draft render and per-scene timing data.
- Applies subtitles from timing_report segments.
- Triggers final export to `final/<scenario_name>.mp4`.

---

## Data Flow

```
Claude.ai Web
    │ scenario text (confirmed)
    ▼
scenario/builder.py ──► md/tts_input.json
    │
    ▼
tts/adapters/espeak.py ──► audio/scene_NNN.mp3 (one per scene)
    │
    ▼
audio/analyzer.py ──► md/timing_report.json
    │
    ▼
Claude.ai Web (receives timing report)
    │ prompt batch JSON
    ▼
images/batch.py ──► images/adapters/*.py ──► images/scene_NNN.png
    │  (loop until all scenes done)
    ▼
assembly/ffmpeg.py ──► renders/<name>_draft.mp4
    │
    ▼
davinci/exporter.py ──► final/<name>.mp4
```

---

## Engine Config Contract

Both TTS and image engines are driven by `config/engines.yaml`.

```yaml
tts:
  engine: espeak          # current working engine
  target_engine: kokoro   # planned — see KOKORO_INTEGRATION.md
  model: espeak-ng
  voice: ru

image:
  engine: diffusers
  provider: local
  model: stabilityai/stable-diffusion-xl-base-1.0
```

Swapping an engine = changing `engine:` key + relevant fields. No code changes.

---

## Non-Negotiable Rules

1. **Single responsibility per module.** No `utils.py`, no grab-bag files.
2. **Adapters are the only place with engine-specific code.** `engine.py` holds only the abstract base class.
3. **The CLI app never advances pipeline state.** Only Claude calls `pipeline_set_state`.
4. **All JSON output formats must match the schemas in `PRODUCTION_PIPELINE.md` exactly.** No renaming fields.
5. **Swapping TTS or image engine requires only config changes, never code changes.**
6. **Every MCP tool returns `{"ok": bool, ...}` — never raise an uncaught exception to Claude.**
7. **`state.json` is always written before returning from any pipeline step.** Crash safety is not optional.
8. **DaVinci integration uses the official Python scripting API only.** No subprocess + AppleScript or CLI hacks.
