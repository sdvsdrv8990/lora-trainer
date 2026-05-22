from pydantic import BaseModel, Field


class WordTiming(BaseModel):
    word: str
    start: float
    end: float


class TimelineEntry(BaseModel):
    scene_id: int
    chapter: str = ""
    audio_file: str
    start: float
    end: float
    duration: float
    text: str
    words: list[WordTiming] = Field(default_factory=list)
