---
name: pipe-adapter-pattern
description: Load when writing or modifying TTS or image engine adapters. Defines the abstract base class pattern, config binding, factory function, and swappability rules.
---

# pipe-adapter-pattern

## The Pattern

Every swappable engine (TTS, image generation) follows the same three-file structure:

```
src/<domain>/
    engine.py          ← abstract base class only
    adapters/
        <name>.py      ← one file per concrete engine
```

A factory function in `engine.py` reads the config and returns the correct adapter instance.

## Abstract Base Class Rules

- Defined in `engine.py` using `abc.ABC` and `abc.abstractmethod`.
- Contains only the interface: method signatures + docstrings.
- Never imports from `adapters/`.
- Never contains engine-specific logic.

**TTS base class contract:**
```python
class TTSEngine(ABC):
    @abstractmethod
    def generate(self, scene: TTSInstruction) -> Path:
        """Generate audio for one scene. Returns path to the audio file."""
```

**Image engine base class contract:**
```python
class ImageEngine(ABC):
    @abstractmethod
    def generate(self, prompt: ImagePrompt) -> Path:
        """Generate one image. Returns path to the image file."""
```

## Adapter Rules

- One file per engine in `adapters/`.
- Adapter imports only from `entities/` and the engine's own SDK.
- Adapter never reads config directly — receives a config object from the factory.
- Adapter never knows about `state.json`, MCP, or other pipeline concerns.
- Adapter never raises bare exceptions — wraps errors in domain-specific exceptions.

**Adapter file template:**
```python
from src.tts.engine import TTSEngine
from src.entities.scenario import TTSInstruction
from pathlib import Path

class KokoroAdapter(TTSEngine):
    def __init__(self, model: str, voice: str):
        # load model once at init
        ...

    def generate(self, scene: TTSInstruction) -> Path:
        # generate and return file path
        ...
```

## Factory Function

Located in `engine.py`, below the abstract class:

```python
def get_tts_engine(config: TTSConfig) -> TTSEngine:
    if config.engine == "kokoro":
        from src.tts.adapters.kokoro import KokoroAdapter
        return KokoroAdapter(model=config.model, voice=config.voice)
    raise ValueError(f"Unknown TTS engine: {config.engine}")
```

- Imports adapters lazily (inside the `if` block) — not at module top.
- Adding a new engine = add one `elif` branch and one adapter file. Nothing else changes.

## Config Binding

Engine config lives in `config/engines.yaml`. Pydantic models in `src/entities/` validate it.

**YAML:**
```yaml
tts:
  engine: kokoro
  model: kokoro-82m
  voice: ru_female_01
```

**Entity:**
```python
class TTSConfig(BaseModel):
    engine: str
    model: str
    voice: str
```

The factory receives a `TTSConfig` instance — never a raw dict.

## Swappability Rules

Swapping an engine must require:
- One config file change (`engines.yaml`)
- Zero code changes

If a swap requires code changes, the adapter pattern is broken. Fix the factory or the adapter boundary.

## Adding a New Adapter Checklist

- [ ] Create `src/<domain>/adapters/<name>.py`
- [ ] Subclass the abstract base class
- [ ] Implement all abstract methods
- [ ] Add one `elif` branch in the factory function
- [ ] Add a unit test in `tests/unit/<domain>/test_<name>_adapter.py`
- [ ] Update `config/engines.yaml` example values if the config fields differ
