# Production Pipeline — Overview

This document describes the end-to-end video production pipeline controlled by Claude AI.
It is an architectural orientation, not a step-by-step guide.
For step-by-step workflows see `docs/pipeline/reference/workflows/`.

## What the Pipeline Does

Takes a topic → produces a finished draft MP4, ready for DaVinci Resolve color grade and delivery.

```
Topic idea
    ↓
Channel DNA + competitor analysis
    ↓
Scenario text (structured tts_input)
    ↓
Voiceover generation (TTS per scene)
    ↓
Timeline (measured audio durations)
    ↓
Transcription (words[] with timestamps)
    ↓
Scene layout (events, characters, assets)
    ↓
Frame render (Pillow v1 or Remotion v2)
    ↓
Scene assembly (frames + audio → MP4 per scene)
    ↓
Concat (all scenes → draft MP4)
    ↓
FCPXML export → DaVinci Resolve
```

## Control Layer

Claude AI controls the pipeline via 95 MCP tools exposed at `http://localhost:8765/mcp`.
Claude does not run code directly — it calls tools and the server executes the work.

Claude advances the pipeline step counter. The server never advances it.
State is tracked in `<workspace>/md/state.json`.

## Three Entry Points

| Entry | When to use | Starting tool |
|---|---|---|
| A — Pre-production | New channel, no assets yet | `pipeline_create_project` |
| B — Full run | Known channel, ready to produce | `pipeline_submit_scenario` |
| C — Iteration | Editing an existing scenario | `pipeline_update_scene_event` |

See `docs/pipeline/reference/workflows/` for detailed guides per entry point.

## Workspace Layout

Every scenario lives in `pipeline/projects/<channel>/<scenario>/`:

```
<workspace>/
├── md/
│   ├── state.json              current pipeline step + status
│   ├── tts_input.json          structured voiceover script
│   ├── timeline.json           scene durations + word timestamps
│   ├── scene_layout.json       all scene events
│   ├── remotion_status.json    render job progress
│   └── lipsync_scene_NNN.json  phoneme cues per speaking scene
├── audio/
│   └── scene_NNN.mp3           generated voiceover per scene
├── images/
│   └── frame_NNNN.png          generated frames
└── renders/
    ├── scenes/
    │   └── scene_NNN.mp4       assembled per-scene video
    ├── <scenario>_draft.mp4    final concat
    └── <scenario>_davinci.fcpxml  DaVinci import file
```

## Source Map

| Layer | Module | Responsibility |
|---|---|---|
| MCP server | `src/mcp/server.py` | 95 tools, input validation, dispatch |
| Project / state | `src/project/` | workspace creation, state.json |
| Scenario | `src/scenario/builder.py` | validates tts_input structure |
| TTS | `src/tts/` | espeak adapter (Kokoro: planned) |
| Audio analysis | `src/audio/analyzer.py` | ffprobe → timeline.json |
| Transcription | `src/audio/transcriber.py` | stable-whisper → words[] |
| Subtitles | `src/audio/subtitle_exporter.py` | SRT/VTT/ASS export |
| Lipsync | `src/audio/lipsync.py` | rhubarb → lipsync JSON |
| Images (v1) | `src/images/` | Pillow compositor, asset library |
| Remotion (v2) | `src/remotion/` + `remotion/` | React/TS renderer (bridge done, TS pending) |
| DaVinci | `src/davinci/exporter.py` | FCPXML 1.10 export |
| Registry | `src/registry.py` | global + project data tables |
| Channel | `src/channel/manager.py` | channel DNA + skill files |
| Competitor | `src/competitor/manager.py` | competitor video analysis |
| Workflow | `src/workflow/instructions.py` | Claude guidance per tool |

## Key Design Rules

- Every MCP tool returns `{"ok": bool, "data": {…}}` — never raises to Claude
- Only Claude advances `current_step` in `state.json`
- Engine swap = `engines.yaml` config change, never code change
- `server.py` dispatches only — no business logic inside
- File paths in tool responses are always absolute

## Related Reference Docs

- [MCP Tool Reference](MCP_TOOLS.md) — all 95 tools
- [Scene Layout Schema](SCENE_LAYOUT_SCHEMA.md) — SceneEvent / SceneLayout JSON
- [Remotion Rendering](REMOTION_RENDERING.md) — React/TS renderer details
- [Kokoro TTS](KOKORO_TTS.md) — planned TTS upgrade
- [DaVinci Workflow](../../DAVINCI_WORKFLOW.md) — FCPXML → Resolve steps
- [Architecture](../ARCHITECTURE.md) — layer diagram
