# Scene Layout JSON Schema

Scene layouts describe what appears on screen and when. Two schema versions exist:
- **v1** (layers-based): static layers per frame, rendered by the Pillow compositor
- **v2** (events-based): time-ordered events per scene, rendered by Remotion

This document covers **v2**, which is the active development path.

---

## SceneLayout (v2)

Submitted to the server as a JSON string via `pipeline_submit_scene_layouts`:

```json
{
  "_schema_version": "v2",
  "canvas": {
    "width": 1920,
    "height": 1080
  },
  "scenes": [
    {
      "scene_id": 1,
      "chapter": "Intro hook",
      "duration": 4.3,
      "lipsync_file": "md/lipsync_scene_001.json",
      "events": [ ... ]
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `_schema_version` | `"v2"` | Must be `"v2"` for Remotion routing |
| `canvas.width` | int | Output width in pixels (default 1920) |
| `canvas.height` | int | Output height in pixels (default 1080) |
| `scenes[]` | array | One entry per scene; must match scenes in `tts_input.json` |
| `scenes[].scene_id` | int | Matches `scene_id` in `tts_input.json` and audio filenames |
| `scenes[].chapter` | string | Chapter label, appears as clip name in DaVinci |
| `scenes[].duration` | float | Scene duration in seconds (from `timeline.json`) |
| `scenes[].lipsync_file` | string | Relative path to lipsync JSON (optional; set after `pipeline_generate_lipsync`) |
| `scenes[].events` | array | Ordered animation events |

---

## SceneEvent

Each event in `scenes[].events`:

```json
{"time": 1.2, "action": "show", "target": "worker", "state": {"emotion": "neutral"}}
```

| Field | Type | Description |
|---|---|---|
| `time` | float | Seconds from scene start when this event fires |
| `action` | string | See action types below |
| `target` | string | Named element to act on (e.g., `"background"`, `"worker"`) |
| `state` | object | Optional state fields passed to the component |
| `preset` | string | Animation preset name (used with `trigger_preset`) |
| `value` | number/string | Numeric or text value (used with `show_number`, `show_text`) |
| `style` | string | Display style variant (e.g., `"gut_punch"` for large counter) |
| `position` | object | `{"x": float, "y": float}` relative to canvas (0.0–1.0) |

### Action types

| Action | Description |
|---|---|
| `show` | Make target visible; optionally set initial state |
| `hide` | Remove target from screen |
| `change_state` | Update character emotion, expression, or pose |
| `trigger_preset` | Fire a named animation preset (`dramatic_popup`, `shake`, `slide_in`) |
| `show_number` | Display an animated counter with optional style |
| `show_text` | Display a floating text overlay |
| `show_bubble` | Show a speech bubble at a position |
| `hide_bubble` | Remove the speech bubble |

---

## Worked Example — 3-event scene

```json
{
  "scene_id": 2,
  "chapter": "The moment of shock",
  "duration": 5.8,
  "lipsync_file": "md/lipsync_scene_002.json",
  "events": [
    {
      "time": 0.0,
      "action": "show",
      "target": "background",
      "state": {"asset_id": "G-BG-001-BASE"}
    },
    {
      "time": 0.5,
      "action": "show",
      "target": "worker",
      "state": {"emotion": "neutral", "pose": "standing"},
      "position": {"x": 0.5, "y": 0.75}
    },
    {
      "time": 2.1,
      "action": "change_state",
      "target": "worker",
      "state": {"emotion": "shocked"}
    },
    {
      "time": 2.3,
      "action": "trigger_preset",
      "preset": "dramatic_popup"
    },
    {
      "time": 3.0,
      "action": "show_number",
      "value": 3800,
      "style": "gut_punch",
      "position": {"x": 0.5, "y": 0.3}
    }
  ]
}
```

---

## Lipsync Connection

Lipsync connects mouth cue timings to the Stickman component:

1. Run `pipeline_generate_lipsync(scene_id=N)` — calls rhubarb-lip-sync on `audio/scene_NNN.mp3`.
2. Output: `md/lipsync_scene_NNN.json` — an array of `{start, end, phoneme}` entries.
3. Set `scenes[N].lipsync_file = "md/lipsync_scene_NNN.json"` in the layout.
4. Re-submit the layout via `pipeline_submit_scene_layouts`.
5. Remotion's `Stickman.tsx` reads this file and advances mouth shape frames automatically.

Phoneme codes from rhubarb: `A`, `B`, `C`, `D`, `E`, `F`, `G`, `H`, `X` (silence).
`Stickman.tsx` maps these to mouth SVG variants in `global_assets/characters/crowd/mouth/`.

---

## Storage and Loading

| File | Written by | Read by |
|---|---|---|
| `md/scene_layout.json` | `pipeline_submit_scene_layouts` | `pipeline_render_frames`, `pipeline_render_scene`, `pipeline_render_all_scenes` |
| `md/remotion_status.json` | `pipeline_render_all_scenes` | `pipeline_get_remotion_status` |
| `renders/scenes/scene_NNN.mp4` | Remotion renderer | `pipeline_export_davinci`, `pipeline_assemble_scenes` |

To update a single event without resubmitting the full layout, use:
- `pipeline_update_scene_event` — modifies one field (dot notation supported)
- `pipeline_move_event` — shifts event time and re-sorts the events array

After any event edit, re-render the affected scene: `pipeline_render_scene(scene_id=N)`.
