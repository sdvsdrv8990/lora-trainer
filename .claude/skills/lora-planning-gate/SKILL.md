---
name: lora-planning-gate
description: Use before any lora-trainer code change. Forces a small plan, scope lock, risk check, and evidence target before editing files.
---

# lora-planning-gate

Before editing, write a short internal plan with:

1. Goal
2. Files expected to change
3. Risk area: ROCm install, sd-scripts flags, dataset mutation, CLI behavior, or docs only
4. Validation command

## Scope Rules

- Keep changes near the requested concern.
- Avoid changing installer and runtime behavior in the same pass unless the task requires both.
- Preserve the simple user path: `python train.py --images ./images`.
- Update `docs/project/memory.md` when a stable project decision changes.

## Evidence Rules

- Dataset changes need tests against a temporary image folder.
- ROCm override changes need tests for RDNA 2 and RDNA 3 values.
- CLI option changes need `--help` or `--dry-run` verification.
- Installer changes need `bash -n install.sh`.
