import json
from pathlib import Path

from src.entities.prompts import ImagePromptsData

_FILENAME = "image_prompts.json"


def save_prompts(workspace: Path, data: dict) -> dict:
    prompts = ImagePromptsData.model_validate(data)
    path = workspace / "md" / _FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prompts.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return {
        "prompts_path": str(path),
        "total_frames": prompts.total_frames,
        "batch_count": len(prompts.batches),
        "batch_size": prompts.batch_size,
    }


def get_batch(workspace: Path, batch_id: int) -> dict:
    path = workspace / "md" / _FILENAME
    if not path.exists():
        raise FileNotFoundError(f"{_FILENAME} not found. Run pipeline_submit_prompts first.")
    data = json.loads(path.read_text())
    prompts = ImagePromptsData.model_validate(data)
    for batch in prompts.batches:
        if batch.batch_id == batch_id:
            return batch.model_dump(mode="json")
    raise ValueError(f"Batch {batch_id} not found. Available: 1..{len(prompts.batches)}")
