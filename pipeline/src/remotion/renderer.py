import json
import subprocess
from pathlib import Path

_RENDER_SCRIPT = Path(__file__).parent.parent.parent / "remotion" / "render.ts"
_NODE = "node"
_TSNODE = Path(__file__).parent.parent.parent / "remotion" / "node_modules" / ".bin" / "ts-node"


def render_scene(scene_json: dict, output_path: Path) -> Path:
    """Call the Remotion render.ts script for a single scene."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scene_tmp = output_path.parent / f"_scene_{scene_json['scene_id']:03d}_layout.json"
    scene_tmp.write_text(json.dumps(scene_json, ensure_ascii=False))

    try:
        proc = subprocess.run(
            [str(_TSNODE), "--project", str(_RENDER_SCRIPT.parent.parent / "tsconfig.json"),
             str(_RENDER_SCRIPT), str(scene_tmp), str(output_path)],
            capture_output=True,
            text=True,
            cwd=str(_RENDER_SCRIPT.parent),
            timeout=300,
        )
    finally:
        scene_tmp.unlink(missing_ok=True)

    if proc.returncode != 0:
        raise RuntimeError(f"Remotion render failed: {proc.stderr}")

    return output_path


def render_scene_preview(scene_json: dict, time: float, output_path: Path) -> Path:
    """Extract a PNG frame at the given time offset from a rendered scene MP4 via FFmpeg."""
    mp4_path = output_path.parent.parent / "scenes" / f"scene_{scene_json['scene_id']:03d}.mp4"
    if not mp4_path.exists():
        raise FileNotFoundError(f"Scene MP4 not found: {mp4_path}. Run pipeline_render_scene first.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", str(time),
            "-i", str(mp4_path),
            "-frames:v", "1",
            "-q:v", "2",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg frame extraction failed: {proc.stderr}")
    return output_path


def get_render_script_path() -> Path:
    return _RENDER_SCRIPT


def get_tsnode_path() -> Path:
    return _TSNODE
