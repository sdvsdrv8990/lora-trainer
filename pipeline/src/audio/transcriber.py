import json
from pathlib import Path


def _load_model(model_name: str):
    import stable_whisper
    return stable_whisper.load_faster_whisper(model_name, device="cpu", compute_type="int8")


def transcribe_scenes(
    workspace: Path,
    model_name: str = "base",
    language: str = "ru",
    vad: bool = False,
    suppress_silence: bool = True,
) -> dict:
    """Run stable-whisper (faster-whisper backend) on each scene audio file.

    Enriches timeline.json with:
      - words[]: [{word, start, end, confidence}]  — absolute timestamps
      - segments[]: [{start, end, text, words[]}]  — natural linguistic segments

    Also saves a reprocessable stable-ts JSON per scene:
      md/stable_result_scene_NNN.json

    These files are consumed by pipeline_export_subtitles and pipeline_align_scene.
    """
    timeline_path = workspace / "md" / "timeline.json"
    if not timeline_path.exists():
        raise FileNotFoundError("timeline.json not found. Run pipeline_build_timeline first.")

    timeline = json.loads(timeline_path.read_text())
    model = _load_model(model_name)

    subtitles_dir = workspace / "md" / "subtitles"
    subtitles_dir.mkdir(parents=True, exist_ok=True)

    total_words = 0
    for entry in timeline:
        audio_file = Path(entry["audio_file"])
        if not audio_file.exists():
            raise FileNotFoundError(
                f"Audio file not found: {audio_file.name}. Run pipeline_start_voiceover first."
            )

        scene_id = entry["scene_id"]
        scene_offset = float(entry["start"])

        result = model.transcribe(
            str(audio_file),
            language=language or None,
            word_timestamps=True,
            suppress_silence=suppress_silence,
            suppress_word_ts=suppress_silence,
            vad=vad,
            regroup=True,
            verbose=None,
        )

        # Save stable-ts JSON for subtitle export / re-alignment
        stable_json_path = workspace / "md" / f"stable_result_scene_{scene_id:03d}.json"
        result.save_as_json(str(stable_json_path))

        # Flat word list with absolute timestamps and confidence
        words = []
        for w in result.all_words():
            words.append({
                "word": w.word.strip(),
                "start": round(scene_offset + w.start, 3),
                "end": round(scene_offset + w.end, 3),
                "confidence": round(float(w.probability), 3),
            })

        # Segment list (natural linguistic groups) with absolute timestamps
        segments = []
        for seg in result.segments:
            seg_words = []
            if seg.words:
                for w in seg.words:
                    seg_words.append({
                        "word": w.word.strip(),
                        "start": round(scene_offset + w.start, 3),
                        "end": round(scene_offset + w.end, 3),
                    })
            segments.append({
                "start": round(scene_offset + seg.start, 3),
                "end": round(scene_offset + seg.end, 3),
                "text": seg.text.strip(),
                "words": seg_words,
            })

        entry["words"] = words
        entry["segments"] = segments
        total_words += len(words)

    timeline_path.write_text(json.dumps(timeline, indent=2, ensure_ascii=False))
    return {
        "scene_count": len(timeline),
        "total_words": total_words,
        "timeline_path": str(timeline_path),
        "stable_results_dir": str(workspace / "md"),
    }
