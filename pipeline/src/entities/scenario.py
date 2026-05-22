from pydantic import BaseModel, Field


class TTSParams(BaseModel):
    emotion: str = "neutral"
    pause_before: float = Field(default=0.0, ge=0.0)
    pause_after: float = Field(default=0.0, ge=0.0)
    stress: list[str] = Field(default_factory=list)
    speed: float = Field(default=1.0, gt=0.0)


class TTSInstruction(BaseModel):
    scene_id: int = Field(ge=1)
    chapter: str = ""
    text: str = Field(min_length=1)
    tts: TTSParams = Field(default_factory=TTSParams)
    metadata: dict[str, str] = Field(default_factory=dict)


class TTSBatch(BaseModel):
    scenes: list[TTSInstruction] = Field(min_length=1)

