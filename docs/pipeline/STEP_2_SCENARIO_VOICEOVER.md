# Step 2 — Scenario Intake and Voiceover

This document describes the currently implemented Step 2 workflow.

Goal: Claude.ai can send a confirmed scenario to the local pipeline, the pipeline
acknowledges that it received the scenario, prepares `md/tts_input.json`, starts
voiceover generation, reports status, and accepts a stop request.

## Current Scope

This is a working control-flow implementation. Voice quality is intentionally not
the goal yet. The current TTS backend uses local `espeak-ng` plus `ffmpeg` to
produce real MP3 files quickly and predictably.

## Files Written

Inside the scenario workspace:

```text
md/scenario.txt
md/tts_input.json
md/voiceover_status.json
audio/scene_001.mp3
audio/scene_002.mp3
...
```

## MCP Tools

### `pipeline_submit_scenario`

Inputs:

- `channel`
- `scenario`
- `scenario_text`

Behavior:

1. Verifies that the workspace exists.
2. Saves the confirmed text to `md/scenario.txt`.
3. Splits the text into scenes.
4. Writes `md/tts_input.json`.
5. Writes `md/voiceover_status.json` with status `scenario_received`.

### `pipeline_start_voiceover`

Inputs:

- `channel`
- `scenario`
- `wait`

Behavior:

- `wait: "false"` starts a background job and returns immediately.
- `wait: "true"` runs synchronously and returns after generation finishes.

The job reads `md/tts_input.json` and writes one MP3 file per scene to `audio/`.

### `pipeline_get_voiceover_status`

Inputs:

- `channel`
- `scenario`

Returns the current contents of `md/voiceover_status.json`.

Important statuses:

- `idle`
- `scenario_received`
- `running`
- `stopping`
- `cancelled`
- `complete`
- `failed`

### `pipeline_stop_voiceover`

Inputs:

- `channel`
- `scenario`

Requests cancellation of a running background job. The worker stops after the
current scene completes.

## Claude.ai Control Loop

Recommended flow:

1. Confirm the scenario with the user.
2. Call `pipeline_submit_scenario`.
3. Tell the user that the scenario was received and voiceover can start.
4. Call `pipeline_start_voiceover` with `wait: "false"`.
5. Poll `pipeline_get_voiceover_status` until status is `complete`, `cancelled`, or `failed`.
6. If the user asks to stop, call `pipeline_stop_voiceover`.

For quick tests, use `wait: "true"` with a short text.

## Validation

Minimum evidence that Step 2 works:

```text
pipeline_submit_scenario -> ok true
pipeline_start_voiceover(wait="true") -> status complete
pipeline_get_voiceover_status -> completed_scenes equals total_scenes
audio/scene_001.mp3 exists
```

