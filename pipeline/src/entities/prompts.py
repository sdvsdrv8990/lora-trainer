from typing import Literal
from pydantic import BaseModel, Field


class FramePrompt(BaseModel):
    frame_id: int
    scene_id: int
    start: float
    end: float
    duration: float
    prompt: str
    negative_prompt: str = ""
    type: Literal["image", "animation"] = "image"
    animation_duration_sec: float | None = None


class PromptBatch(BaseModel):
    batch_id: int
    frames: list[FramePrompt]


class ImagePromptsData(BaseModel):
    batch_size: int
    total_frames: int
    batches: list[PromptBatch] = Field(min_length=1)
