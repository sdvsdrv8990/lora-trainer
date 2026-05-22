---
name: lora-rocm-troubleshooter
description: Use for lora-trainer ROCm, AMD GPU, PyTorch HIP, install.sh, HSA_OVERRIDE_GFX_VERSION, tokenizer patch, or accelerate configuration issues.
---

# lora-rocm-troubleshooter

## Diagnostic Order

1. Confirm Linux and Python 3.10.
2. Check `rocm-smi`.
3. Check PyTorch HIP with `python -c "import torch; print(torch.version.hip)"`.
4. Confirm `HSA_OVERRIDE_GFX_VERSION` for the GPU family.
5. Check `sd-scripts/library/sdxl_train_util.py` tokenizer constants.
6. Check that `xformers` is absent from install and command flags.

## Known Values

- RDNA 2: `HSA_OVERRIDE_GFX_VERSION=10.3.0`
- RDNA 3: `HSA_OVERRIDE_GFX_VERSION=11.0.0`
- ROCm PyTorch index: `https://download.pytorch.org/whl/rocm6.3`
- SDXL tokenizer path: `openai/clip-vit-large-patch14`

## Fix Policy

Prefer explicit failure messages over silent fallback. If auto-detection is uncertain, default to
RDNA 2 and show the user how to pass `--gpu rdna3`.
