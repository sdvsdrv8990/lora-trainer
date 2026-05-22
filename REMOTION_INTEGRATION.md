# Remotion Integration

## Status
Implemented — TypeScript files ready, Python bridge layer ready.
Requires `ensureBrowser()` to download Chromium on first render (~200MB, one-time).

## Location
```
pipeline/remotion/
├── package.json              ← remotion@4.0.465 + @remotion/renderer@4.0.465
├── tsconfig.json
├── render.ts                 ← CLI entry point called by Python
└── src/
    ├── types.ts              ← SceneLayout, SceneEvent interfaces
    ├── Root.tsx              ← registers Scene composition
    ├── Scene.tsx             ← event-driven renderer
    ├── components/
    │   ├── Background.tsx
    │   ├── Stickman.tsx      ← 7 pre-computed color filters for channel colors
    │   ├── FloatingText.tsx
    │   ├── AnimatedNumber.tsx
    │   └── SpeechBubble.tsx
    └── presets/
        ├── dramatic_popup.ts
        ├── shake.ts
        └── slide_in.ts
```

## Scene Schema v2 — events-based

```json
{
  "_schema_version": "v2",
  "scenes": [
    {
      "scene_id": 1,
      "chapter": "Hook",
      "audio_file": "/path/to/audio/scene_001.mp3",
      "duration": 8.4,
      "fps": 30,
      "canvas": {"width": 1920, "height": 1080},
      "events": [
        {"time": 0.0, "action": "show", "target": "bg", "component": "background",
         "state": {"color": "#F5F5F5"}},
        {"time": 0.5, "action": "show", "target": "worker1", "component": "stickman",
         "state": {"color": "#FFD700", "emotion": "neutral", "pose": "standing"},
         "position": {"x": 400, "y": 200}},
        {"time": 2.1, "action": "trigger_preset", "target": "worker1", "preset": "shake"},
        {"time": 2.1, "action": "change_state", "target": "worker1",
         "state": {"emotion": "shocked"}},
        {"time": 3.0, "action": "show_text", "target": "caption1",
         "value": "€800/month rent increase", "style": "gut_punch",
         "position": {"x": 700, "y": 500}},
        {"time": 6.0, "action": "hide", "target": "caption1"}
      ]
    }
  ]
}
```

## v1 vs v2 routing

`pipeline_submit_scene_layouts` auto-detects schema version:
- `scenes[].events` present → v2 (Remotion)
- `frames[].layers` present → v1 (Pillow compositor)

`pipeline_render_frames` routes automatically based on detected schema.

## MCP tools for v2

| Tool | Purpose |
|---|---|
| `pipeline_render_scene` | Render single scene via Remotion |
| `pipeline_render_all_scenes` | Render all scenes (background job) |
| `pipeline_get_remotion_status` | Per-scene progress |
| `pipeline_stop_render` | Cancel running job |
| `pipeline_update_scene_event` | Edit single event field |
| `pipeline_move_event` | Shift event timing |
| `pipeline_preview_scene_event` | PNG at specific time |
| `pipeline_list_scene_events` | Inspect events for a scene |

## Animation presets

| Preset | Effect |
|---|---|
| `dramatic_popup` | Spring scale + fade in — for reveals |
| `shake` | Decaying oscillation — for shock/impact |
| `slide_in` | Directional slide — for label entry |

## Stickman component — supported values

| Prop | Values |
|---|---|
| `emotion` | neutral, happy, sad, shocked, angry |
| `pose` | standing, pointing_right, pointing_left, sitting, arms_raised |
| `color` | #FFD700, #2196F3, #4CAF50, #FF4444, #9C27B0, #FF9800, #9E9E9E |

SVG parts expected at: `pipeline/global_assets/characters/crowd/{body,eyes,mouth,accessories}/`

## First render

```bash
cd pipeline/remotion
# One-time Chromium download (~200MB):
node -e "const {ensureBrowser}=require('@remotion/renderer'); ensureBrowser().then(()=>console.log('done'))"

# Test render:
node -e "
const {renderMedia,selectComposition,ensureBrowser}=require('@remotion/renderer');
const path=require('path');
// requires a scene.json to exist
"
```

## Python bridge

Python calls `render.ts` via `ts-node`:
```python
from src.remotion.renderer import render_scene
render_scene(scene_dict, output_path)
```
