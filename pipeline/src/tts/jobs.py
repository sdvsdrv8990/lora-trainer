import json
import threading
from datetime import datetime
from pathlib import Path

from src.scenario import builder
from src.tts.engine import get_tts_engine

_LOCK = threading.Lock()
_JOBS: dict[str, threading.Event] = {}


def _now() -> str:
    return datetime.now().isoformat()


def _status_path(workspace: Path) -> Path:
    return workspace / "md" / "voiceover_status.json"


def _job_key(workspace: Path) -> str:
    return str(workspace.resolve())


def _write_status(workspace: Path, payload: dict) -> dict:
    workspace.joinpath("md").mkdir(parents=True, exist_ok=True)
    current = read_status(workspace)
    current.update(payload)
    current["updated_at"] = _now()
    _status_path(workspace).write_text(json.dumps(current, indent=2, ensure_ascii=False))
    return current


def read_status(workspace: Path) -> dict:
    path = _status_path(workspace)
    if not path.exists():
        return {
            "status": "idle",
            "message": "No scenario has been submitted yet.",
            "total_scenes": 0,
            "completed_scenes": 0,
            "audio_files": [],
            "updated_at": None,
        }
    return json.loads(path.read_text())


def mark_scenario_received(workspace: Path, scene_count: int, tts_input_path: str) -> dict:
    return _write_status(
        workspace,
        {
            "status": "scenario_received",
            "message": "Scenario received. Voiceover is ready to start.",
            "total_scenes": scene_count,
            "completed_scenes": 0,
            "audio_files": [],
            "tts_input_path": tts_input_path,
            "started_at": None,
            "finished_at": None,
            "stop_requested": False,
            "error": None,
        },
    )


def stop(workspace: Path) -> dict:
    key = _job_key(workspace)
    with _LOCK:
        event = _JOBS.get(key)
        if event is not None:
            event.set()
            return _write_status(
                workspace,
                {
                    "status": "stopping",
                    "message": "Stop requested. Voiceover will stop after the current scene.",
                    "stop_requested": True,
                },
            )
    status = read_status(workspace)
    if status.get("status") in {"running", "stopping"}:
        return _write_status(
            workspace,
            {
                "status": "cancelled",
                "message": "No active worker was found; marked as cancelled.",
                "stop_requested": True,
                "finished_at": _now(),
            },
        )
    return status


def start(workspace: Path, engine_config: dict, wait: bool = False) -> dict:
    batch = builder.load_tts_batch(workspace)
    key = _job_key(workspace)
    with _LOCK:
        active = _JOBS.get(key)
        if active is not None and not active.is_set():
            status = read_status(workspace)
            status["already_running"] = True
            return status

        cancel_event = threading.Event()
        _JOBS[key] = cancel_event

    _write_status(
        workspace,
        {
            "status": "running",
            "message": "Voiceover generation is running.",
            "total_scenes": len(batch.scenes),
            "completed_scenes": 0,
            "audio_files": [],
            "started_at": _now(),
            "finished_at": None,
            "stop_requested": False,
            "error": None,
        },
    )

    def run() -> None:
        try:
            _run_job(workspace, engine_config, cancel_event)
        finally:
            with _LOCK:
                if _JOBS.get(key) is cancel_event:
                    _JOBS.pop(key, None)

    if wait:
        run()
    else:
        threading.Thread(target=run, name=f"voiceover:{key}", daemon=True).start()
    return read_status(workspace)


def _run_job(workspace: Path, engine_config: dict, cancel_event: threading.Event) -> None:
    try:
        batch = builder.load_tts_batch(workspace)
        engine = get_tts_engine(engine_config)
        audio_dir = workspace / "audio"
        audio_files: list[str] = []

        for scene in batch.scenes:
            if cancel_event.is_set():
                _write_status(
                    workspace,
                    {
                        "status": "cancelled",
                        "message": "Voiceover generation was stopped by request.",
                        "stop_requested": True,
                        "finished_at": _now(),
                    },
                )
                return

            output = engine.generate(scene, audio_dir)
            audio_files.append(str(output))
            _write_status(
                workspace,
                {
                    "status": "running",
                    "message": f"Generated scene {scene.scene_id}.",
                    "completed_scenes": len(audio_files),
                    "audio_files": audio_files,
                },
            )

        _write_status(
            workspace,
            {
                "status": "complete",
                "message": "Voiceover generation complete.",
                "completed_scenes": len(audio_files),
                "audio_files": audio_files,
                "finished_at": _now(),
                "stop_requested": False,
            },
        )
    except Exception as exc:
        _write_status(
            workspace,
            {
                "status": "failed",
                "message": "Voiceover generation failed.",
                "error": str(exc),
                "finished_at": _now(),
            },
        )

