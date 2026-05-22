# lora-trainer

> AI-orchestrated video production pipeline.  
> From script to DaVinci Resolve — fully automated through 93 MCP tools.

[![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python)](https://python.org)
[![Remotion](https://img.shields.io/badge/Remotion-4.0-purple?logo=react)](https://remotion.dev)
[![MCP](https://img.shields.io/badge/MCP-Claude-orange)](https://anthropic.com)
[![License](https://img.shields.io/badge/License-Private-red)]()

---

## What this is

Claude AI acts as director and analyst. The server executes. A written script becomes a structured video project — voiceover, word-level transcription, SVG composition, state-driven animation, and DaVinci Resolve export, all orchestrated through conversation.

Nothing is hardcoded. Every creative decision goes through dialogue and is recorded in structured registries for future analysis.

---

## Architecture

```
Claude Web (director)
        │
        ▼
MCP Server — Python, 93 tools
        │
        ├── TTS ──────────────── espeak-ng → audio/*.mp3
        │                        (target: Kokoro TTS)
        │
        ├── Transcription ─────── faster-whisper → word-level timings
        │
        ├── Asset Library ──────── SVG components + uniqueness scoring
        │                          global_assets/ (characters, objects, sounds)
        │
        ├── Compositor v1 ──────── Pillow + CairoSVG → PNG (fallback)
        │
        ├── Compositor v2 ──────── Remotion (React) → scene_N.mp4
        │                          state-driven, character rig, animation presets
        │
        └── Export ─────────────── FCPXML 1.10 → DaVinci Resolve
```

**Final stage:** DaVinci Resolve handles transitions, color grading, subtitles, and YouTube delivery.

---

## Core systems

### 93 MCP tools

| Layer | Count | Description |
|---|---|---|
| Project | 5 | Workspace creation and management |
| Config | 4 | Channel config, skills, project settings |
| Voiceover | 4 | TTS generation, status, cancellation |
| Transcription | 2 | faster-whisper, word-level timings |
| Assets | 8 | SVG library, search, upload, generate |
| Compositor | 10 | Remotion render, scene events, preview |
| Registry | 10 | Dynamic tables, analytics, experiments |
| Competitors | 11 | Channel analysis, transcripts, insights |
| DaVinci | 1 | FCPXML export |
| Lip sync | 1 | Rhubarb phoneme timings |

### Asset Uniqueness System

Three-level scoring prevents visual repetition across videos:

```
AUS  Asset Uniqueness Score      per asset, across all projects
FES  Fragment Effective Score    per asset, within one video
VUC  Video Uniqueness Coefficient weighted average across all frames

AUS = min(1.0, max(0, 1 − (total_uses − 1) × 0.10) + min(0.25, (variant_count − 1) × 0.05))
FES = AUS × max(0, 1 − uses_in_this_video × 0.15)
VUC = Σ(FES_i × weight_i) / Σ(weight_i)
```

Target: VUC > 0.85 per video. Claude checks scores before building scene layouts and proposes new variants when thresholds are exceeded.

### Hook Engine

Claude applies a 7-module attention model when writing scripts:

```
HOOK → SETUP → STABILITY → DISRUPTION → ESCALATION → PAYOFF → AFTERTASTE
```

Reset points placed every 12–15 seconds. Reward type selected per project (educational / story / entertainment / visual_loop). Closing comment-bait always structured as two clear camps.

### Remotion Compositor

State-driven animation — Claude describes events, Remotion renders frames:

```json
[
  { "time": 0.0,  "action": "show",            "target": "background"                         },
  { "time": 1.2,  "action": "show",            "target": "worker",  "state": {"emotion": "neutral"} },
  { "time": 2.8,  "action": "change_state",    "target": "worker",  "state": {"emotion": "shocked"} },
  { "time": 3.5,  "action": "trigger_preset",  "preset": "dramatic_popup"                     },
  { "time": 4.0,  "action": "show_number",     "value": 3800,       "style": "gut_punch"      }
]
```

Character rig with modular SVG parts (body poses, eye states, mouth shapes). Animation presets use Remotion's built-in `spring()` and `interpolate()`.

### Content Intelligence Tables

Per-scenario registries with 8 sheets, master registry aggregates across all episodes:

```
overview      production metadata and status
structure     Hook Engine data — modules, reset points, reward type
chapters      per-chapter breakdown with fact references
key_data      every fact with source and verification status
emotion_map   emotional arc mapped to timestamps
production    step-by-step production status
assets        FES scores per asset used
performance   YouTube metrics after publish
```

### Channel Intelligence

Every channel gets:
- `channel_config.json` — visual style, narrative rules, frame triggers, uniqueness thresholds
- `skills/` — Claude skill files: SCENARIO_WRITER, HOOK_ENGINE, IMAGE_PROMPTS, FRAME_RULES, CHANNEL_VOICE
- Competitor registry — transcript-based structure deconstruction, hook pattern analysis, CTR/retention correlation

---

## Stack

**Python (MCP server)**
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — word-level transcription
- [Pillow](https://python-pillow.org) — compositor v1 fallback
- [CairoSVG](https://cairosvg.org) — SVG rendering
- [ffmpeg-python](https://github.com/kkroening/ffmpeg-python) — audio analysis
- [pydantic v2](https://docs.pydantic.dev) — schema validation

**Node.js (Remotion)**
- [remotion](https://remotion.dev) — core framework
- [@remotion/renderer](https://www.remotion.dev/docs/renderer) — server-side rendering

**Binaries**
- [espeak-ng](https://github.com/espeak-ng/espeak-ng) — current TTS engine
- [ffmpeg](https://ffmpeg.org) — audio/video processing
- [rhubarb-lip-sync](https://github.com/DanielSWolf/rhubarb-lip-sync) — phoneme timings

---

## Project structure

```
pipeline/
├── src/
│   ├── mcp/server.py           93 MCP tool definitions
│   ├── audio/
│   │   ├── tts/                espeak adapter + tone fallback
│   │   ├── transcriber.py      faster-whisper wrapper
│   │   └── lipsync.py          rhubarb wrapper
│   ├── images/
│   │   ├── compositor.py       Pillow compositor (v1)
│   │   ├── adapters/           stub + diffusers adapters
│   │   └── layout_store.py     v1/v2 schema routing
│   ├── remotion/
│   │   ├── renderer.py         Python → Node.js bridge
│   │   └── render_jobs.py      async job management
│   ├── davinci/
│   │   └── exporter.py         FCPXML 1.10, stdlib only
│   └── registry.py             global + project registries
├── remotion/
│   └── src/
│       ├── Scene.tsx           event-driven renderer
│       ├── components/         Background, Stickman, FloatingText, AnimatedNumber, SpeechBubble
│       └── presets/            dramatic_popup, shake, slide_in
├── channels/                   channel configs + skill files
├── global_assets/              SVG library — characters, objects, sounds
├── global_registry.json        cross-project asset scoring + analytics
└── config/
    ├── engines.yaml            active model profiles
    └── image_engines/          sd15, sdxl, stub profiles
```

---

## Production workflow

```
1. Intelligence gathering
   Competitor analysis + own performance data → inform script decisions

2. Script
   Claude writes using channel skills
   Hook Engine model applied — structure recorded in registry

3. Voiceover
   pipeline_start_voiceover → audio/*.mp3

4. Transcription
   pipeline_transcribe_scenes → word-level timings in timeline.json

5. Scene layout
   Claude proposes event timeline, user reviews and approves
   pipeline_submit_scene_layouts → scene_layout.json (v2 events schema)

6. Render
   pipeline_render_all_scenes → Remotion → renders/scenes/*.mp4

7. DaVinci export
   pipeline_export_davinci → FCPXML
   DaVinci Resolve: transitions, subtitles, color grade → YouTube
```

---

## Current status

| Component | Status |
|---|---|
| Python MCP server — 93 tools | ✅ |
| faster-whisper transcription | ✅ |
| Remotion v2 compositor | ✅ |
| DaVinci FCPXML export | ✅ |
| Asset uniqueness system (AUS/FES/VUC) | ✅ |
| Competitor intelligence | ✅ |
| Channel skills system | ✅ |
| Rhubarb lip sync | 🔧 binary install required |
| Kokoro TTS adapter | 📋 planned |
| Character full rig | 📋 in progress |

---

## Install

```bash
# Python
cd pipeline
python -m venv venv
venv/bin/pip install -e ".[dev]"
venv/bin/pip install faster-whisper

# Node.js
cd remotion
npm install

# System (Fedora)
sudo dnf install espeak-ng ffmpeg

# Rhubarb lip sync — download binary:
# https://github.com/DanielSWolf/rhubarb-lip-sync/releases
```

---

## License

Private project. All rights reserved.
