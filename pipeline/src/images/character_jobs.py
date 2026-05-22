import json
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path

_CHARACTERS_DIR = (Path(__file__).parent.parent.parent / "global_assets" / "characters" / "main").resolve()
_STATUS_FILE = "md/character_status.json"
_cancel_events: dict[str, threading.Event] = {}


def _write_status(workspace: Path, data: dict) -> None:
    path = workspace / _STATUS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def read_status(workspace: Path) -> dict:
    path = workspace / _STATUS_FILE
    if not path.exists():
        return {"status": "pending", "name": None, "png_path": None, "svg_path": None,
                "started_at": None, "finished_at": None, "error": None}
    return json.loads(path.read_text())


def list_characters() -> dict:
    _CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
    characters = []
    for svg in sorted(_CHARACTERS_DIR.glob("*.svg")):
        characters.append({
            "name": svg.stem,
            "path": f"characters/main/{svg.name}",
            "has_png": (svg.with_suffix(".png")).exists(),
        })
    return {"characters": characters, "total": len(characters)}


def _generate_worker(
    workspace: Path,
    engine,
    name: str,
    prompt: str,
    style: str,
    cancel_event: threading.Event,
) -> None:
    """Run generation in thread or inline; writes md/character_status.json throughout."""
    _CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)

    status: dict = {
        "status": "running",
        "name": name,
        "png_path": None,
        "svg_path": None,
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "error": None,
    }
    _write_status(workspace, status)

    if cancel_event.is_set():
        status["status"] = "cancelled"
        status["finished_at"] = datetime.now().isoformat()
        _write_status(workspace, status)
        return

    try:
        from src.entities.prompts import FramePrompt

        fp = FramePrompt(
            frame_id=0, scene_id=0, start=0.0, end=1.0, duration=1.0,
            prompt=f"{style} design character, simple shape, {prompt}",
            negative_prompt="realistic, photo, complex background, shadow",
        )
        with tempfile.TemporaryDirectory() as tmp:
            png_src = engine.generate(fp, Path(tmp))
            final_png = _CHARACTERS_DIR / f"{name}.png"
            shutil.copy2(png_src, final_png)

        svg_path = _CHARACTERS_DIR / f"{name}.svg"
        try:
            import vtracer
            vtracer.convert_image_to_svg_py(
                str(final_png), str(svg_path), colormode="color", filter_speckle=4
            )
        except ImportError:
            # Embed PNG as fallback SVG when vtracer is not installed
            import base64
            b64 = base64.b64encode(final_png.read_bytes()).decode()
            svg_path.write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'xmlns:xlink="http://www.w3.org/1999/xlink">'
                f'<image xlink:href="data:image/png;base64,{b64}"/></svg>'
            )

        status["status"] = "complete"
        status["png_path"] = str(final_png)
        status["svg_path"] = str(svg_path)

    except Exception as e:
        status["status"] = "failed"
        status["error"] = str(e)

    status["finished_at"] = datetime.now().isoformat()
    _write_status(workspace, status)


def start(
    workspace: Path,
    engine,
    name: str,
    prompt: str,
    style: str = "flat",
    wait: bool = False,
) -> dict:
    """Start character generation. wait=True blocks; wait=False returns immediately with status=running."""
    ws_key = str(workspace)
    cancel = threading.Event()
    _cancel_events[ws_key] = cancel

    if wait:
        _generate_worker(workspace, engine, name, prompt, style, cancel)
    else:
        t = threading.Thread(
            target=_generate_worker,
            args=(workspace, engine, name, prompt, style, cancel),
            daemon=True,
        )
        t.start()
    return read_status(workspace)
