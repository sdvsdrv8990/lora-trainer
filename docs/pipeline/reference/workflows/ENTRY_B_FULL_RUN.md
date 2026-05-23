# Entry Point B — Full Production Run

Takes a scenario idea to a finished draft MP4. Each step gates on the previous step's state being `complete`. Claude advances state via `pipeline_set_state` after confirming each step succeeded.

Prerequisites: channel DNA and asset library ready (see [Entry Point A](ENTRY_A_PREPRODUCTION.md)).

---

## Step 1 — Create Workspace

```
pipeline_create_project(
    channel="my_channel",
    scenario="ep_001",
    channel_id="my_channel_id"    # seeds project_config from channel_config
)
```

Creates `~/projects/videos/my_channel/ep_001/` with standard subdirectories.

**Check response:** `created: true` → workspace is fresh. `created: false` → it already exists.

---

## Step 2 — Submit Scenario (TTS Input)

Dialogue with Claude to write a script. When confirmed, submit as structured JSON:

```
pipeline_submit_scenario(
    channel="my_channel",
    scenario="ep_001",
    tts_input='[
        {
            "scene_id": 1,
            "chapter": "Intro hook",
            "text": "Opening line of spoken voiceover...",
            "tts": {"voice": "ru", "speed_wpm": 150},
            "metadata": {"emotion": "neutral", "importance": "high"}
        },
        {
            "scene_id": 2,
            "chapter": "The problem",
            "text": "...",
            "tts": {"voice": "ru", "speed_wpm": 150},
            "metadata": {"emotion": "tension"}
        }
    ]'
)
```

Writes `md/tts_input.json` and `scenario.txt`. Returns `scene_count`.

**Common failure:** `tts_input must be a JSON array` — confirm the outer brackets are present.

---

## Step 3 — Voiceover Generation

```
pipeline_start_voiceover(
    channel="my_channel",
    scenario="ep_001",
    wait="false"           # use "true" for small scenarios only
)
```

Starts espeak-ng in background. Monitor until complete:

```
pipeline_get_voiceover_status(channel="my_channel", scenario="ep_001")
```

Wait for `status: "complete"`. Output: `audio/scene_001.mp3`, `audio/scene_002.mp3`, etc.

**Common failure:** `audio directory not found` — check workspace was created first.

---

## Step 4 — Build Timeline

```
pipeline_build_timeline(channel="my_channel", scenario="ep_001")
```

Runs ffprobe on each scene audio file. Writes `md/timeline.json` with:
- `scene_id`
- `duration` (seconds)
- `audio_path`

**Check response:** `total_duration` should match expected video length. If a scene is missing, check that voiceover completed for all scenes.

---

## Step 5 — Transcribe Scenes (Optional but Recommended)

Adds word-level timing to the timeline for subtitle export and lipsync:

```
pipeline_transcribe_scenes(
    channel="my_channel",
    scenario="ep_001",
    model="base",          # tiny/base/small/medium/large
    language="ru"
)
```

Enriches `md/timeline.json` with `words[]` and `segments[]` per scene.
Saves `md/stable_result_scene_NNN.json` for subtitle export.

**Note:** Requires `faster-whisper` installed in the pipeline venv (`pip install faster-whisper`).

---

## Step 6 — Submit Scene Layouts

Design the visual track: which assets appear, when, what animations fire.

```
pipeline_submit_scene_layouts(
    channel="my_channel",
    scenario="ep_001",
    scene_layout_json='{
        "_schema_version": "v2",
        "canvas": {"width": 1920, "height": 1080},
        "scenes": [
            {
                "scene_id": 1,
                "chapter": "Intro hook",
                "duration": 4.3,
                "events": [
                    {"time": 0.0, "action": "show", "target": "background", "state": {"asset_id": "G-BG-001-BASE"}},
                    {"time": 0.5, "action": "show", "target": "worker", "state": {"emotion": "neutral"}},
                    {"time": 2.1, "action": "change_state", "target": "worker", "state": {"emotion": "shocked"}},
                    {"time": 2.3, "action": "trigger_preset", "preset": "dramatic_popup"}
                ]
            }
        ]
    }'
)
```

Check asset availability before layout design: `pipeline_list_assets`, `pipeline_get_asset_stats`.
For schema details: see [Scene Layout Schema](../SCENE_LAYOUT_SCHEMA.md).

---

## Step 7 — Render Scenes

### v2 path (Remotion — recommended)

```
pipeline_render_all_scenes(
    channel="my_channel",
    scenario="ep_001",
    wait="false"
)
```

Outputs: `renders/scenes/scene_001.mp4`, `renders/scenes/scene_002.mp4`, etc.

Monitor: `pipeline_get_remotion_status(channel="my_channel", scenario="ep_001")`

**Requires:** Node.js and `npm install` inside `pipeline/remotion/`.

### v1 path (Pillow compositor — fallback)

Submit a v1 (layers-based) layout, then:

```
pipeline_render_frames(channel="my_channel", scenario="ep_001", wait="false")
```

Outputs static PNGs in `images/`. Use `pipeline_assemble_scenes` (Step 8) to combine with audio.

**Requires:** `pip install cairosvg Pillow` in the pipeline venv.

---

## Step 8 — Assemble and Concatenate (v1 path or post-Remotion)

If using the v1 Pillow path, assemble PNGs + audio into per-scene MP4s:

```
pipeline_assemble_scenes(channel="my_channel", scenario="ep_001", wait="false")
```

Outputs: `renders/scenes/scene_NNN.mp4`.
Monitor: `pipeline_get_render_status(channel="my_channel", scenario="ep_001")`

Then concatenate all scene clips into the draft render:

```
pipeline_concat_scenes(channel="my_channel", scenario="ep_001", wait="true")
```

Output: `renders/ep_001_draft.mp4`.

Confirm: `pipeline_get_output_file(channel="my_channel", scenario="ep_001")` → returns `path`, `size_mb`, `duration_sec`.

---

## Step 9 — DaVinci Export

```
pipeline_export_davinci(
    channel="my_channel",
    scenario="ep_001",
    format="fcpxml"
)
```

Output: `renders/ep_001_davinci.fcpxml`

All paths in the FCPXML are absolute. Scene durations come from `timeline.json`.

---

## Step 10 — DaVinci Resolve (Local PC)

Open DaVinci Resolve 18+:
1. File → Import → Timeline → select the `.fcpxml` file
2. Edit page: add transitions, background music track
3. Subtitles: import SRT from `md/subtitles/` if exported
4. Color page: grade
5. Deliver page: YouTube 1080p preset → export

See [DaVinci Workflow](../../DAVINCI_WORKFLOW.md) for details.

---

## State Advancement

After each step succeeds, advance the pipeline state:

```
pipeline_set_state(
    channel="my_channel",
    scenario="ep_001",
    step="2",
    status="complete"
)
```

Step numbers: 0=init, 1=config, 2=voiceover, 3=timeline, 4=render, 5=assembly, 6=export.

---

## Resuming a Failed Run

1. `pipeline_get_state` → check `current_step` and `step_status`
2. If `step_status: "failed"`, investigate the error in the last tool response
3. Re-run the failed step's tool; don't re-run earlier steps unless their outputs are corrupt
4. `pipeline_set_state` with `status: "complete"` to continue
