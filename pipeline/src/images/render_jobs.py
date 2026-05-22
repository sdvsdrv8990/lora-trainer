import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.images import layout_store

_STATUS_FILE = "md/render_frames_status.json"
_cancel_events: dict[str, threading.Event] = {}


def _write_status(workspace: Path, data: dict) -> None:
    path = workspace / _STATUS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def read_status(workspace: Path) -> dict:
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


def _render_worker(
    workspace: Path,
    engine,
    frame_ids: Optional[list[int]],
    cancel_event: threading.Event,
) -> None:
    from src.images.compositor import Compositor

    layout = layout_store.load_layout(workspace)
    output_dir = workspace / "images"
    compositor = Compositor(layout.canvas, output_dir, image_engine=engine, workspace=workspace)

    frames = [f for f in layout.frames if frame_ids is None or f.frame_id in frame_ids]
    total = len(frames)

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
    for frame in frames:
        if cancel_event.is_set():
            status["status"] = "cancelled"
            status["finished_at"] = datetime.now().isoformat()
            _write_status(workspace, status)
            return
        try:
            compositor.render_frame(frame)
            completed += 1
        except Exception as e:
            failed.append({"frame_id": frame.frame_id, "error": str(e)})
        status["completed_frames"] = completed
        status["failed_frames"] = failed
        _write_status(workspace, status)

    final = "complete" if not failed else "failed"
    status["status"] = final
    status["finished_at"] = datetime.now().isoformat()
    _write_status(workspace, status)


def start(
    workspace: Path,
    engine,
    frame_ids: Optional[list[int]] = None,
    wait: bool = False,
) -> dict:
    ws_key = str(workspace)
    cancel = threading.Event()
    _cancel_events[ws_key] = cancel

    if wait:
        _render_worker(workspace, engine, frame_ids, cancel)
    else:
        t = threading.Thread(
            target=_render_worker,
            args=(workspace, engine, frame_ids, cancel),
            daemon=True,
        )
        t.start()
    return read_status(workspace)


def preview_frame(workspace: Path, engine, frame_id: int) -> dict:
    """Render a single frame synchronously and return the output path."""
    from src.images.compositor import Compositor

    layout = layout_store.load_layout(workspace)
    frame = next((f for f in layout.frames if f.frame_id == frame_id), None)
    if frame is None:
        raise ValueError(f"Frame {frame_id} not found in scene_layout.json")

    output_dir = workspace / "images"
    compositor = Compositor(layout.canvas, output_dir, image_engine=engine, workspace=workspace)
    out = compositor.render_frame(frame)
    return {"frame_id": frame_id, "path": str(out), "exists": out.exists()}


def list_frames(workspace: Path) -> dict:
    layout = layout_store.load_layout(workspace)
    output_dir = workspace / "images"
    frames = []
    ready = 0
    for f in layout.frames:
        rel = f"images/frame_{f.frame_id:04d}.png"
        exists = (output_dir / f"frame_{f.frame_id:04d}.png").exists()
        if exists:
            ready += 1
        frames.append({"frame_id": f.frame_id, "path": rel, "exists": exists})
    return {
        "frames": frames,
        "total_expected": layout.total_frames,
        "total_ready": ready,
    }
