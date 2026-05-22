# Development Notes

This directory is a thin project index. The detailed AI operating rules live in
`.claude/CLAUDE.md` and `.claude/skills/lora-*/SKILL.md`.

## Skill Map

| Skill | Use |
|---|---|
| `lora-dev-guide` | Always load first for project architecture and rules |
| `lora-planning-gate` | Load before code changes |
| `lora-rocm-troubleshooter` | Load for ROCm, PyTorch, GPU, or tokenizer failures |
| `lora-dataset-builder` | Load for dataset/caption changes |
| `lora-sd-scripts-wrapper` | Load for command flags and sd-scripts integration |
