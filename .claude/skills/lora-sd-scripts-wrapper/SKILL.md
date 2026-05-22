---
name: lora-sd-scripts-wrapper
description: Use when changing sd-scripts command construction, TrainingConfig, config/default.yaml, optimizer behavior, precision, epochs, rank, or output naming in lora-trainer.
---

# lora-sd-scripts-wrapper

## Command Policy

The wrapper builds an explicit `sdxl_train_network.py` command. Keep flags readable and
ROCm-safe.

Required defaults:

- `--network_module networks.lora`
- `--optimizer_type AdamW`
- `--train_batch_size 1`
- `--cache_latents`
- `--gradient_checkpointing`
- `--save_model_as safetensors`

Forbidden:

- `--xformers`
- `AdamW8bit`
- CUDA-only assumptions

## Validation

For command changes:

- update `TrainingConfig` validation if user input changes
- run or add a dry-run-oriented test
- verify the command still points at local `sd-scripts/sdxl_train_network.py`
