import json
import subprocess
from pathlib import Path
from typing import Optional

_STATUS_FILE = "md/render_status.json"


def _load_timeline(workspace: Path) -> list:
    path = workspace / "md" / "timeline.json"
    if not path.exists():
        raise FileNotFoundError("timeline.json not found. Run pipeline_build_timeline first.")
    return json.loads(path.read_text())


def _load_frame_list(workspace: Path) -> list[dict]:
    """Return flat list of {frame_id, scene_id, start, duration}.

    Tries scene_layout.json first (new compositing workflow),
    falls back to image_prompts.json (legacy prompt workflow).
    """
    layout_path = workspace / "md" / "scene_layout.json"
    prompts_path = workspace / "md" / "image_prompts.json"

    if layout_path.exists():
        data = json.loads(layout_path.read_text())
        return [
            {
                "frame_id": f["frame_id"],
                "scene_id": f["scene_id"],
                "start": f["start"],
                "duration": round(f["end"] - f["start"], 3),
            }
            for f in data.get("frames", [])
        ]

    if prompts_path.exists():
        from src.entities.prompts import ImagePromptsData
        prompts = ImagePromptsData.model_validate(json.loads(prompts_path.read_text()))
        return [
            {
                "frame_id": frame.frame_id,
                "scene_id": frame.scene_id,
                "start": frame.start,
                "duration": frame.duration,
            }
            for batch in prompts.batches
            for frame in batch.frames
        ]

    raise FileNotFoundError(
        "Neither scene_layout.json nor image_prompts.json found. "
        "Run pipeline_submit_scene_layouts or pipeline_submit_prompts first."
    )


def _get_scene_frames(frame_list: list[dict], scene_id: int) -> list[dict]:
    return sorted(
        [f for f in frame_list if f["scene_id"] == scene_id],
        key=lambda f: f["start"],
    )


def _read_render_status(workspace: Path) -> dict:
    path = workspace / _STATUS_FILE
    if not path.exists():
        return {
            "assemble_status": "pending",
            "concat_status": "pending",
            "scenes_done": 0,
            "scenes_total": 0,
            "output_file": None,
            "error": None,
        }
    return json.loads(path.read_text())


def _write_render_status(workspace: Path, data: dict) -> None:
    path = workspace / _STATUS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _run_ffmpeg(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-2000:]}")


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(path)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    for stream in data.get("streams", []):
        if stream.get("codec_type") in ("audio", "video"):
            dur = stream.get("duration")
            if dur:
                return round(float(dur), 3)
    return 0.0


def assemble_scenes(workspace: Path) -> dict:
    """Build one MP4 clip per scene (frames + audio) into renders/scenes/."""
    timeline = _load_timeline(workspace)
    frame_list = _load_frame_list(workspace)
    images_dir = workspace / "images"
    scenes_dir = workspace / "renders" / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)

    total = len(timeline)
    status: dict = {
        "assemble_status": "running",
        "concat_status": "pending",
        "scenes_done": 0,
        "scenes_total": total,
        "output_file": None,
        "error": None,
    }
    _write_render_status(workspace, status)

    for i, entry in enumerate(timeline):
        scene_id = entry["scene_id"]
        audio_file = Path(entry["audio_file"])
        output_file = scenes_dir / f"scene_{scene_id:03d}.mp4"

        frames = _get_scene_frames(frame_list, scene_id)
        if not frames:
            raise FileNotFoundError(
                f"No frames found for scene {scene_id}. Run pipeline_render_frames first."
            )

        for frame in frames:
            img_path = images_dir / f"frame_{frame['frame_id']:04d}.png"
            if not img_path.exists():
                raise FileNotFoundError(
                    f"Image not found: frame_{frame['frame_id']:04d}.png. "
                    "Run pipeline_render_frames first."
                )

        if len(frames) == 1:
            img_path = images_dir / f"frame_{frames[0]['frame_id']:04d}.png"
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-t", str(entry["duration"]),
                "-i", str(img_path),
                "-i", str(audio_file),
                "-c:v", "libx264", "-tune", "stillimage",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p", "-shortest",
                str(output_file),
            ]
        else:
            input_args: list[str] = []
            for frame in frames:
                img_path = images_dir / f"frame_{frame['frame_id']:04d}.png"
                input_args += ["-loop", "1", "-t", str(frame["duration"]), "-i", str(img_path)]

            n = len(frames)
            concat_filter = "".join(f"[{j}:v]" for j in range(n)) + f"concat=n={n}:v=1:a=0[v]"
            cmd = (
                ["ffmpeg", "-y"]
                + input_args
                + ["-i", str(audio_file)]
                + ["-filter_complex", concat_filter]
                + ["-map", "[v]", "-map", f"{n}:a"]
                + ["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-shortest"]
                + [str(output_file)]
            )

        try:
            _run_ffmpeg(cmd)
        except RuntimeError as e:
            status["assemble_status"] = "failed"
            status["error"] = str(e)
            _write_render_status(workspace, status)
            raise

        status["scenes_done"] = i + 1
        _write_render_status(workspace, status)

    status["assemble_status"] = "complete"
    _write_render_status(workspace, status)

    return {
        "status": "complete",
        "scenes_total": total,
        "scenes_done": total,
        "output_dir": str(scenes_dir),
    }


def concat_scenes(workspace: Path) -> dict:
    """Concatenate renders/scenes/scene_*.mp4 into renders/<scenario>_draft.mp4."""
    scenes_dir = workspace / "renders" / "scenes"
    if not scenes_dir.exists():
        raise FileNotFoundError(
            "renders/scenes/ not found. Run pipeline_assemble_scenes first."
        )

    scene_files = sorted(scenes_dir.glob("scene_*.mp4"))
    if not scene_files:
        raise FileNotFoundError("No scene .mp4 files found. Run pipeline_assemble_scenes first.")

    scenario_name = workspace.name
    output_file = workspace / "renders" / f"{scenario_name}_draft.mp4"
    concat_list = workspace / "renders" / "concat_list.txt"
    concat_list.write_text("\n".join(f"file '{f}'" for f in scene_files))

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(output_file),
    ]

    try:
        _run_ffmpeg(cmd)
    except RuntimeError as e:
        status = _read_render_status(workspace)
        status["concat_status"] = "failed"
        status["error"] = str(e)
        _write_render_status(workspace, status)
        raise

    duration = _probe_duration(output_file)

    status = _read_render_status(workspace)
    status["concat_status"] = "complete"
    status["output_file"] = str(output_file)
    _write_render_status(workspace, status)

    return {
        "status": "complete",
        "output_file": str(output_file),
        "duration": duration,
    }


def read_render_status(workspace: Path) -> dict:
    return _read_render_status(workspace)


def get_output_file(workspace: Path) -> dict:
    scenario_name = workspace.name
    output_file = workspace / "renders" / f"{scenario_name}_draft.mp4"
    exists = output_file.exists()
    size_mb = 0.0
    duration_sec = 0.0
    if exists:
        size_mb = round(output_file.stat().st_size / (1024 * 1024), 2)
        try:
            duration_sec = _probe_duration(output_file)
        except Exception:
            pass
    return {
        "path": str(output_file),
        "size_mb": size_mb,
        "duration_sec": duration_sec,
        "exists": exists,
    }
