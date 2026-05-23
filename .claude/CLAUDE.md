# lora-trainer — Project Instructions for AI

## What This Project Is

`lora-trainer` is a focused Python 3.10 CLI for SDXL LoRA training on AMD/ROCm Linux.

It is NOT:
- a new training framework
- a generic model-management platform
- an NVIDIA/CUDA training tool

It IS:
- a safe wrapper around `kohya-ss/sd-scripts`
- a ROCm setup and validation helper
- a dataset normalizer for kohya LoRA structure
- a simple path from image folder to `.safetensors`

## Mandatory Skill Loading

This repository contains two related surfaces:

- LoRA trainer CLI: `train.py`, root `src/`, root `config/`, root `tests/`
- Video pipeline MCP server: `pipeline/`, `docs/pipeline/`, `PRODUCTION_PIPELINE.md`

**At the start of every LoRA trainer session, load:**

1. `/lora-dev-guide` — always first
2. One task-specific skill from the table below

**The AI must not write code without loading `lora-dev-guide` and running `lora-planning-gate`.**

**At the start of every video pipeline session, load:**

1. `/pipe-dev-guide` — always first
2. `/pipe-policy-core` — **mandatory second** (constitution: invariants, safety rules, skill tiers)
3. `/pipe-planning-gate` — before any code change
4. One task-specific pipeline skill from the table below

**Pipeline audit files live in `pipeline/audit/` — read them before any pipeline code change.**

### Task → Skill mapping

| Work type | Load |
|---|---|
| Any code change (mandatory gate) | `/lora-planning-gate` |
| ROCm, PyTorch, GPU detection, install, tokenizer failures | `/lora-rocm-troubleshooter` |
| Dataset naming, captions, repeats, image formats | `/lora-dataset-builder` |
| sd-scripts command flags or training config | `/lora-sd-scripts-wrapper` |
| Adding or extending a module in src/ | `/lora-module-builder` |
| Documentation structure, updating memory.md or architecture.md | `/lora-doc-structure` |
| Pydantic entities, config schema, YAML defaults | `/lora-entities-registry` |
| Writing any non-trivial test, scenario matrix | `/lora-test-scenarios` |

### Pipeline Task → Skill mapping

| Work type | Load |
|---|---|
| Any pipeline code change (mandatory gate) | `/pipe-planning-gate` |
| MCP server tools and tool schemas | `/pipe-mcp-tools` |
| Claude.ai connector, OAuth discovery, Cloudflare tunnel, remote tools discovery | `/pipe-claude-connector` |
| TTS/image engine adapters | `/pipe-adapter-pattern` |
| Pydantic entities, `state.json`, YAML config schemas | `/pipe-entities` |
| Pipeline tests or MCP SDK verification | `/pipe-test-patterns` |

### When to Load Each Skill

#### `/lora-module-builder` — load when adding any new file to src/
Load when creating a new Python module in `src/`. Covers: naming rules, Pydantic config placement, wiring into `train.py`, test requirements, and documentation update checklist.

**When NOT needed:** edits within an existing file with no new concerns introduced.

#### `/lora-doc-structure` — load when updating documentation
Load when updating `docs/project/memory.md`, `docs/project/architecture.md`, or creating `docs/development/<feature>.md`. Defines what goes where, writing style, and when to promote development notes to stable project docs.

#### `/lora-entities-registry` — load when touching config or Pydantic models
Load when adding config keys to `config/default.yaml`, creating or modifying Pydantic models in `src/`, or changing how CLI flags override config. Governs the entity-per-file rule and YAML-as-source-of-defaults rule.

#### `/lora-test-scenarios` — load before writing any test
Load whenever writing or updating tests. Defines the Scenario Matrix (`tests/scenarios/MATRIX.md`), `SCN-*` IDs, test layer taxonomy, and the pre-commit checklist.

## Project Quick Facts

- Runtime: Python 3.10 only
- CLI: `train.py`
- Package modules: `src/`
- Config: `config/default.yaml`
- Backend dependency: local `sd-scripts/`
- Project memory: `docs/project/memory.md`
- Session state: `.planning/STATE.md`

## Pipeline Quick Facts

- Pipeline runtime lives under `pipeline/`
- Pipeline server entrypoint: `pipeline/main.py`
- MCP tools live in `pipeline/src/mcp/server.py`
- Local URL for Claude Code: `http://localhost:8765/mcp`
- Claude.ai web URL: `https://<trycloudflare-host>/mcp`, printed by `bash pipeline/start.sh`
- Transport: MCP Streamable HTTP
- Remote connector requires OAuth discovery over the public tunnel
- Verification source of truth: official MCP Python SDK `initialize -> tools/list`, not a bare `GET /mcp`

## Non-Negotiable Rules

1. Do not use `AdamW8bit`; use `AdamW`.
2. Do not install or pass `xformers`.
3. Keep `HSA_OVERRIDE_GFX_VERSION` explicit for ROCm.
4. RDNA 2 override is `10.3.0`; RDNA 3 override is `11.0.0`.
5. Keep SDXL 16GB defaults conservative: batch size 1, cache latents, gradient checkpointing.
6. Patch both SDXL tokenizer constants in sd-scripts during install.
7. Keep modules single-purpose; no `utils.py`, `helpers.py`, or broad grab-bag files.
8. Validate behavior with unit tests or dry-run evidence before calling work complete.

## Pipeline Non-Negotiable Rules

1. Do not use a bare `GET /mcp` as a health check. It can validly return `400 Bad Request: Missing session ID`.
2. Health-check the server with a JSON-RPC `initialize` sent by `POST /mcp`.
3. Claude.ai protected resource metadata for `/mcp` must be available at `/.well-known/oauth-protected-resource/mcp`.
4. `cloudflared` reaches uvicorn from `127.0.0.1`; do not hide OAuth metadata based only on `request.client.host`.
5. Hide OAuth discovery only for direct local `Host: localhost` / `127.0.0.1`, so Claude Code stays non-OAuth.
6. Keep tool input schemas Claude.ai-friendly: simple JSON Schema, string arguments where practical, descriptions on every parameter.
7. After changing MCP auth, tunnel, or tool schemas, remove and re-add the Claude.ai custom integration; hosted Claude may cache connector metadata.
8. A pipeline MCP change is not complete until the official MCP SDK can run `initialize -> tools/list` and see the expected tools.

## Running

```bash
python3.10 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest
python train.py --images ./images --dry-run
```
