# Channel System

> Channel DNA, competitor intelligence, and three entry-point workflow for the video production pipeline.

---

## Overview

The channel system provides two storage layers and one workflow:

| Layer | Path | Purpose |
|---|---|---|
| Channel config | `pipeline/channels/{id}/channel_config.json` | Channel DNA — style, audience, format defaults |
| Channel skills | `pipeline/channels/{id}/skills/{SKILL_NAME}.md` | Production knowledge Claude uses to generate content |
| Competitor intelligence | `pipeline/competitor_intelligence/channels/{id}/` | Channel and video records with computed metrics |

Claude forms all data as JSON or markdown. The server only stores, retrieves, and applies engagement formula math. Claude reasons, analyzes, and makes decisions.

---

## Channel Config (DNA)

A channel config is the single source of truth for what makes a channel distinctive.

**`channel_config.json` example:**
```json
{
  "channel_id": "finance_shorts",
  "channel_name": "Money Secrets",
  "description": "Short-form finance content for retail investors",
  "style": {
    "mood": "dramatic",
    "visual_energy": "high",
    "color_palette": ["#1a1a2e", "#e94560"],
    "typography": "bold sans-serif"
  },
  "audience": {
    "age_range": "25-45",
    "interest_tags": ["investing", "trading", "financial freedom"],
    "pain_points": ["losing money", "missing opportunities", "not understanding markets"]
  },
  "format": {
    "default_duration_sec": 60,
    "scene_count": "auto",
    "hook_style": "question",
    "reward_type": "revelation"
  },
  "voice": {
    "tts_engine": "espeak",
    "voice": "en",
    "speed_wpm": 160
  },
  "custom_notes": "Always start with a hook that creates FOMO. End with a clear call-to-action."
}
```

`pipeline_create_project` with `channel_id` set auto-seeds `project_config.json` from the channel defaults. Claude may then override any field for the specific scenario.

---

## Channel Skills

Five skill files encode production knowledge that Claude loads at the start of a session.

| Skill name | Purpose |
|---|---|
| `SCENARIO_WRITER` | How to write scenarios for this channel (structure, tone, pacing) |
| `IMAGE_PROMPTS` | Style guide for image prompt generation (colors, subjects, camera angles) |
| `FRAME_RULES` | Frame layout rules (character positions, text zones, composite patterns) |
| `HOOK_ENGINE` | Hook type catalog and selection rules for this channel |
| `CHANNEL_VOICE` | Voice and tone guide (vocabulary, forbidden phrases, emotional register) |

Skills are plain markdown written by Claude during the channel setup session.

**Workflow:**
1. `pipeline_create_channel_skills(channel_id)` — creates 5 template `.md` files.
2. Claude and user develop each skill document via `pipeline_update_channel_skill`.
3. At the start of each production session: `pipeline_get_channel_skill(channel_id, skill_name)` for each skill.

---

## Competitor Intelligence

Competitor data is stored at `competitor_intelligence/channels/{channel_id}/videos/{video_id}/`.

**`video.json` structure:**
```json
{
  "video_id": "abc123",
  "channel_id": "competitor_1",
  "title": "5 Money Habits of Rich People",
  "url": "...",
  "published_at": "2026-04-01",
  "raw_metrics": {
    "views": 500000,
    "likes": 25000,
    "comments": 1200,
    "retention_rate": 0.62,
    "duration_minutes": 1.5,
    "key_points_count": 5
  },
  "computed_metrics": {
    "engagement_rate": 0.0524,
    "estimated_reach": 650000,
    "click_quality_score": 0.0325,
    "discussion_rate": 0.0024,
    "estimated_ctr": 0.0075,
    "attention_compression": 3.33
  },
  "hook": "What if 1 habit could change everything?",
  "thumbnail_desc": "Person holding cash, shocked expression, red background",
  "pacing": "fast",
  "pattern_notes": ""
}
```

`computed_metrics` are derived automatically from `raw_metrics` using formulas in `config/engagement_formulas.yaml`. The server applies pure math — Claude interprets the results.

**Engagement formulas:**
```yaml
engagement_rate:   "(likes + comments) / views"
estimated_reach:   "views * 1.3"
click_quality_score: "retention_rate * engagement_rate"
discussion_rate:   "comments / views"
estimated_ctr:     "likes / views * 0.15"
attention_compression: "key_points_count / duration_minutes"
```

**Global index** at `competitor_intelligence/_global_index.json` aggregates hooks, thumbnails, pacing, and patterns across all channels. Use `pipeline_query_competitor_data` to filter.

---

## Three Entry Points

### Entry Point 1 — New channel, no data

1. `pipeline_save_channel_config` — define channel DNA
2. `pipeline_create_channel_skills` — create 5 skill template files
3. Develop each skill with `pipeline_update_channel_skill` in dialogue with the user
4. `pipeline_create_project(channel_id=...)` — auto-seeds project_config from channel defaults
5. Proceed with standard production workflow

### Entry Point 2 — New channel + competitor research

1. Add competitor channels via `pipeline_add_competitor_channel`
2. Add competitor videos via `pipeline_add_competitor_video` (engagement formulas applied automatically)
3. Import transcripts via `pipeline_import_transcript`
4. Read `pipeline_get_competitor_index` and analyze patterns
5. Build channel skills informed by what works for competitors
6. Continue with Entry Point 1 from step 4

### Entry Point 3 — Channel already running

1. `pipeline_get_channel_config` — load existing DNA
2. `pipeline_get_channel_skill(channel_id, "SCENARIO_WRITER")` — load writing guide
3. `pipeline_get_channel_skill(channel_id, "HOOK_ENGINE")` — load hook guide
4. `pipeline_get_channel_skill(channel_id, "CHANNEL_VOICE")` — load voice guide
5. `pipeline_get_analytics` — review what has worked
6. `pipeline_create_project(channel_id=...)` — start new scenario with inherited defaults

---

## Responsibility Boundary

| Claude (AI) | Server |
|---|---|
| Reads competitor transcripts, analyzes patterns | Stores and returns raw text |
| Decides which hooks/thumbnails work and why | Returns raw records |
| Writes and evolves channel skills | Saves/loads .md files |
| Interprets engagement metrics | Applies formula math only |
| Identifies pattern clusters | Returns filtered index rows |
| Develops channel strategy with user | Never interprets, decides, or analyzes |
