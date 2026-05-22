import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

_STATUS_FILE = "md/remotion_status.json"
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
            "scenes_total": 0,
            "scenes_done": 0,
            "scenes_failed": 0,
            "current_scene": None,
            "current_scene_progress": 0.0,
            "eta_seconds": None,
            "scenes": [],
            "started_at": None,
            "finished_at": None,
        }
    return json.loads(path.read_text())


def _render_worker(
    workspace: Path,
    scenes: list[dict],
    cancel_event: threading.Event,
) -> None:
    from src.remotion.renderer import render_scene

    total = len(scenes)
    renders_dir = workspace / "renders" / "scenes"
    renders_dir.mkdir(parents=True, exist_ok=True)

    scene_statuses = [
        {"scene_id": s["scene_id"], "status": "pending", "path": None, "duration_sec": s.get("duration")}
        for s in scenes
    ]

    status: dict = {
        "status": "running",
        "scenes_total": total,
        "scenes_done": 0,
        "scenes_failed": 0,
        "current_scene": None,
        "current_scene_progress": 0.0,
        "eta_seconds": None,
        "scenes": scene_statuses,
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
    }
    _write_status(workspace, status)

    done = 0
    failed = 0
    start_ts = datetime.now().timestamp()

    for i, scene in enumerate(scenes):
        if cancel_event.is_set():
            status["status"] = "cancelled"
            status["finished_at"] = datetime.now().isoformat()
            for j in range(i, total):
                scene_statuses[j]["status"] = "cancelled"
            _write_status(workspace, status)
            return

        scene_id = scene["scene_id"]
        out_path = renders_dir / f"scene_{scene_id:03d}.mp4"

        status["current_scene"] = scene_id
        status["current_scene_progress"] = 0.0
        scene_statuses[i]["status"] = "running"
        _write_status(workspace, status)

        try:
            render_scene(scene, out_path)
            done += 1
            scene_statuses[i]["status"] = "complete"
            scene_statuses[i]["path"] = str(out_path.relative_to(workspace))
        except Exception as e:
            failed += 1
            scene_statuses[i]["status"] = "failed"
            scene_statuses[i]["error"] = str(e)

        status["scenes_done"] = done
        status["scenes_failed"] = failed
        status["current_scene_progress"] = 1.0

        elapsed = datetime.now().timestamp() - start_ts
        if done > 0:
            avg = elapsed / done
            remaining = (total - done) * avg
            status["eta_seconds"] = int(remaining)

        _write_status(workspace, status)

    final = "complete" if failed == 0 else ("failed" if done == 0 else "partial")
    status["status"] = final
    status["current_scene"] = None
    status["finished_at"] = datetime.now().isoformat()
    _write_status(workspace, status)


def start(
    workspace: Path,
    scenes: list[dict],
    wait: bool = False,
) -> dict:
    ws_key = str(workspace)
    cancel = threading.Event()
    _cancel_events[ws_key] = cancel

    if wait:
        _render_worker(workspace, scenes, cancel)
    else:
        t = threading.Thread(
            target=_render_worker,
            args=(workspace, scenes, cancel),
            daemon=True,
        )
        t.start()

    return read_status(workspace)


def stop(workspace: Path) -> dict:
    ws_key = str(workspace)
    ev = _cancel_events.get(ws_key)
    if ev:
        ev.set()
        return {"stopped": True}
    return {"stopped": False, "reason": "no active render job"}
