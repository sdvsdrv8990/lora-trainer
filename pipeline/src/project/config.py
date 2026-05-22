import json
from pathlib import Path

from src.entities.config import ProjectConfigData

_FILENAME = "project_config.json"


def save(workspace: Path, data: dict) -> dict:
    config = ProjectConfigData.model_validate(data)
    path = workspace / _FILENAME
    path.write_text(json.dumps(config.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return {"config_path": str(path), "title": config.project.title}


def load(workspace: Path) -> dict:
    path = workspace / _FILENAME
    if not path.exists():
        raise FileNotFoundError(f"{_FILENAME} not found. Run pipeline_save_project_config first.")
    return json.loads(path.read_text())
