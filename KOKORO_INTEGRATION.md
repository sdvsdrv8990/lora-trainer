# Kokoro TTS Integration Plan

## Status
Not implemented. espeak-ng is the current working engine.

## Why Kokoro
- Apache 2.0 license — commercial use allowed
- 82M parameter model — fast on CPU
- High quality English TTS — production-ready output
- Local inference — no API costs

## Installation (when ready)
```
pip install kokoro-onnx
```

## Expected adapter location
`pipeline/src/tts/adapters/kokoro.py`

## Interface to implement
```python
class KokoroAdapter:
    def synthesize(self, text: str, output_path: Path, **kwargs) -> Path:
        ...
```

## engines.yaml switch (one line when adapter is ready)
```yaml
tts:
  engine: kokoro   # change from espeak
```
