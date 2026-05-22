---
name: lora-module-builder
description: "Protocol for adding or extending a module in lora-trainer/src/. Covers: when to create a new file, naming rules, Pydantic model placement, wiring into train.py, and the completion checklist. Load lora-dev-guide and lora-planning-gate first."
---

# lora-module-builder — Module Creation Protocol

> **Prerequisites:** Load `lora-dev-guide` and complete `lora-planning-gate` before starting.
> A plan must be approved before any file is created.

---

## Architecture Map

```
lora-trainer/
├── train.py                ← CLI only — click options, rich output, calls src/*
├── src/
│   ├── trainer.py          ← Command assembly + subprocess execution
│   ├── dataset.py          ← Image/caption preparation for kohya structure
│   ├── validator.py        ← Pre-flight environment checks (ROCm, GPU, paths)
│   └── rocm_utils.py       ← AMD GFX version detection, HSA_OVERRIDE env var
├── config/
│   └── default.yaml        ← Training defaults (batch, rank, optimizer, etc.)
└── tests/
    └── scenarios/
        └── MATRIX.md       ← Scenario matrix (see lora-test-scenarios)
```

---

## When to Create a New File in src/

Create a new `src/<name>.py` only when the concern is **genuinely separate** from all existing files:

| New concern | Correct file name |
|---|---|
| LoRA merge / weight averaging | `src/merger.py` |
| Output file naming and packaging | `src/packager.py` |
| sd-scripts version management | `src/scripts_manager.py` |
| Caption auto-generation (BLIP, WD14) | `src/captioner.py` |
| Progress reporting / callback | `src/progress.py` |

**Never:**
- Add `src/utils.py` or `src/helpers.py` — every file must have a purpose name.
- Move AMD logic out of `rocm_utils.py` into another file.
- Move CLI logic out of `train.py` into `src/`.
- Add a 6th concern to an existing 5-concern file to avoid creating a new one.

---

## Step-by-Step Protocol

### Step 0: Name the Module

Choose the filename before writing code.
Ask: "What does this file do?" — the answer must map directly to the filename.

- `dataset.py` → prepares datasets
- `validator.py` → validates the environment
- `trainer.py` → runs the training

### Step 1: Define the Pydantic Config Model (if needed)

If the module takes structured config from `config/default.yaml`, define its model in the file itself — not in a separate `models.py` or `types.py`.

```python
# src/<name>.py
from __future__ import annotations
from pydantic import BaseModel, Field

class <Name>Config(BaseModel):
    """Config for <Name> — fields come from config/default.yaml."""
    field: type = Field(default=..., description="...")
```

Then add the corresponding section to `config/default.yaml`:

```yaml
<name>:
  field: value
```

And load it in `train.py` by extending the config loading section (see `config/default.yaml` loading pattern in `train.py`).

### Step 2: Implement the Module

```python
# src/<name>.py
"""<ClassName> — <one-line purpose statement>."""

from __future__ import annotations
from pathlib import Path
import structlog  # if you need logging

log = structlog.get_logger(__name__)


class <ClassName>:
    """[What this class does in one sentence.]"""

    def __init__(self, config: <Name>Config) -> None:
        self.config = config

    def <verb>_<noun>(self, ...) -> <ReturnType>:
        """[What this returns and when to call it.]"""
        ...
```

**File rules:**
- No cross-module imports except: `rocm_utils` is importable by all; `trainer.py` imports from all others.
- No subprocess calls outside `trainer.py`.
- No AMD/GPU logic outside `rocm_utils.py`.
- No CLI flag parsing outside `train.py`.

### Step 3: Wire into train.py

In `train.py`, add the import and call site in the correct phase:

| Phase | Where in train.py |
|---|---|
| Validation (before everything) | Before `TrainingConfig` is built |
| Dataset prep | After validation, before `Trainer.run()` |
| Training | Inside `Trainer.run()` only |
| Post-processing | After `Trainer.run()` returns |

### Step 4: Write Tests

Create `tests/test_<name>.py`. See `lora-test-scenarios` for scenario matrix rules.

Minimum test coverage for a new module:

```python
# tests/test_<name>.py
import pytest
from pathlib import Path
from src.<name> import <ClassName>, <Name>Config

def test_<class>_<expected_behavior>(tmp_path):
    """[What this test verifies.]"""
    cfg = <Name>Config(...)
    obj = <ClassName>(cfg)
    result = obj.<verb>_<noun>(...)
    assert result == expected

def test_<class>_rejects_invalid_input():
    """Verify <ClassName> raises on invalid input."""
    with pytest.raises(<Error>):
        ...
```

Run:
```bash
python3.10 -m pytest tests/test_<name>.py -v
```

### Step 5: Update Documentation

**Required:**
- `docs/project/architecture.md` — add row to the concern table
- `docs/project/memory.md` — add stable decision if one was made

**Optional (for non-trivial modules):**
- `docs/development/<name>.md` — design rationale, data flow, extension points

---

## Module Completion Checklist

```
□ Filename describes a single concern
□ Pydantic config model defined in the file (if applicable)
□ config/default.yaml updated (if new config keys added)
□ No subprocess calls outside trainer.py
□ No AMD/GPU logic outside rocm_utils.py
□ No CLI logic outside train.py
□ Imported and wired into train.py at the correct phase
□ Tests written and passing: python3.10 -m pytest tests/test_<name>.py -v
□ docs/project/architecture.md updated
□ docs/project/memory.md updated if a stable decision was made
□ lora-test-scenarios: MATRIX.md entry added for each new scenario
```
