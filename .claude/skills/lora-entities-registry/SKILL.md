---
name: lora-entities-registry
description: "Rules for Pydantic entities, config registry, and YAML defaults in lora-trainer. Covers: where entities live, config schema patterns, how config/default.yaml is authoritative, and the registry pattern for extending configuration."
---

# lora-entities-registry — Entities and Config Registry Rules

## What This Skill Governs

1. **Pydantic entities** — structured data models used inside src/ modules
2. **Config schema** — `TrainingConfig` and per-module config classes
3. **YAML registry** — `config/default.yaml` as the single source of defaults
4. **Config loading** — how CLI flags, YAML, and defaults merge in `train.py`

---

## Entity Rules

### Where Entities Live

Every structured data class lives in the file that **owns** the concern:

| Entity | File |
|---|---|
| `TrainingConfig` | `src/trainer.py` |
| `DatasetConfig` | `src/dataset.py` |
| `ValidatorResult` | `src/validator.py` |
| `ROCmInfo` | `src/rocm_utils.py` |

**Rule:** Entity declarations are **never copied** to another file. Always import.

```python
# WRONG — redeclaring in train.py
class TrainingConfig(BaseModel): ...

# CORRECT — importing
from src.trainer import TrainingConfig
```

### Entity File Template

```python
# src/<module>.py
from __future__ import annotations
from pydantic import BaseModel, Field
from pathlib import Path


class <Name>Config(BaseModel):
    """Config for <module> — fields match config/default.yaml → <section>."""

    field_name: type = Field(
        default=...,
        description="[What this controls. Units if numeric.]",
    )
```

### Pydantic Validation Rules

- Use `Field(ge=1, le=128)` for numeric constraints (e.g., rank, batch size).
- Use `Field(default_factory=list)` for mutable defaults, never `default=[]`.
- Validate paths with `Path` type, not `str`. Let Pydantic coerce `str → Path`.
- For AMD-specific values, validate in a `@validator` or `model_validator` that calls `rocm_utils`.

---

## YAML Registry — config/default.yaml

`config/default.yaml` is the **single authoritative source** for all defaults. No default value may be hardcoded in Python — put it in YAML and read it.

### Current Structure

```yaml
training:
  optimizer: AdamW           # NOT AdamW8bit (AMD stability)
  rank: 32                   # LoRA rank (16-64 recommended)
  batch_size: 1              # 16GB VRAM limit
  epochs: 20
  gradient_checkpointing: true
  cache_latents: true
  mixed_precision: bf16

dataset:
  repeats: 10
  caption_extension: .txt
  supported_formats: [png, jpg, jpeg, webp]

rocm:
  rdna2_gfx_version: "10.3.0"
  rdna3_gfx_version: "11.0.0"
```

### Adding New Config Keys

When a new module needs config:

1. Add a section to `config/default.yaml`:

```yaml
<module_name>:
  key: value
```

2. Add corresponding `<Name>Config` Pydantic class in `src/<module>.py`.

3. Load it in `train.py` alongside the other config sections:

```python
# In train.py — config loading section
<module>_cfg = <Name>Config(**config.get("<module_name>", {}))
```

4. Override with CLI flags where user needs control.

---

## Config Loading Pattern in train.py

The merge order (highest priority wins):

```
CLI flags > environment variables > config/default.yaml
```

```python
# train.py — correct config loading pattern
import yaml
from pathlib import Path

def load_config(config_path: Path, cli_overrides: dict) -> dict:
    """Load YAML defaults, then apply CLI overrides."""
    defaults = yaml.safe_load(config_path.read_text())
    for key, value in cli_overrides.items():
        if value is not None:  # None means "not provided by user"
            _deep_set(defaults, key, value)
    return defaults
```

---

## Registry Checklist

When adding or modifying an entity:

```
□ Entity class declared in the file that owns its concern
□ Entity NOT redeclared in any other file
□ Default values in config/default.yaml, not hardcoded in Python
□ Pydantic Field() used for every field with a description
□ Numeric constraints expressed with ge=/le= on Field()
□ Mutable defaults use default_factory, not mutable literals
□ config/default.yaml updated when new keys are added
□ train.py updated to load the new config section if needed
□ Validator or dry-run confirms config round-trips correctly
```
