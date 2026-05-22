"""Channel Config and Skills system — per-channel production DNA."""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

_SERVER_ROOT = Path(__file__).parent.parent.parent
_CHANNELS_ROOT = _SERVER_ROOT / "channels"

_SKILL_NAMES = ["SCENARIO_WRITER", "IMAGE_PROMPTS", "FRAME_RULES", "HOOK_ENGINE", "CHANNEL_VOICE"]

_SKILL_TEMPLATES = {
    "SCENARIO_WRITER": """\
# Scenario Writer — {channel_name}

## Channel Voice
[Fill based on channel_config narrative_style]

## Preferred Structures
[Fill based on competitor analysis and user decisions]

## Structure Template
HOOK (0-Xs): [preferred_hook_type]
SETUP (Xs): [context rules]
DISRUPTION (Xs): [twist rules]
ESCALATION (Xs): [stakes rules]
PAYOFF (Xs): [delivery rules]
AFTERTASTE (Xs): [closing rules]

## Frame Change Rules
New frame when:
[Fill from channel_config frame_rules.change_triggers]

## Reset Point Rule
Every [reset_point_interval_sec] seconds minimum.

## What to Avoid
[Fill from competitor analysis + user decisions]
""",
    "IMAGE_PROMPTS": """\
# Image Prompts — {channel_name}

## Required Prefix
[Fill from channel_config prompt_style.image_prompt_prefix]

## Required Negative
[Fill from channel_config prompt_style.image_negative_prompt]

## Character Rules
[Fill from channel_config prompt_style.character_description]

## Object Rules
[Fill from channel_config prompt_style.object_style]

## Scene Rules by Module
HOOK scene: [rules]
ESCALATION scene: [rules]
PAYOFF scene: [rules]
""",
    "FRAME_RULES": """\
# Frame Rules — {channel_name}

## Change Triggers
[Fill from channel_config frame_rules.change_triggers]

## Average Cut Interval
[avg_cut_interval_sec] seconds

## Reset Points
Every [reset_point_interval_sec] seconds minimum.

## Appearance Animation
[appearance_animation: true/false]

## Module-Specific Rules
HOOK: [rules]
SETUP: [rules]
DISRUPTION: [rules]
ESCALATION: [rules]
PAYOFF: [rules]
""",
    "HOOK_ENGINE": """\
# Hook Engine — {channel_name}

## Preferred Hook Types
[Fill from channel_config narrative_style.hook_preferences]

## Opening Techniques
[Fill based on competitor analysis]

## Reset Point Templates
[Fill based on channel style and competitor analysis]

## Reward Types Used
[Fill from channel_config narrative_style.reward_type]

## Structure Patterns
[Fill based on competitor analysis + user decisions]
""",
    "CHANNEL_VOICE": """\
# Channel Voice — {channel_name}

## Tone
[Fill from channel_config narrative_style.tone]

## Language Style
[Fill from channel_config narrative_style.language_style]

## Personality
[Fill from channel_config narrative_style.personality]

## Storytelling Pattern
[Fill from channel_config narrative_style.storytelling_pattern]

## What to Avoid
[Fill based on user decisions]
""",
}


def _channel_dir(channel_id: str) -> Path:
    return _CHANNELS_ROOT / channel_id


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def save_channel_config(channel_id: str, config: dict) -> dict:
    config["channel_id"] = channel_id
    config.setdefault("created_at", datetime.now().isoformat())
    config["skills_path"] = f"channels/{channel_id}/skills/"
    config["version"] = config.get("version", "1.0")
    path = _channel_dir(channel_id) / "channel_config.json"
    _write_json(path, config)
    return {"channel_id": channel_id, "saved": True, "path": str(path)}


def get_channel_config(channel_id: str) -> dict:
    path = _channel_dir(channel_id) / "channel_config.json"
    if not path.exists():
        raise FileNotFoundError(f"Channel config not found for '{channel_id}'")
    return _read_json(path)


def update_channel_config(channel_id: str, field: str, value) -> dict:
    path = _channel_dir(channel_id) / "channel_config.json"
    if not path.exists():
        raise FileNotFoundError(f"Channel config not found for '{channel_id}'")
    data = _read_json(path)
    parts = field.split(".")
    d = data
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = value
    _write_json(path, data)
    return {"channel_id": channel_id, "field": field, "updated": True}


def list_channels() -> dict:
    if not _CHANNELS_ROOT.exists():
        return {"channels": [], "total": 0}
    channels = []
    for ch_dir in sorted(_CHANNELS_ROOT.iterdir()):
        if ch_dir.is_dir():
            cfg_path = ch_dir / "channel_config.json"
            if cfg_path.exists():
                try:
                    data = _read_json(cfg_path)
                    channels.append({
                        "channel_id": ch_dir.name,
                        "channel_name": data.get("channel_name", ch_dir.name),
                        "niche": data.get("niche", ""),
                        "target_platform": data.get("target_platform", ""),
                    })
                except Exception:
                    pass
    return {"channels": channels, "total": len(channels)}


def create_channel_skills(channel_id: str) -> dict:
    skills_dir = _channel_dir(channel_id) / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Load channel name for templates
    try:
        cfg = get_channel_config(channel_id)
        channel_name = cfg.get("channel_name", channel_id)
    except FileNotFoundError:
        channel_name = channel_id

    created = []
    for skill_name in _SKILL_NAMES:
        skill_path = skills_dir / f"{skill_name}.md"
        if not skill_path.exists():
            content = _SKILL_TEMPLATES[skill_name].format(channel_name=channel_name)
            skill_path.write_text(content, encoding="utf-8")
            created.append(skill_name)

    return {
        "channel_id": channel_id,
        "skills_dir": str(skills_dir),
        "created": created,
        "skill_names": _SKILL_NAMES,
    }


def update_channel_skill(channel_id: str, skill_name: str, content: str) -> dict:
    skill_name = skill_name.upper()
    skills_dir = _channel_dir(channel_id) / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skills_dir / f"{skill_name}.md"
    skill_path.write_text(content, encoding="utf-8")
    return {
        "channel_id": channel_id,
        "skill_name": skill_name,
        "updated": True,
        "size_bytes": len(content.encode()),
    }


def get_channel_skill(channel_id: str, skill_name: str) -> dict:
    skill_name = skill_name.upper()
    skill_path = _channel_dir(channel_id) / "skills" / f"{skill_name}.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill '{skill_name}' not found for channel '{channel_id}'")
    content = skill_path.read_text(encoding="utf-8")
    return {
        "channel_id": channel_id,
        "skill_name": skill_name,
        "content": content,
    }


def list_channel_skills(channel_id: str) -> dict:
    skills_dir = _channel_dir(channel_id) / "skills"
    if not skills_dir.exists():
        return {"channel_id": channel_id, "skills": [], "total": 0}
    skills = []
    for skill_file in sorted(skills_dir.glob("*.md")):
        skills.append({
            "skill_name": skill_file.stem,
            "last_updated": datetime.fromtimestamp(skill_file.stat().st_mtime).isoformat(),
            "size_bytes": skill_file.stat().st_size,
        })
    return {"channel_id": channel_id, "skills": skills, "total": len(skills)}


def build_project_config_from_channel(channel_id: str) -> dict:
    """Build a base project_config inheriting channel defaults."""
    try:
        cfg = get_channel_config(channel_id)
    except FileNotFoundError:
        return {}

    visual_style = cfg.get("visual_style", {})
    frame_rules = cfg.get("frame_rules", {})
    audio_style = cfg.get("audio_style", {})
    prompt_style = cfg.get("prompt_style", {})

    return {
        "channel_id": channel_id,
        "style": {
            "type": visual_style.get("animation_type", "slideshow"),
            "mood": audio_style.get("music_mood", "neutral"),
            "visual_references": visual_style.get("visual_references", []),
        },
        "frame_rules": {
            "mode": frame_rules.get("mode", "dynamic"),
            "change_triggers": frame_rules.get("change_triggers", []),
            "scene_count_preference": "auto",
        },
        "visual_rhythm": {
            "pace": "moderate",
            "avg_cut_interval": frame_rules.get("avg_cut_interval_sec", 3.0),
            "pattern": "escalating",
            "micro_motion": False,
            "pattern_interrupts": True,
        },
        "audio": {
            "tts_engine": "espeak",
            "default_speed": audio_style.get("tts_speed", 1.0),
            "pause_between_scenes_sec": audio_style.get("pause_between_scenes_sec", 0.5),
        },
        "prompts": {
            "batch_size": 50,
            "style_prefix": prompt_style.get("image_prompt_prefix", ""),
            "negative_prompt": prompt_style.get("image_negative_prompt", ""),
        },
        "user_preferences": {
            "analytics_review_before_scenario": True,
            "competitor_review_before_scenario": False,
            "show_asset_overuse_warnings": True,
            "auto_save_comp_assets": True,
            "scene_count": "auto",
            "frame_change_conditions": frame_rules.get("change_triggers", []),
            "hook_style_preference": "",
            "reward_type_preference": cfg.get("narrative_style", {}).get("reward_type", ""),
            "platform_target": cfg.get("target_platform", ""),
            "custom_notes": "",
        },
    }
