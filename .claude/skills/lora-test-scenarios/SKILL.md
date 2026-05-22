---
name: lora-test-scenarios
description: "Mandatory test scenario rules for lora-trainer. Defines the Scenario Matrix (tests/scenarios/MATRIX.md), SCN-* IDs, test layer taxonomy (user scenario → module contract → unit invariant), and update policies. Load before writing any test."
---

# lora-test-scenarios — Test Scenario Rules

> **When to load:** Before writing or updating any test.

---

## Scenario Matrix Contract

All test scenarios are tracked in `tests/scenarios/MATRIX.md`.

This file is:
- Committed to version control
- Append-only (no deletion, only deprecation)
- The source of truth for "what does this codebase actually guarantee?"

### Scenario ID Format

`SCN-<PREFIX>-<NNN>`

| Prefix | Module/Concern |
|---|---|
| `TRAIN` | `src/trainer.py` — command assembly, subprocess launch |
| `DATA` | `src/dataset.py` — dataset prep, image/caption structure |
| `VALID` | `src/validator.py` — environment preflight checks |
| `ROCM` | `src/rocm_utils.py` — GPU detection, GFX version override |
| `CLI` | `train.py` — CLI flags, option parsing, output |
| `CFG` | `config/default.yaml` — config loading, overrides, Pydantic validation |
| `INTG` | Cross-module end-to-end (dry-run) |

IDs are never reused. After deprecation, the row stays with `status: deprecated`.

---

## Test Layer Taxonomy

Write tests at the lowest layer that gives useful signal. Higher layers are for integration only.

| Layer | What it tests | Pytest marker | Example |
|---|---|---|---|
| **Unit invariant** | One function, mocked I/O | `@pytest.mark.unit` | `test_rocm_gfx_version_rdna2()` |
| **Module contract** | One module's public interface, temp files | `@pytest.mark.module` | `test_dataset_creates_kohya_structure()` |
| **Integration / dry-run** | Multiple modules, no GPU required | `@pytest.mark.integration` | `test_train_dry_run_full_pipeline()` |

**AMD hardware tests** (require a GPU): mark `@pytest.mark.hardware` and skip in CI.

---

## MATRIX.md Row Schema

Each scenario is one row. Required fields:

| Field | Description |
|---|---|
| `scenario_id` | `SCN-<PREFIX>-<NNN>` |
| `user_intent` | Real user goal, not a function name |
| `module` | Which `src/` file is under test |
| `expected_contract` | Observable behavior that must remain true |
| `failure_modes` | Invalid input, missing env, bad path, OOM flag |
| `anti_hardcode_risks` | Paths, version strings, magic numbers to parameterize |
| `test_files` | Which test files cover this scenario |
| `update_policy` | `update` / `create` / `deprecate` / `merge` |
| `status` | `active` / `deprecated` |

---

## MATRIX.md Format Example

```markdown
# lora-trainer — Test Scenario Matrix

## SCN-ROCM-001

- **User intent:** Detect RDNA 2 GPU and set correct HSA override
- **Module:** `src/rocm_utils.py`
- **Expected contract:** `detect_gfx_version()` returns `"10.3.0"` for RDNA 2 hardware
- **Failure modes:** No GPU found (return None); unknown GFX family (return None with warning)
- **Anti-hardcode risks:** GFX version strings must come from `config/default.yaml`, not literals
- **Test files:** `tests/test_rocm_utils.py::test_gfx_version_rdna2`
- **Update policy:** update if ROCm adds new GFX families
- **Status:** active

## SCN-DATA-001

- **User intent:** Prepare an image folder into kohya-compatible structure
- **Module:** `src/dataset.py`
- **Expected contract:** Output dir contains `{repeats}_{trigger}/` with images and .txt files
- **Failure modes:** Non-image files are skipped; no images found raises clear error
- **Anti-hardcode risks:** Trigger word and repeats count must come from config, not hardcoded
- **Test files:** `tests/test_dataset.py::test_dataset_creates_kohya_structure`
- **Update policy:** update if kohya changes expected layout
- **Status:** active
```

---

## Update Policy Semantics

| Policy | When to use |
|---|---|
| `update` | Requirements for an existing scenario changed; modify the row in place |
| `create` | New scenario with no prior analog; add a new row |
| `deprecate` | Scenario no longer valid; set `status: deprecated` with reason; do not delete |
| `merge` | Two scenarios test the same path; collapse into one, deprecate the redundant one |

---

## Test File Template

```python
# tests/test_<module>.py
"""Tests for src/<module>.py — scenarios: SCN-<PREFIX>-NNN, ..."""

import pytest
from pathlib import Path
from src.<module> import <ClassName>, <Config>


@pytest.mark.unit
def test_<behavior>():
    """SCN-<PREFIX>-NNN: [user intent from matrix]"""
    # arrange
    ...
    # act
    result = ...
    # assert
    assert result == expected


@pytest.mark.module
def test_<behavior>_with_real_files(tmp_path):
    """SCN-<PREFIX>-NNN: [scenario using temp filesystem]"""
    (tmp_path / "image.png").write_bytes(b"...")
    ...


@pytest.mark.hardware
def test_gpu_detection():
    """SCN-ROCM-NNN: requires real AMD GPU — skip in CI."""
    ...
```

---

## Pre-Commit Test Checklist

Before marking any work complete:

```
□ tests/scenarios/MATRIX.md updated — new scenarios added, existing ones updated
□ Scenario IDs assigned (SCN-<PREFIX>-NNN)
□ Each test function references its SCN-* ID in the docstring
□ Unit and module tests pass: python3.10 -m pytest tests/ -v -m "unit or module"
□ Dry-run integration test passes: python3.10 -m pytest tests/ -v -m integration
□ No hardcoded paths, version strings, or magic numbers in tests
□ Anti-hardcode risks from MATRIX.md row are parameterized in the test
```

---

## Running Tests

```bash
# All non-hardware tests
python3.10 -m pytest tests/ -v -m "not hardware"

# One layer only
python3.10 -m pytest tests/ -v -m unit
python3.10 -m pytest tests/ -v -m module
python3.10 -m pytest tests/ -v -m integration

# Single file
python3.10 -m pytest tests/test_dataset.py -v
```
