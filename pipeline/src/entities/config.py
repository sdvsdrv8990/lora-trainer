from typing import Literal
from datetime import datetime
from pydantic import BaseModel, Field


class ProjectInfo(BaseModel):
    title: str
    description: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class StyleConfig(BaseModel):
    type: Literal["slideshow", "animation", "mixed"] = "slideshow"
    mood: str = "neutral"
    visual_references: list[str] = Field(default_factory=list)


class FrameRules(BaseModel):
    mode: Literal["dynamic", "fixed", "manual"] = "dynamic"
    default_duration_sec: float = 5.0
    min_duration_sec: float = 1.0
    max_duration_sec: float = 15.0
    change_triggers: list[str] = Field(default_factory=list)
    scene_count_preference: str = "auto"


class AudioConfig(BaseModel):
    tts_engine: str = "espeak"
    default_emotion: str = "neutral"
    default_speed: float = 1.0
    pause_between_scenes_sec: float = 0.5


class PromptsConfig(BaseModel):
    batch_size: int = 50
    style_prefix: str = ""
    negative_prompt: str = ""


class UserPreferences(BaseModel):
    analytics_review_before_scenario: bool = True
    show_asset_overuse_warnings: bool = True
    auto_save_comp_assets: bool = True
    preferred_composite_style: str = "modular"
    scene_count: str = "auto"
    frame_change_conditions: list[str] = Field(default_factory=list)
    hook_style_preference: str = ""
    reward_type_preference: str = ""
    custom_notes: str = ""


class ProjectConfigData(BaseModel):
    project: ProjectInfo
    style: StyleConfig = Field(default_factory=StyleConfig)
    frame_rules: FrameRules = Field(default_factory=FrameRules)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    prompts: PromptsConfig = Field(default_factory=PromptsConfig)
    user_preferences: UserPreferences = Field(default_factory=UserPreferences)
