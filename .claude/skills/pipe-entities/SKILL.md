---
name: pipe-entities
description: Load when adding or modifying Pydantic entities, config schemas, or YAML defaults. Defines entity placement, naming, validation rules, and JSON contract alignment.
---

# pipe-entities

## File Placement

One entity per file. All entities live in `src/entities/`.

| File | Models |
|---|---|
| `project.py` | `ProjectConfig`, `WorkspaceContext` |
| `scenario.py` | `Scene`, `TTSInstruction`, `TTSBatch` |
| `timing.py` | `AudioSegment`, `SceneTiming`, `TimingReport` |
| `prompts.py` | `ImagePrompt`, `PromptBatch` |
| `state.py` | `PipelineState`, `StepStatus` |

Do not create a single `models.py` or `schemas.py` that holds everything.

## Pydantic v2 Rules

- All models inherit from `pydantic.BaseModel`.
- Use `model_config = ConfigDict(strict=True)` for data coming from Claude or external files.
- Use `model_config = ConfigDict(frozen=True)` for config objects that must not be mutated at runtime.
- Every field has an explicit type — no `Any`.
- Optional fields use `Optional[T] = None`, not bare `= None` without a type.

## JSON Contract Alignment

Entity field names must exactly match the JSON schemas defined in `PRODUCTION_PIPELINE.md`.
Do not rename a field for Python style reasons — the JSON contract with Claude is the source of truth.

**Correct:**
```python
class TTSInstruction(BaseModel):
    scene_id: int
    text: str
    tts: TTSParams
```

**Wrong (breaks JSON contract):**
```python
class TTSInstruction(BaseModel):
    scene_id: int
    line_text: str      # renamed — breaks contract
    parameters: TTSParams  # renamed — breaks contract
```

## YAML Config Models

Config models are Pydantic models validated at startup from `config/pipeline.yaml` and `config/engines.yaml`.

```python
class TTSConfig(BaseModel):
    engine: str
    model: str
    voice: str

class ImageConfig(BaseModel):
    engine: str
    provider: str
    model: str

class EnginesConfig(BaseModel):
    tts: TTSConfig
    image: ImageConfig
```

YAML is the single source of truth for defaults. Do not hardcode default values in adapter code.

## State Entity

`PipelineState` in `state.py` is the authoritative shape of `state.json`.
All reads and writes to `state.json` go through this model.

```python
class StepStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    complete = "complete"
    failed = "failed"

class PipelineState(BaseModel):
    channel: str
    scenario: str
    current_step: int
    step_status: StepStatus
    last_updated: datetime
    errors: list[str] = []
```

## Adding an Entity Checklist

- [ ] One new file in `src/entities/` (or add to the correct existing file)
- [ ] All field names match the JSON schema in `PRODUCTION_PIPELINE.md`
- [ ] No `Any` fields
- [ ] Optional fields typed as `Optional[T]`
- [ ] Unit test in `tests/unit/entities/test_<name>.py` that validates a good payload and rejects a bad one
- [ ] If YAML defaults apply: values come from `config/` only, not hardcoded in the model
