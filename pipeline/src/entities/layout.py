from typing import Annotated, Literal, Optional, Union
from pydantic import BaseModel, Field


class AssetLayer(BaseModel):
    id: str
    type: Literal["asset"]
    asset_path: str
    x: int = 0
    y: int = 0
    scale: float = 1.0
    opacity: float = 1.0
    flip_x: bool = False


class CharacterLayer(BaseModel):
    id: str
    type: Literal["character"]
    asset_path: str
    color: str = "#808080"
    emotion: str = "neutral"
    x: int = 0
    y: int = 0
    scale: float = 0.8
    flip_x: bool = False


class SpeechBubbleLayer(BaseModel):
    id: str
    type: Literal["speech_bubble"]
    template: str = "oval_right"
    text: str
    font: str = "Arial Bold"
    font_size: int = 32
    color: str = "#000000"
    x: int = 0
    y: int = 0


class GeneratedLayer(BaseModel):
    id: str
    type: Literal["generated"]
    prompt: str
    negative_prompt: str = ""
    x: int = 0
    y: int = 0
    scale: float = 1.0
    width: int = 512
    height: int = 512


class TextLayer(BaseModel):
    id: str
    type: Literal["text"]
    text: str
    font: str = "Arial"
    font_size: int = 32
    color: str = "#000000"
    x: int = 0
    y: int = 0


class CompositeComponent(BaseModel):
    role: str
    asset_id: str
    z_index: int = 0


class CharacterCompositeLayer(BaseModel):
    id: str
    type: Literal["character_composite"]
    group_id: str
    components: list[CompositeComponent] = Field(default_factory=list)
    color: str = "#808080"
    save_as_comp: bool = False
    x: int = 0
    y: int = 300
    scale: float = 0.8
    flip_x: bool = False


class AssetCompositeLayer(BaseModel):
    id: str
    type: Literal["asset_composite"]
    group_id: str
    components: list[CompositeComponent] = Field(default_factory=list)
    save_as_comp: bool = False
    x: int = 0
    y: int = 0
    scale: float = 1.0


Layer = Annotated[
    Union[
        AssetLayer, CharacterLayer, SpeechBubbleLayer, GeneratedLayer, TextLayer,
        CharacterCompositeLayer, AssetCompositeLayer,
    ],
    Field(discriminator="type"),
]


class Canvas(BaseModel):
    width: int = 1920
    height: int = 1080


class FrameLayout(BaseModel):
    frame_id: int
    scene_id: int
    start: float
    end: float
    background: str = "#FFFFFF"
    layers: list[Layer] = []
    appearance_order: list[str] = []
    notes: str = ""


class SceneLayout(BaseModel):
    total_frames: int
    canvas: Canvas = Field(default_factory=Canvas)
    frames: list[FrameLayout]
