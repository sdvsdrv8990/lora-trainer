# Entry Point A — Pre-Production (New Channel Setup)

Use this workflow when starting a new channel from scratch. The goal is to build the intelligence foundation — channel DNA, competitor data, and asset library — before writing a single script.

This is a one-time setup per channel. Once complete, continue to [Entry Point B — Full Production Run](ENTRY_B_FULL_RUN.md) for each episode.

---

## Step 1 — Create the Workspace

```
pipeline_create_project(
    channel="my_channel",
    scenario="setup"
)
```

Creates `~/projects/videos/my_channel/setup/` with standard subdirectories (`audio/`, `images/`, `md/`, `renders/`).

---

## Step 2 — Channel DNA

Define what makes this channel unique. This config drives every creative decision downstream.

```
pipeline_save_channel_config(
    channel="my_channel",
    scenario="setup",
    channel_id="my_channel_id",
    config_json='{
        "channel_name": "...",
        "niche": "finance",
        "narrative_style": {
            "tone": "authoritative-friendly",
            "vocabulary": "simple",
            "hook_formula": "shocking_fact_first"
        },
        "visual_style": {
            "character_color": "#2563EB",
            "animation_energy": "medium",
            "frame_change_interval": 3.5
        },
        "frame_rules": {
            "max_static_duration": 4.0,
            "emotion_change_triggers_frame": true
        },
        "audio_style": {
            "tts_voice": "ru",
            "pace_wpm": 150
        },
        "prompt_style": {
            "art_style": "flat_vector",
            "color_palette": ["#2563EB", "#F59E0B", "#1F2937"]
        }
    }'
)
```

**Tip:** The richer the channel config, the better Claude's scenario and hook suggestions. Spend time on `narrative_style` and `frame_rules` — these are loaded into every session.

Then generate 5 skill template files from the config:

```
pipeline_create_channel_skills(
    channel="my_channel",
    scenario="setup",
    channel_id="my_channel_id"
)
```

Fill in each skill with content tailored to the niche. Use `pipeline_update_channel_skill` with `skill_name` set to each of: `CHANNEL_VOICE`, `FRAME_RULES`, `HOOK_ENGINE`, `IMAGE_PROMPTS`, `SCENARIO_WRITER`.

---

## Step 3 — Competitor Intelligence

Understanding what works in the niche before writing any scripts prevents guesswork.

Add 3–5 top competitor channels:

```
pipeline_add_competitor_channel(
    channel="my_channel",
    scenario="setup",
    channel_id="top_finance_channel",
    channel_data_json='{
        "channel_name": "Top Finance Channel",
        "platform": "youtube",
        "niche": "personal-finance",
        "avg_views": 250000,
        "subscriber_count": 1800000
    }'
)
```

For each channel, add their top 5 videos:

```
pipeline_add_competitor_video(
    channel="my_channel",
    scenario="setup",
    channel_id="top_finance_channel",
    video_id="yt_abc123",
    video_data_json='{
        "title": "Why Your Salary Destroys You",
        "platform": "youtube",
        "raw_metrics": {"views": 3200000, "likes": 142000, "comments": 4800, "duration": 487}
    }'
)
```

Import transcripts for structural analysis:

```
pipeline_import_transcript(
    channel="my_channel",
    scenario="setup",
    channel_id="top_finance_channel",
    video_id="yt_abc123",
    transcript_json='{
        "source": "tactiq",
        "segments": [
            {"start": 0.0, "end": 4.2, "text": "Opening hook text..."},
            ...
        ]
    }'
)
```

Query the intelligence index to find patterns:

```
pipeline_get_competitor_index(channel="my_channel", scenario="setup")
pipeline_query_competitor_data(
    channel="my_channel",
    scenario="setup",
    sheet="hooks",
    filter_field="hook_type",
    filter_value="shocking_stat"
)
```

Use these findings to refine `HOOK_ENGINE.md` and `SCENARIO_WRITER.md`.

---

## Step 4 — Asset Foundation

Build the character and object library before the first render. Re-using well-prepared assets across episodes keeps visual identity consistent.

Search existing assets before uploading new ones:

```
pipeline_search_assets(
    channel="my_channel",
    scenario="setup",
    scope="global",
    semantic="finance money"
)
```

Generate a lead character:

```
pipeline_generate_character(
    channel="my_channel",
    scenario="setup",
    name="protagonist",
    prompt="flat vector stickman character, professional worker, simple design",
    style="flat",
    wait="true"
)
```

Upload a brand background SVG:

```
pipeline_upload_asset(
    channel="my_channel",
    scenario="setup",
    category="backgrounds",
    name="office_clean",
    svg_content="<svg ...>...</svg>",
    scope="global",
    role="BASE",
    semantic_tags='["office", "professional", "clean"]',
    emotion_tags='["calm", "neutral"]',
    visual_energy="0.2"
)
```

**Minimum asset target before first render:**
- 3+ character body poses
- 5+ character emotion states
- 2–3 background variants
- 5–10 object/prop SVGs matching the niche's visual vocabulary

---

## Step 5 — First Episode

Asset library and competitor data are ready. Continue to [Entry Point B — Full Production Run](ENTRY_B_FULL_RUN.md).

The `channel_id` from Step 2 can now be passed to `pipeline_create_project` for every future scenario, which automatically seeds `project_config.json` from the channel config.
