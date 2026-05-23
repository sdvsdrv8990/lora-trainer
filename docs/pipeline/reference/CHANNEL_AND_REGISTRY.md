# Channel Config and Registry

Two persistence systems track channel identity and production data:
- **Channel config** — per-channel DNA: voice, style, narrative rules, visual preferences
- **Registry** — per-scenario data tables: scenes, hooks, analytics, experiments

---

## Channel Directory Structure

```
pipeline/channels/
└── <channel_id>/
    ├── channel_config.json          Channel DNA file
    └── skills/
        ├── CHANNEL_VOICE.md         Tone, vocabulary, pacing rules for scripts
        ├── FRAME_RULES.md           When to change frames, visual transition triggers
        ├── HOOK_ENGINE.md           Hook formulas and patterns for this niche
        ├── IMAGE_PROMPTS.md         Prompt style, negative prompts, visual rules
        └── SCENARIO_WRITER.md       Script structure, scene count, formatting rules
```

`channel_id` is the directory name (e.g., `wallet_from_eu`). It is not the same as the `channel` workspace parameter used in tool calls.

---

## channel_config.json

The DNA file for all videos on this channel:

```json
{
  "channel_id": "wallet_from_eu",
  "channel_name": "Wallet from EU",
  "niche": "finance-migration",
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
}
```

Key fields used at render time:
- `visual_style.character_color` → injected into SVG `currentColor` for character coloring
- `frame_rules` → informs Claude's frame-change decisions during layout design
- `narrative_style.tone` → loaded into `CHANNEL_VOICE.md` and used by script generation

---

## Channel Skill Files

Each of the 5 skill files is a Markdown document loaded by Claude at the start of a session for that channel. They are generated from the channel config by `pipeline_create_channel_skills` and updated via `pipeline_update_channel_skill`.

| Skill | Purpose |
|---|---|
| `CHANNEL_VOICE.md` | Defines tone, sentence length, vocabulary, call-to-action phrasing |
| `FRAME_RULES.md` | When to trigger a new frame: emotion change, topic shift, time threshold |
| `HOOK_ENGINE.md` | 3–5 hook opening formulas that work for this niche with examples |
| `IMAGE_PROMPTS.md` | Prompt prefix/suffix templates, negative prompts, art style rules |
| `SCENARIO_WRITER.md` | Scene count per video, per-scene word budget, chapter naming |

---

## Registry

### Global Registry (`pipeline/global_registry.json`)

Cross-project data. Contains performance stats, experiments, and asset overuse data:

```json
{
  "sheets": {
    "performance": {
      "columns": ["video_id", "platform", "avg_watch_time", "ctr", "like_rate"],
      "rows": [ ... ]
    },
    "experiments": {
      "columns": ["experiment_id", "scenario_a", "scenario_b", "variable", "winner", "insight"],
      "rows": [ ... ]
    }
  }
}
```

### Project Registry (`<workspace>/project_registry.json`)

Per-scenario data. Default sheets:

| Sheet | Contents |
|---|---|
| `overview` | Production metadata: channel, scenario, dates, step status |
| `structure` | Hook Engine structure: modules, reset_points, hook_type, reward_type |
| `chapters` | Per-chapter breakdown with fact references |
| `key_data` | Every fact used in the script with source and verification status |
| `emotion_map` | Emotional arc mapped to timestamps (`time_start`, `time_end`, `emotion`, `intensity`) |
| `production` | Step-by-step production status |
| `assets` | FES scores per asset used in this video |
| `performance` | YouTube/TikTok stats imported after publish |

Sheets are dynamic — add columns or new sheets without code changes via `pipeline_add_registry_column` and `pipeline_add_registry_sheet`.

---

## Common Usage Patterns

### Add a row to a sheet

```
pipeline_add_registry_row(
    channel="wallet_from_eu",
    scenario="ep_005",
    scope="project",
    sheet="key_data",
    row_data='{"fact_id": "F001", "text": "...", "source": "Reuters", "verified": "true"}'
)
```

### Query rows by field value

```
pipeline_query_registry(
    channel="wallet_from_eu",
    scenario="ep_005",
    scope="project",
    sheet="key_data",
    filter_field="verified",
    filter_value="false"
)
```

### Update one field

```
pipeline_update_registry(
    channel="wallet_from_eu",
    scenario="ep_005",
    scope="project",
    sheet="key_data",
    row_id="F001",
    field="verified",
    value="true"
)
```

---

## Creating a New Channel

```
# 1. Create workspace (channel + scenario directory tree)
pipeline_create_project(channel="my_channel", scenario="ep_001")

# 2. Save channel DNA
pipeline_save_channel_config(
    channel="my_channel",
    scenario="ep_001",
    channel_id="my_channel_id",
    config_json='{"channel_name": "...", "niche": "...", ...}'
)

# 3. Generate 5 skill template files
pipeline_create_channel_skills(
    channel="my_channel",
    scenario="ep_001",
    channel_id="my_channel_id"
)

# 4. Fill in each skill file
pipeline_update_channel_skill(
    channel="my_channel",
    scenario="ep_001",
    channel_id="my_channel_id",
    skill_name="CHANNEL_VOICE",
    content="# Channel Voice\n\n..."
)
```

Repeat step 4 for all 5 skill names: `CHANNEL_VOICE`, `FRAME_RULES`, `HOOK_ENGINE`, `IMAGE_PROMPTS`, `SCENARIO_WRITER`.

Future scenarios in this channel inherit the config via the `channel_id` argument to `pipeline_create_project`.
