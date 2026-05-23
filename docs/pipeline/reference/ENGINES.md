# Engine Profiles

Engine selection is driven entirely by `pipeline/config/engines.yaml`. No code changes are needed to swap engines — only a config change or a `pipeline_switch_engine_profile` tool call.

---

## engines.yaml Schema

```yaml
# TTS engine configuration
tts:
  engine: "espeak"          # Active engine: espeak | kokoro (planned)
  target_engine: "kokoro"   # Target when Kokoro adapter is ready
  model: "espeak-ng"
  voice: "ru"
  speed_wpm: 150

# Image generation engine configuration
image:
  profile: "stub"           # Active profile ID (overrides engine/model below)
  profiles_dir: "config/image_engines"
  engine: "stub"            # Fallback if profile not found: stub | diffusers
  provider: "local"
  model: "stabilityai/stable-diffusion-xl-base-1.0"

# SVG rendering
svg:
  engine: "cairosvg"
  dpi: 96

# PNG-to-SVG tracing
tracing:
  engine: "vtracer"
  color_mode: "color"
  filter_speckle: 4

# Asset overuse detection thresholds
asset_overuse:
  global_warn_threshold: 10
  project_warn_threshold: 5
  exempt_roles: ["BASE", "LORA"]
```

---

## TTS Engines

### espeak (current)

- Binary: `espeak-ng`
- Install: `sudo dnf install espeak-ng` (Fedora) or `sudo apt install espeak-ng`
- Adapter: `pipeline/src/tts/adapters/espeak.py`
- Produces: `audio/scene_NNN.mp3` per scene
- Limitations: robotic voice quality; suitable for development and testing

### kokoro (planned)

- Status: target engine specified in `engines.yaml`; adapter not yet written
- Adapter would go in `pipeline/src/tts/adapters/kokoro.py`
- To enable: write the adapter, add `elif config.engine == "kokoro"` in `src/tts/engine.py`, change `tts.engine` in `engines.yaml`

---

## Image Engines

### stub (default)

- Adapter: `pipeline/src/images/adapters/stub.py`
- Output: minimal 1×1 PNG placeholder file
- Purpose: develop and test the pipeline without GPU hardware
- Profile: `profile: "stub"` in `engines.yaml`

### diffusers (local inference)

- Adapter: `pipeline/src/images/adapters/diffusers.py`
- Requires: `pip install diffusers transformers accelerate`
- Requires: GPU with 8GB+ VRAM (NVIDIA or AMD/ROCm)
- Supports: SD 1.5, SDXL via HuggingFace model IDs
- Profile examples: `sd15_deliberate`, `sdxl_base`

Profile configs live in `pipeline/config/image_engines/<profile_id>.json`:

```json
{
  "engine": "diffusers",
  "model": "stabilityai/stable-diffusion-xl-base-1.0",
  "scheduler": "DPMSolverMultistepScheduler",
  "steps": 20,
  "guidance_scale": 7.5,
  "width": 1024,
  "height": 576
}
```

---

## Switching Engine Profile

At runtime (no server restart):

```
pipeline_switch_engine_profile(
    channel=..., scenario=...,
    profile_id="sdxl_base"
)
```

This writes `image.profile` in `engines.yaml` and takes effect on the next `pipeline_render_frames` call.

List available profiles:

```
pipeline_list_engine_profiles(channel=..., scenario=...)
```

Returns `profiles` array and `active_id`.

---

## Adding a New Image Engine Adapter

1. Create `pipeline/src/images/adapters/<name>.py`:

```python
from src.images.engine import ImageEngine
from src.entities.prompts import ImagePrompt
from pathlib import Path

class MyAdapter(ImageEngine):
    def __init__(self, model: str, **kwargs):
        ...  # load model once at init

    def generate(self, prompt: ImagePrompt) -> Path:
        ...  # generate and return file path
```

2. Add one `elif` branch in `pipeline/src/images/engine.py`'s `get_image_engine()` factory:

```python
elif config.engine == "my_engine":
    from src.images.adapters.my_engine import MyAdapter
    return MyAdapter(model=config.model)
```

3. Add a profile JSON in `pipeline/config/image_engines/my_profile.json`.

4. Change `image.engine` (or `image.profile`) in `engines.yaml`.

No changes to `server.py` or any tool are needed. See `pipe-adapter-pattern` skill for the full contract.

---

## SVG Rasterization

The Pillow compositor (v1 path) uses CairoSVG to rasterize SVG assets:

- Install: `pip install cairosvg`
- If not installed: SVG layers render as a grey placeholder and a warning appears in tool responses
- DPI: 96 (configured in `svg.dpi`)

## PNG-to-SVG Tracing

`pipeline_generate_asset` and `pipeline_generate_character` optionally trace generated PNGs to SVG:

- Tool: vtracer (`pip install vtracer`)
- Config: `tracing.color_mode`, `tracing.filter_speckle` in `engines.yaml`
- If not installed: PNG is saved without SVG tracing; upload SVG manually via `pipeline_upload_asset`
