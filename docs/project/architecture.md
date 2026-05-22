# Architecture

## Execution Flow

```text
CLI flags
  -> TrainingConfig validation
  -> EnvironmentValidator preflight
  -> DatasetPreparer kohya dataset
  -> LoraTrainer command assembly
  -> sd-scripts training process with ROCm env
```

## Modules

| File | Responsibility |
|---|---|
| `train.py` | User-facing Click CLI and Rich output |
| `src/trainer.py` | Validated config, sd-scripts command assembly, subprocess launch |
| `src/dataset.py` | Image discovery, normalized copy, caption creation |
| `src/validator.py` | Linux, Python 3.10, ROCm PyTorch, sd-scripts checks |
| `src/rocm_utils.py` | AMD GPU family detection and ROCm environment variables |
| `config/default.yaml` | Conservative SDXL LoRA defaults |

## Non-Negotiables

- `AdamW8bit` is rejected.
- `xformers` is not part of the install or command.
- ROCm PyTorch comes from `https://download.pytorch.org/whl/rocm6.3`.
- SDXL tokenizer patch touches both `TOKENIZER1_PATH` and `TOKENIZER2_PATH`.
- Dataset output follows `{repeats}_{trigger}/image.ext` plus matching `.txt`.
