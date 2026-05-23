# Kokoro TTS Engine

> **Status: planned — not yet implemented.** Current engine: espeak-ng.
> This file will be updated when Kokoro is wired into the adapter layer.

## What It Is

[Kokoro](https://github.com/hexgrad/kokoro) is a lightweight, high-quality neural TTS engine
that runs locally with no API key. It produces significantly more natural speech than espeak-ng
while keeping inference fast enough for batch voiceover generation.

## Why It's in This Project

The pipeline uses a swappable engine architecture — TTS and image generation are config-driven,
not hardcoded. Kokoro is the planned upgrade for the TTS slot because it:

- runs locally (no cost, no rate limits)
- outputs 24kHz audio suitable for video voiceover
- supports multiple voices and speaking styles
- is MIT-licensed

## Where It Fits in the Workflow

Entry point B, Step 2: `pipeline_start_voiceover`

```
pipeline_submit_scenario → [tts_input.json] → pipeline_start_voiceover
                                                      ↓
                                              engines.yaml: tts_engine: kokoro
                                                      ↓
                                              src/tts/adapters/kokoro.py  ← NOT YET BUILT
                                                      ↓
                                              audio/scene_NNN.mp3
```

Current path uses `src/tts/adapters/espeak.py` with `tts_engine: espeak` in `engines.yaml`.

## How to Switch (once implemented)

```yaml
# pipeline/config/engines.yaml
tts_engine: kokoro
kokoro_voice: af_heart      # or any kokoro voice ID
kokoro_speed: 1.0
```

Then call `pipeline_switch_engine_profile` or edit `engines.yaml` directly.
No code change required — the adapter pattern handles dispatch.

## Implementation Checklist

> For the local developer. Update this section and remove the "Status: planned" line
> when the adapter is complete and verified.

- [ ] `pip install kokoro` in `pipeline/venv`
- [ ] Create `pipeline/src/tts/adapters/kokoro.py` implementing `TTSEngine` base class
- [ ] Add `kokoro` entry to `pipeline/config/engines.yaml`
- [ ] Generate one test audio file and confirm it exists on disk
- [ ] Update `pipeline/INSTALL.md` — add Kokoro installation step
- [ ] Update this file: change status to "implemented", add voice list

## README Link

Add this row to the README documentation table once the adapter is shipped:

```markdown
| [Kokoro TTS](docs/pipeline/reference/KOKORO_TTS.md) | Neural TTS engine — voices, switching, config |
```
