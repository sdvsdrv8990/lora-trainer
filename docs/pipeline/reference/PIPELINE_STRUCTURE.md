# Pipeline Source Map

The pipeline lives entirely under `pipeline/` inside the `lora-trainer` repo.
Everything below `pipeline/` is a Python MCP server, a Node.js Remotion renderer, and supporting data stores.

---

## Directory Tree

```
pipeline/
├── main.py                          CLI entry point (Typer)
├── start.sh                         Launches cloudflared + server; prints public URL
├── pyproject.toml
├── config/
│   ├── pipeline.yaml                Server host/port, base_dir, workspace subdirs
│   ├── engines.yaml                 Active TTS and image engine selection
│   └── image_engines/               Per-profile image engine configs (sd15, sdxl, stub)
├── src/
│   ├── mcp/
│   │   ├── server.py                97 @mcp.tool() definitions — the only MCP entry point
│   │   └── oauth.py                 LocalOAuthProvider for Claude.ai connector
│   ├── entities/
│   │   ├── project.py               ProjectConfig, WorkspaceContext
│   │   ├── scenario.py              Scene, TTSInstruction, TTSBatch
│   │   ├── timing.py                AudioSegment, SceneTiming, TimingReport
│   │   ├── prompts.py               ImagePrompt, PromptBatch
│   │   └── state.py                 PipelineState, StepStatus
│   ├── project/
│   │   ├── manager.py               Workspace creation and resolution (Cases 1–4)
│   │   ├── state.py                 state.json read/write (only module that touches state.json)
│   │   └── config.py                project_config.json read/write
│   ├── scenario/
│   │   └── builder.py               Validates tts_input, writes md/tts_input.json + scenario.txt
│   ├── tts/
│   │   ├── engine.py                Abstract TTSEngine base class + factory function
│   │   ├── jobs.py                  Background voiceover job management
│   │   └── adapters/
│   │       └── espeak.py            espeak-ng adapter (current); Kokoro planned
│   ├── audio/
│   │   ├── analyzer.py              ffprobe → md/timeline.json (scene durations)
│   │   ├── transcriber.py           stable-whisper (faster-whisper backend) → words[] + segments[]
│   │   ├── subtitle_exporter.py     Reads stable_result_scene_NNN.json → SRT/VTT/ASS/TSV/TXT
│   │   ├── lipsync.py               rhubarb-lip-sync wrapper → md/lipsync_scene_NNN.json
│   │   └── audio_import.py          Freesound search + download (two-step import)
│   ├── images/
│   │   ├── engine.py                Abstract ImageEngine base class + factory function
│   │   ├── batch.py                 Image generation loop, md/generation_status.json
│   │   ├── compositor.py            SVG→PNG (CairoSVG) Pillow compositor (v1 path)
│   │   ├── assets.py                Asset library v2: role-suffixed IDs, overuse detection
│   │   ├── layout_store.py          Saves/loads md/scene_layout.json; routes v1/v2 schema
│   │   ├── render_jobs.py           Background Pillow render thread pool (v1 path)
│   │   ├── character_jobs.py        Character PNG generation + status tracking
│   │   ├── engine_profiles.py       Profile switching; persists to config/engines.yaml
│   │   └── adapters/
│   │       ├── stub.py              Placeholder 1×1 PNG (default)
│   │       └── diffusers.py         Local SDXL/Flux via HuggingFace diffusers
│   ├── remotion/
│   │   ├── renderer.py              Python → Node.js bridge (runs Remotion CLI)
│   │   └── render_jobs.py           Async Remotion render job management
│   ├── davinci/
│   │   └── exporter.py              FCPXML 1.10 writer (stdlib xml.etree only)
│   ├── assembly/
│   │   ├── ffmpeg.py                Scene MP4 assembler + concat → draft render
│   │   └── jobs.py                  Background assembly job management
│   ├── registry.py                  global_registry.json + project_registry.json; fcntl locking
│   ├── competitor/
│   │   └── manager.py               Competitor channel/video storage; engagement metrics
│   ├── channel/
│   │   └── manager.py               Channel DNA (channel_config.json) + 5 skill .md files
│   └── workflow/
│       └── instructions.py          50+ instruction templates returned in tool responses
├── remotion/
│   ├── package.json
│   ├── render.ts                    Remotion render entry point (CLI target)
│   └── src/
│       ├── Root.tsx                 Composition root
│       ├── Scene.tsx                Event-driven scene renderer
│       ├── types.ts                 SceneLayout, SceneEvent TypeScript interfaces
│       └── components/
│           ├── Background.tsx       Full-frame background image/color
│           ├── Stickman.tsx         Modular character rig (body, eyes, mouth SVG parts)
│           ├── FloatingText.tsx     Animated text overlays
│           ├── AnimatedNumber.tsx   Animated counter (gut_punch style)
│           └── SpeechBubble.tsx     Dialog bubble component
│       └── presets/                 Animation presets: dramatic_popup, shake, slide_in
├── channels/
│   └── <channel_id>/
│       ├── channel_config.json      Channel DNA — niche, style, narrative rules
│       └── skills/                  5 Claude skill files per channel
├── global_assets/
│   ├── assets_index.json            Global asset registry
│   ├── backgrounds/                 Background images/SVGs
│   ├── characters/
│   │   ├── main/                    Lead character PNG+SVG sets
│   │   └── crowd/                   Crowd character SVG parts (body, eyes, mouth)
│   ├── objects/                     Object SVGs (money, props, etc.)
│   └── speech_bubbles/              Speech bubble SVG templates
├── competitor_intelligence/         Competitor channel/video data store
├── global_registry.json             Cross-project performance and experiment data
└── tests/                           pytest unit and integration tests
```

---

## Module Responsibilities

### `src/project/`
- `manager.py` — resolves workspace path, creates directory tree (`~/projects/videos/<channel>/<scenario>/`)
- `state.py` — **only** module that reads/writes `state.json`; Claude calls `pipeline_set_state` to advance steps
- `config.py` — reads/writes `project_config.json` in the scenario root

### `src/scenario/`
- `builder.py` — validates structured `tts_input` JSON array, writes `md/tts_input.json` and `scenario.txt`

### `src/tts/`
- `engine.py` — abstract `TTSEngine` base class + `get_tts_engine(config)` factory
- `jobs.py` — starts background voiceover generation; polls `md/voiceover_status.json`
- `adapters/espeak.py` — espeak-ng subprocess; reads `md/tts_input.json`, writes `audio/scene_NNN.mp3`

### `src/audio/`
- `analyzer.py` — runs ffprobe on each `audio/scene_*.mp3`, writes `md/timeline.json` with durations
- `transcriber.py` — runs stable-whisper on each scene; enriches `timeline.json` with `words[]` and `segments[]`; saves `md/stable_result_scene_NNN.json`
- `subtitle_exporter.py` — reads `md/stable_result_scene_NNN.json`; exports to `md/subtitles/`; never re-transcribes

### `src/images/`
- `engine.py` — abstract `ImageEngine` + `get_image_engine(config)` factory
- `compositor.py` — Pillow + CairoSVG renderer for v1 (layers-based) layouts
- `layout_store.py` — saves/loads `md/scene_layout.json`; detects `_schema_version` (`v1` or `v2`)
- `assets.py` — manages `global_assets/assets_index.json`; role-suffixed IDs (`G-CHR-001-BODY`)

### `src/remotion/`
- `renderer.py` — invokes Node.js `npx remotion render` for v2 (events-based) layouts
- `render_jobs.py` — manages render jobs; writes `md/remotion_status.json`

### `src/davinci/`
- `exporter.py` — builds FCPXML 1.10 from `md/timeline.json` + scene MP4 paths; writes `renders/<scenario>_davinci.fcpxml`

### `src/assembly/`
- `ffmpeg.py` — builds one MP4 per scene (frames + audio); concatenates to `renders/<scenario>_draft.mp4`
- `jobs.py` — background assembly job management

---

## How to Add a New Tool

1. Add the function to `pipeline/src/mcp/server.py` following the template:
   ```python
   @mcp.tool()
   def pipeline_my_tool(channel: ChannelArg, scenario: ScenarioArg, ...) -> dict:
       """One-sentence description."""
       try:
           ws = _workspace(channel, scenario)
           result = my_module.do_thing(ws, ...)
           return {"ok": True, "data": result, "instructions": ""}
       except Exception as e:
           return {"ok": False, "error": str(e)}
   ```
2. All business logic goes in a module under `src/` — no inline logic in `server.py`.
3. Every parameter needs a `description=` in the `Field()` annotation.
4. Verify: `grep -c "@mcp.tool()" pipeline/src/mcp/server.py` → count must match `pipe-mcp-tools` skill.
5. Run `python -m py_compile pipeline/src/mcp/server.py` to confirm no syntax errors.
6. After server restart: run the MCP SDK `initialize → tools/list` snippet to confirm the new tool appears.

See `pipe-mcp-tools` skill for naming conventions and response shape requirements.

---

## How to Swap a TTS or Image Engine

**TTS:**
1. Edit `pipeline/config/engines.yaml` — change `tts.engine` to the new engine name.
2. Add a new adapter in `pipeline/src/tts/adapters/<name>.py` implementing `TTSEngine.generate()`.
3. Add one `elif` branch in `src/tts/engine.py`'s `get_tts_engine()` factory.
4. No changes to `server.py` or any tool — the factory handles the swap.

**Image engine:**
1. Edit `pipeline/config/engines.yaml` — change `image.profile` to a profile ID.
2. Profile configs live in `pipeline/config/image_engines/<profile_id>.json`.
3. Or use `pipeline_switch_engine_profile` to switch at runtime without editing YAML.

See `pipe-adapter-pattern` skill for full adapter contract details.
