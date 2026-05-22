# Content Intelligence System

> Registry tables, Hook Engine model, and analytics workflow for the video production pipeline.

---

## Overview

The pipeline maintains two registry files:

| File | Scope | Purpose |
|---|---|---|
| `pipeline/global_registry.json` | All projects | Cross-project performance, experiments, asset usage |
| `{workspace}/project_registry.json` | One scenario | Scene structure, hooks, emotion map, per-video analytics |

Claude forms all data as JSON. The server only saves and queries. Tables support dynamic schema — new columns and sheets are added without changing server code.

---

## Global Registry — Sheets

### `assets`
Tracks usage statistics across all scenarios.

| Column | Description |
|---|---|
| `id` | Asset ID (e.g. `G-CHR-001-001`) |
| `name` | Asset file stem |
| `type` | Type code: CHR, OBJ, BG, BUB, SND |
| `path` | Relative path |
| `created_at` | ISO timestamp |
| `total_uses` | Total times referenced across all scenarios |
| `total_scenarios` | Number of scenarios using this asset |
| `last_used` | ISO timestamp of last use |

### `experiments`
A/B tests comparing two scenarios on a variable.

| Column | Description |
|---|---|
| `experiment_id` | Unique identifier |
| `scenario_a` | First scenario |
| `scenario_b` | Second scenario |
| `variable` | What was tested (e.g. `hook_type`, `reward_type`) |
| `result` | Observed outcome |
| `winner` | Which scenario won |
| `insight` | Key learning |

### `performance`
Cross-project performance records (imported from platforms).

| Column | Description |
|---|---|
| `video_id` | Video/scenario identifier |
| `platform` | Platform (youtube, tiktok, instagram) |
| `avg_watch_time` | Average watch time in seconds |
| `retention_73s` | Retention at 73 seconds |
| `ctr` | Click-through rate |
| `rewatch_rate` | Rewatch rate |

---

## Project Registry — Sheets

### `scenes`
One row per scene in the video.

| Column | Description |
|---|---|
| `scene_id` | Scene identifier |
| `start` / `end` | Time range in seconds |
| `chapter` | Chapter or segment name |
| `module_type` | HOOK / SETUP / STABILITY / DISRUPTION / ESCALATION / PAYOFF / AFTERTASTE |
| `emotion` | Primary emotion |
| `visual_pattern` | Visual approach (close-up, wide, text-overlay, ...) |
| `audio_pattern` | Audio approach (tense, calm, silence, ...) |
| `reset_point` | Whether this scene is a reset point (true/false) |
| `notes` | Free-text notes |

### `hooks`
Hook analysis per video.

| Column | Description |
|---|---|
| `hook_id` | Unique hook identifier |
| `type` | Hook archetype (price_conflict, authority, mystery, ...) |
| `duration` | Hook duration in seconds |
| `trigger` | Psychological trigger used |
| `reward_type` | educational / story / entertainment / visual_loop |
| `audience_expectation` | What the hook promises |
| `effectiveness_score` | 0–10 score (filled after performance import) |

### `emotion_map`
Emotion timeline — one row per emotion segment.

| Column | Description |
|---|---|
| `time_start` / `time_end` | Time range in seconds |
| `emotion` | Emotion name (curiosity, tension, relief, ...) |
| `module` | Module type this segment belongs to |
| `intensity` | high / medium / low |
| `visual_support` | Visual element supporting this emotion |
| `audio_support` | Audio element supporting this emotion |

### `attention_graph`
Attention management plan — one row per attention event.

| Column | Description |
|---|---|
| `time` | Time in seconds |
| `module_type` | Module context |
| `reset_point` | Whether this is a reset point |
| `fatigue_level` | Estimated viewer fatigue (high/medium/low) |
| `trigger_type` | What triggers attention (visual/audio/text/pause) |
| `expected_retention` | Expected retention % at this point |

### `performance`
Per-video platform metrics (imported via `pipeline_import_platform_stats`).

| Column | Description |
|---|---|
| `metric` | Metric name (avg_watch_time, ctr, ...) |
| `value` | Metric value |
| `source` | Platform name |
| `recorded_at` | ISO timestamp |

### `insights`
Learnings extracted from performance analysis.

| Column | Description |
|---|---|
| `insight_id` | Unique identifier |
| `type` | experiment / observation / hypothesis |
| `description` | What was learned |
| `evidence` | Comma-separated evidence sources |
| `action` | Recommended action |
| `created_at` | ISO timestamp |

---

## Hook Engine Model

Every video uses the 7-module structure:

```
HOOK → SETUP → STABILITY → DISRUPTION → ESCALATION → PAYOFF → AFTERTASTE
```

### Modules

| Module | Role | Duration |
|---|---|---|
| HOOK | First impression, establishes the reward promise | 3–7s |
| SETUP | Context, introduce characters/setting | 5–15s |
| STABILITY | Status quo before disruption | 5–20s |
| DISRUPTION | Core conflict or problem | 10–30s |
| ESCALATION | Rising tension, stakes increase | 10–30s |
| PAYOFF | Resolution, reward delivery | 10–20s |
| AFTERTASTE | Call to action, open loop, emotion afterglow | 3–10s |

### Reward Types

| Type | Definition | Hook Pattern |
|---|---|---|
| `educational` | Viewer learns something actionable | Authority claim + gap |
| `story` | Narrative resolution promised | Character conflict |
| `entertainment` | Emotional payoff (humor, awe, shock) | Curiosity + surprise |
| `visual_loop` | Satisfying visual sequence | Pattern interrupt |

### Reset Points
Reset points are moments that re-engage viewers experiencing fatigue. Recommended placement:
- Short videos (< 30s): 1 reset point
- Medium videos (30–90s): 2–3 reset points at ~15s, ~45s
- Long videos (> 90s): every 30–45 seconds

---

## Asset ID System

Assets use a structured ID format:

```
{SCOPE}-{TYPE}-{GROUP:03d}-{ITEM:03d}

G-CHR-001-002   ← Global, Characters, Group 1 (crowd), Item 2 (figure_happy)
P-OBJ-001-001   ← Project, Objects, Group 1 (money), Item 1 (coin)
```

| Scope prefix | Location |
|---|---|
| `G-` | `pipeline/global_assets/` |
| `P-` | `{workspace}/assets/` |

| Type code | Asset type |
|---|---|
| `CHR` | Characters |
| `OBJ` | Objects |
| `BG` | Backgrounds |
| `BUB` | Speech bubbles |
| `SND` | Sounds (music/effects) |

Groups are auto-assigned alphabetically within each type directory. Items are assigned alphabetically within each group directory. IDs are rebuilt on every upload/delete via `_build_index()`.

---

## Typical Intelligence Workflow

```
1. pipeline_save_project_config
   → pipeline_get_analytics          ← check past retention patterns
   → pipeline_query_registry(sheet="hooks")  ← best hook types
   
2. pipeline_submit_scenario
   → pipeline_set_video_structure    ← record modules + reset points
   → pipeline_add_emotion_map        ← emotion timeline
   → pipeline_add_registry_row(sheet="hooks")  ← hook details

3. (after video goes live)
   → pipeline_import_platform_stats  ← YouTube/TikTok retention data
   → cross-reference with emotion_map
   → pipeline_add_registry_row(sheet="insights")
   → pipeline_create_experiment / pipeline_update_experiment

4. Next video planning
   → pipeline_get_analytics          ← patterns: what hook types work
   → pipeline_get_insights           ← validated learnings
   → pipeline_compare_videos         ← side-by-side comparison
```

---

## Dynamic Schema

Any sheet can be extended at runtime without server restart:

```python
# Add a new column to an existing sheet
pipeline_add_registry_column(scope="project", sheet="scenes", column_name="color_palette")

# Add a completely new sheet
pipeline_add_registry_sheet(scope="project", sheet_name="thumbnails",
                             columns='["thumbnail_id", "prompt", "ctr"]')
```

This means Claude can track any new analytics dimension without requiring a code change.
