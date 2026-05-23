# lora-trainer

An AI-orchestrated video production pipeline. Claude.ai writes scripts and calls 97 MCP tools to produce voiceover, scene animations, and a DaVinci Resolve-ready FCPXML — without any manual intermediate steps.

This is not a media player, a standalone editor, or an AI training tool. It is a Python MCP server that Claude.ai controls.

---

## Quick Start

```bash
# Install Python dependencies
cd pipeline
python -m venv venv
venv/bin/pip install -e ".[dev]"
venv/bin/pip install faster-whisper

# Install Node.js dependencies (Remotion compositor)
cd remotion && npm install && cd ..

# Install system binaries (Fedora)
sudo dnf install espeak-ng ffmpeg

# Start the server
bash pipeline/start.sh
```

`start.sh` prints the local URL (`http://localhost:8765/mcp`) and, if `VIDPIPE_PUBLIC_URL` is set, the public Cloudflare tunnel URL.

Connect Claude Code to `http://localhost:8765/mcp`. For Claude.ai web, see [Connector Setup](docs/pipeline/CONNECT.md).

---

## Documentation

| Doc | What it covers |
|---|---|
| [Pipeline structure](docs/pipeline/reference/PIPELINE_STRUCTURE.md) | Module map, how to add tools, how to swap engines |
| [MCP tool reference](docs/pipeline/reference/MCP_TOOLS.md) | All 97 tools, I/O shapes, state gate rules |
| [Scene layout schema](docs/pipeline/reference/SCENE_LAYOUT_SCHEMA.md) | JSON format for v2 (events-based) scenes |
| [Global assets](docs/pipeline/reference/GLOBAL_ASSETS.md) | Asset library, ID format, SVG character rig |
| [Channels and registry](docs/pipeline/reference/CHANNEL_AND_REGISTRY.md) | Channel DNA, skill files, data registry |
| [Engine profiles](docs/pipeline/reference/ENGINES.md) | TTS and image engine swap guide |
| [Workflow A — Pre-production](docs/pipeline/reference/workflows/ENTRY_A_PREPRODUCTION.md) | New channel setup: DNA, competitors, asset library |
| [Workflow B — Full run](docs/pipeline/reference/workflows/ENTRY_B_FULL_RUN.md) | Scenario to draft MP4, step by step |
| [Workflow C — Iteration](docs/pipeline/reference/workflows/ENTRY_C_ITERATION.md) | Edit without rerunning the full pipeline |
| [DaVinci export](DAVINCI_WORKFLOW.md) | FCPXML → DaVinci Resolve workflow |
| [Architecture](docs/pipeline/ARCHITECTURE.md) | Layer map, module boundaries, data flow |
| [Connector setup](docs/pipeline/CONNECT.md) | Claude.ai OAuth and Cloudflare tunnel setup |

---

## What's Not Included

- Cloud rendering: all computation runs locally on the machine running the pipeline server
- NVIDIA/CUDA: image generation uses AMD/ROCm or CPU (stub adapter by default)
- DaVinci Resolve scripting: resolve-mcp is a separate server, not wrapped in these tools
- Hosted TTS: current engine is local espeak-ng; Kokoro adapter is planned

---

## License

Private project. All rights reserved.
