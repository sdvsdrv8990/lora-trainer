# Project Memory — lora-trainer

## Identity

`lora-trainer` is a focused CLI wrapper for AMD/ROCm LoRA training on Linux. It should feel
like a practical training tool, not a general ML framework.

## Stable Decisions

- Use Python 3.10 exactly because ROCm PyTorch wheels are version-sensitive.
- Use `kohya-ss/sd-scripts` as the training backend.
- Use `click`, `rich`, `pydantic`, and `pyyaml` for the local CLI surface.
- Keep sd-scripts cloned as a runtime dependency in `./sd-scripts`.
- Patch both SDXL tokenizer constants to `openai/clip-vit-large-patch14`.
- Keep AMD-specific decisions in `src/rocm_utils.py`.
- Keep dataset shaping in `src/dataset.py`.
- Keep command assembly and training execution in `src/trainer.py`.
- Keep environment preflight checks in `src/validator.py`.

## Architecture Rule

Every module owns one concern. Avoid `utils.py`, broad helper files, and hidden side effects.
Configuration defaults live in `config/default.yaml`; runtime overrides come from CLI flags.

## User Promise

The happy path is:

```bash
python train.py --images ./images --name my_lora --trigger my_style
```

The output should be a `.safetensors` file in `./output`.
