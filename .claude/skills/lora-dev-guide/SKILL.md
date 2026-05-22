---
name: lora-dev-guide
description: Always use first when working on lora-trainer. Defines project identity, file map, architecture boundaries, and AMD/ROCm non-negotiables for the LoRA Trainer CLI.
---

# lora-dev-guide

## First Read

Read these before changing behavior:

- `docs/project/memory.md` for stable decisions
- `docs/project/architecture.md` for module boundaries
- `.planning/STATE.md` for current work state

## Architecture Boundaries

| Concern | File |
|---|---|
| CLI flags and terminal output | `train.py` |
| Training config and command assembly | `src/trainer.py` |
| Dataset preparation | `src/dataset.py` |
| Environment checks | `src/validator.py` |
| AMD/ROCm behavior | `src/rocm_utils.py` |
| Defaults | `config/default.yaml` |

Keep each concern in its file. Do not create generic `utils.py` or hide training logic in the CLI.

## AMD Rules

- Python is exactly 3.10.
- ROCm PyTorch is installed from `https://download.pytorch.org/whl/rocm6.3`.
- RDNA 2 uses `HSA_OVERRIDE_GFX_VERSION=10.3.0`.
- RDNA 3 uses `HSA_OVERRIDE_GFX_VERSION=11.0.0`.
- Do not install or use `xformers`.
- Do not use `AdamW8bit`.
- SDXL defaults must remain conservative for 16GB VRAM.

## Completion Evidence

For code changes, provide at least one of:

- focused unit test result
- dry-run command output
- install script shell syntax check
- explicit reason why runtime verification was not possible
