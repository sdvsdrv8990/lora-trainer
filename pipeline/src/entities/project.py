from pydantic import BaseModel, ConfigDict
from pathlib import Path


class ProjectConfig(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    channel: str
    scenario: str


class WorkspaceContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    channel: str
    scenario: str
    workspace: Path
    existed: bool
