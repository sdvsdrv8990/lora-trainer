import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.entities.prompts import ImagePromptsData

_STATUS_FILE = "md/generation_status.json"
_PROMPTS_FILE = "md/image_prompts.json"


def _load_prompts(workspace: Path) -> ImagePromptsData:
    path = workspace / _PROMPTS_FILE
    if not path.exists():
        raise FileNotFoundError(f"{_PROMPTS_FILE} not found. Run pipeline_submit_prompts first.")
    return ImagePromptsData.model_validate(json.loads(path.read_text()))


def _read_status(workspace: Path) -> dict:
    path = workspace / _STATUS_FILE
    if not path.exists():
        return {
            "status": "pending",
            "total_frames": 0,
            "completed_frames": 0,
            "failed_frames": [],
            "started_at": None,
            "finished_at": None,
        }
    return json.loads(path.read_text())


def _write_status(workspace: Path, data: dict) -> None:
    path = workspace / _STATUS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def generate(workspace: Path, engine, batch_id: Optional[int] = None) -> dict:
    """Generate images for all batches or a specific batch_id.

    Writes images to images/frame_{frame_id:04d}.png.
    Tracks progress in md/generation_status.json.
    """
    prompts = _load_prompts(workspace)
    output_dir = workspace / "images"

    frames_to_generate = []
    for batch in prompts.batches:
        if batch_id is None or batch.batch_id == batch_id:
            frames_to_generate.extend(batch.frames)

    if batch_id is not None and not frames_to_generate:
        raise ValueError(f"Batch {batch_id} not found. Available: 1..{len(prompts.batches)}")

    total = len(frames_to_generate)
    status: dict = {
        "status": "running",
        "total_frames": total,
        "completed_frames": 0,
        "failed_frames": [],
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
    }
    _write_status(workspace, status)

    completed = 0
    failed: list = []
    for frame in frames_to_generate:
        try:
            engine.generate(frame, output_dir)
            completed += 1
        except Exception as e:
            failed.append({"frame_id": frame.frame_id, "error": str(e)})

        status["completed_frames"] = completed
        status["failed_frames"] = failed
        _write_status(workspace, status)

    final_status = "complete" if not failed else "failed"
    status["status"] = final_status
    status["finished_at"] = datetime.now().isoformat()
    _write_status(workspace, status)

    return {
        "status": final_status,
        "total_frames": total,
        "completed_frames": completed,
        "output_dir": str(output_dir),
    }


def read_status(workspace: Path) -> dict:
    return _read_status(workspace)


def list_images(workspace: Path) -> dict:
    """Return per-frame existence check against image_prompts.json frame list."""
    prompts = _load_prompts(workspace)
    images_dir = workspace / "images"

    all_frames = [f for batch in prompts.batches for f in batch.frames]
    images = []
    ready = 0
    for frame in all_frames:
        rel = f"images/frame_{frame.frame_id:04d}.png"
        exists = (images_dir / f"frame_{frame.frame_id:04d}.png").exists()
        if exists:
            ready += 1
        images.append({"frame_id": frame.frame_id, "path": rel, "exists": exists})

    return {
        "images": images,
        "total_expected": len(all_frames),
        "total_ready": ready,
    }
