import json
import subprocess
from pathlib import Path

from src.scenario.builder import load_tts_batch


def _ffprobe_duration(audio_file: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            str(audio_file),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "audio":
            return float(stream.get("duration", 0.0))
    return 0.0


def build_timeline(workspace: Path) -> list[dict]:
    """Read all scene audio files, measure durations, write md/timeline.json."""
    batch = load_tts_batch(workspace)
    audio_dir = workspace / "audio"
    timeline: list[dict] = []
    offset = 0.0

    for scene in batch.scenes:
        audio_file = audio_dir / f"scene_{scene.scene_id:03d}.mp3"
        if not audio_file.exists():
            raise FileNotFoundError(
                f"Audio file not found: audio/scene_{scene.scene_id:03d}.mp3. "
                "Run pipeline_start_voiceover first."
            )
        duration = _ffprobe_duration(audio_file)
        entry = {
            "scene_id": scene.scene_id,
            "chapter": scene.chapter,
            "audio_file": str(audio_file),
            "start": round(offset, 3),
            "end": round(offset + duration, 3),
            "duration": round(duration, 3),
            "text": scene.text,
            "words": [],
        }
        timeline.append(entry)
        offset += duration

    path = workspace / "md" / "timeline.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(timeline, indent=2, ensure_ascii=False))
    return timeline


def load_timeline(workspace: Path) -> list[dict]:
    path = workspace / "md" / "timeline.json"
    if not path.exists():
        raise FileNotFoundError("timeline.json not found. Run pipeline_build_timeline first.")
    return json.loads(path.read_text())
