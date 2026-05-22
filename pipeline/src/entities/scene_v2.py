from typing import Any, Dict, Literal, Optional, Union
from pydantic import BaseModel, Field


class SceneEventAction(str):
    pass


class SceneEvent(BaseModel):
    time: float
    action: Literal["show", "hide", "change_state", "trigger_preset", "show_text", "show_number"]
    target: Optional[str] = None
    component: Optional[str] = None
    state: Optional[Dict[str, str]] = None
    value: Optional[Union[str, float, int]] = None
    preset: Optional[str] = None
    position: Optional[Dict[str, float]] = None
    style: Optional[str] = None


class CanvasV2(BaseModel):
    width: int = 1920
    height: int = 1080


class SceneLayoutV2(BaseModel):
    scene_id: int
    chapter: str = ""
    audio_file: str
    duration: float
    fps: int = 30
    canvas: CanvasV2 = Field(default_factory=CanvasV2)
    events: list[SceneEvent] = Field(default_factory=list)


class MultiSceneLayoutV2(BaseModel):
    _schema_version: str = "v2"
    scenes: list[SceneLayoutV2]
