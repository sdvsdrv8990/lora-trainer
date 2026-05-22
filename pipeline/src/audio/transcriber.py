import json
from pathlib import Path


def _load_model(model_name: str):
    from faster_whisper import WhisperModel
    return WhisperModel(model_name, device="cpu", compute_type="int8")


def transcribe_scenes(workspace: Path, model_name: str = "base", language: str = "ru") -> dict:
    """Run faster-whisper on each scene audio file and enrich timeline.json with word timings.

    Word timestamps are absolute (offset from video start), matching timeline entry start/end.
    Returns scene_count, total_words, and the timeline_path written.
    """
    timeline_path = workspace / "md" / "timeline.json"
    if not timeline_path.exists():
        raise FileNotFoundError("timeline.json not found. Run pipeline_build_timeline first.")

    timeline = json.loads(timeline_path.read_text())
    model = _load_model(model_name)

    total_words = 0
    for entry in timeline:
        audio_file = Path(entry["audio_file"])
        if not audio_file.exists():
            raise FileNotFoundError(
                f"Audio file not found: {audio_file.name}. Run pipeline_start_voiceover first."
            )

        scene_offset = entry["start"]
        segments, _ = model.transcribe(
            str(audio_file),
            language=language or None,
            word_timestamps=True,
        )

        words = []
        for segment in segments:
            if segment.words:
                for w in segment.words:
                    words.append({
                        "word": w.word.strip(),
                        "start": round(scene_offset + w.start, 3),
                        "end": round(scene_offset + w.end, 3),
                    })

        entry["words"] = words
        total_words += len(words)

    timeline_path.write_text(json.dumps(timeline, indent=2, ensure_ascii=False))
    return {
        "scene_count": len(timeline),
        "total_words": total_words,
        "timeline_path": str(timeline_path),
    }
