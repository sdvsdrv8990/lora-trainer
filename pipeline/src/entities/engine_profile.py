from typing import Optional
from pydantic import BaseModel, Field


class LoraConfig(BaseModel):
    enabled: bool = False
    path: Optional[str] = None


class GenerationParams(BaseModel):
    steps: int = 25
    guidance_scale: float = 7.5
    width: int = 512
    height: int = 512


class EngineProfile(BaseModel):
    name: str
    model_id: Optional[str] = None
    engine: str = "stub"
    device: str = "cpu"
    fallback_device: str = "cpu"
    dtype: Optional[str] = None
    lora: LoraConfig = Field(default_factory=LoraConfig)
    default_params: GenerationParams = Field(default_factory=GenerationParams)
