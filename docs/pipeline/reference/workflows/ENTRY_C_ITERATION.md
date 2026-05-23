# Entry Point C — Iteration and Editing

Use this when modifying a scenario that has already been through a full or partial production run. The goal is to change the minimum required components — not to rerun the whole pipeline.

---

## Editing the Script (Voiceover)

If dialogue changes significantly, re-run from voiceover:

```
pipeline_submit_scenario(
    channel="my_channel",
    scenario="ep_001",
    tts_input='[...]'       # updated JSON array
)
pipeline_start_voiceover(channel="my_channel", scenario="ep_001", wait="false")
```

After voiceover completes, re-run `pipeline_build_timeline` to update durations, then re-render.

**If only one scene changed:** re-submit the full `tts_input` array, then regenerate only that scene's audio.
Re-transcribe only the changed scene: `pipeline_transcribe_scenes` with the model and language set as before — it overwrites only the scenes it finds audio for.

---

## Editing a Single Scene Layout

Change one event without resubmitting the full layout:

```
pipeline_update_scene_event(
    channel="my_channel",
    scenario="ep_001",
    scene_id=3,
    event_index=2,           # zero-based index in the events array
    field="state.emotion",   # dot notation for nested fields
    value="shocked"
)
```

Then re-render that scene only:

```
pipeline_render_scene(
    channel="my_channel",
    scenario="ep_001",
    scene_id=3,
    wait="true"
)
```

**Supported fields for `pipeline_update_scene_event`:**
- `time` — event start time in seconds
- `action` — action type string
- `state.emotion` — character emotion
- `state.pose` — character pose
- `position.x` / `position.y` — position (0.0–1.0 relative)
- `value` — for `show_number` / `show_text` actions
- `preset` — animation preset name

---

## Moving an Event in Time

Shift when an event fires without touching other fields:

```
pipeline_move_event(
    channel="my_channel",
    scenario="ep_001",
    scene_id=3,
    event_index=2,
    new_time=3.1       # seconds from scene start
)
```

The server re-sorts the `events` array by `time` after moving. Re-render the scene to see the change.

---

## Previewing Before Re-rendering

Extract a frame at a specific time from an already-rendered scene MP4:

```
pipeline_preview_scene_event(
    channel="my_channel",
    scenario="ep_001",
    scene_id=3,
    time=2.5
)
```

Output: `renders/previews/scene_003_t2.5.png`

Use this to check timing before committing to a full scene re-render.

For a static frame from the Pillow compositor (v1 path):

```
pipeline_preview_frame(
    channel="my_channel",
    scenario="ep_001",
    frame_id="3"
)
```

---

## Re-transcribing After Audio Change

If voiceover audio changes, re-transcribe affected scenes:

```
pipeline_transcribe_scenes(
    channel="my_channel",
    scenario="ep_001",
    model="base",
    language="ru"
)
```

This overwrites `timeline.json` words/segments for scenes whose audio files have changed.

If you know the correct text but want to fix timestamps only (faster than full transcription):

```
pipeline_align_scene(
    channel="my_channel",
    scenario="ep_001",
    scene_id=3,
    corrected_text="The correct spoken text for this scene.",
    model="base",
    language="ru"
)
```

`align_scene` skips speech recognition and only aligns timing — much faster than re-transcribing.

---

## Subtitle Export

Export subtitles from transcription results (no re-transcription needed):

```
pipeline_export_subtitles(
    channel="my_channel",
    scenario="ep_001",
    format="srt",            # srt | vtt | ass | tsv | txt
    scene_ids="all"          # or "1,3,5" for specific scenes
)
```

Output: `md/subtitles/scene_NNN.srt`

For karaoke-style word highlighting in DaVinci (ASS format with word-level timing):

```
pipeline_export_subtitles(
    channel="my_channel",
    scenario="ep_001",
    format="ass",
    word_level="true"
)
```

---

## Swapping an Asset

Replace a global or project asset without changing the scene layout:

```
# Remove old asset
pipeline_delete_asset(
    channel="my_channel",
    scenario="ep_001",
    asset_id="G-OBJ-002-CTX"
)

# Upload replacement
pipeline_upload_asset(
    channel="my_channel",
    scenario="ep_001",
    category="objects/money",
    name="coin_stack_v2",
    svg_content="<svg ...>...</svg>",
    scope="global",
    role="CTX",
    semantic_tags='["money", "wealth"]'
)
```

After upload, re-render any scenes that reference the old asset ID.

---

## Switching Image Engine Mid-Project

Change the render engine without restarting the server:

```
pipeline_switch_engine_profile(
    channel="my_channel",
    scenario="ep_001",
    profile_id="sdxl_base"
)
```

Takes effect on the next `pipeline_render_frames` or `pipeline_render_scene` call.
List available profiles: `pipeline_list_engine_profiles`.

---

## Listing What's in the Workspace

Check which files exist without reading their content:

```
pipeline_list_files(
    channel="my_channel",
    scenario="ep_001",
    directory="md"         # empty string = workspace root
)

pipeline_list_frames(channel="my_channel", scenario="ep_001")
pipeline_list_images(channel="my_channel", scenario="ep_001")
```

---

## Partial Re-render (v1 Pillow path)

Re-render specific frames without touching other frames:

```
pipeline_render_frames(
    channel="my_channel",
    scenario="ep_001",
    frame_ids="3,7,12",     # comma-separated frame IDs
    wait="true"
)
```

Update a single frame's layer definition without full layout resubmit:

```
pipeline_update_frame_layout(
    channel="my_channel",
    scenario="ep_001",
    frame_id="7",
    layers_json='[{"type": "asset", "asset_id": "G-BG-002-BASE", "z": 0}, ...]'
)
```
