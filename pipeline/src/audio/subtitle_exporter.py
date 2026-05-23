import json
from pathlib import Path

SUPPORTED_FORMATS = ("srt", "vtt", "ass", "tsv", "txt")


def export_subtitles(
    workspace: Path,
    scene_ids: list[int] | None,
    fmt: str = "srt",
    segment_level: bool = True,
    word_level: bool = False,
) -> list[dict]:
    """Export subtitles for one or all scenes using saved stable-ts JSON results.

    Returns list of {scene_id, path, format} for each exported file.
    Files saved to md/subtitles/scene_NNN.<fmt>

    scene_ids=None exports all scenes that have a stable_result file.
    segment_level=True puts one subtitle per linguistic segment.
    word_level=True adds word-by-word karaoke highlighting (ASS only).
    """
    import stable_whisper

    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format '{fmt}'. Choose from: {SUPPORTED_FORMATS}")

    subtitles_dir = workspace / "md" / "subtitles"
    subtitles_dir.mkdir(parents=True, exist_ok=True)

    # Discover available scenes
    available = sorted(
        (workspace / "md").glob("stable_result_scene_*.json"),
        key=lambda p: int(p.stem.split("_")[-1]),
    )
    if not available:
        raise FileNotFoundError(
            "No stable_result_scene_NNN.json files found. "
            "Run pipeline_transcribe_scenes first."
        )

    if scene_ids is not None:
        wanted = {f"stable_result_scene_{sid:03d}.json" for sid in scene_ids}
        available = [p for p in available if p.name in wanted]
        if not available:
            raise FileNotFoundError(f"No stable results found for scene_ids={scene_ids}")

    exported = []
    for result_path in available:
        scene_id = int(result_path.stem.split("_")[-1])
        result = stable_whisper.WhisperResult(str(result_path))

        out_path = subtitles_dir / f"scene_{scene_id:03d}.{fmt}"

        if fmt in ("srt", "vtt"):
            result.to_srt_vtt(
                str(out_path),
                segment_level=segment_level,
                word_level=word_level,
            )
        elif fmt == "ass":
            result.to_ass(
                str(out_path),
                segment_level=segment_level,
                word_level=word_level,
            )
        elif fmt == "tsv":
            result.to_tsv(str(out_path))
        elif fmt == "txt":
            result.to_txt(str(out_path))

        exported.append({
            "scene_id": scene_id,
            "path": str(out_path),
            "format": fmt,
        })

    return exported


def align_scene(
    workspace: Path,
    scene_id: int,
    corrected_text: str,
    model_name: str = "base",
    language: str = "ru",
) -> dict:
    """Re-align corrected text to scene audio without re-transcribing.

    Faster than a full transcribe. Updates the stable_result JSON in-place
    and re-writes the words[] for that scene in timeline.json.

    Returns: {scene_id, word_count, stable_result_path}
    """
    import stable_whisper

    timeline_path = workspace / "md" / "timeline.json"
    if not timeline_path.exists():
        raise FileNotFoundError("timeline.json not found.")

    # Find the scene entry
    timeline = json.loads(timeline_path.read_text())
    entry = next((e for e in timeline if e["scene_id"] == scene_id), None)
    if entry is None:
        raise ValueError(f"Scene {scene_id} not found in timeline.json")

    audio_file = Path(entry["audio_file"])
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    scene_offset = float(entry["start"])

    model = stable_whisper.load_faster_whisper(model_name, device="cpu", compute_type="int8")
    result = model.align(str(audio_file), corrected_text, language=language or None)

    stable_json_path = workspace / "md" / f"stable_result_scene_{scene_id:03d}.json"
    result.save_as_json(str(stable_json_path))

    words = []
    for w in result.all_words():
        words.append({
            "word": w.word.strip(),
            "start": round(scene_offset + w.start, 3),
            "end": round(scene_offset + w.end, 3),
            "confidence": round(float(w.probability), 3),
        })

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
    timeline_path.write_text(json.dumps(timeline, indent=2, ensure_ascii=False))

    return {
        "scene_id": scene_id,
        "word_count": len(words),
        "stable_result_path": str(stable_json_path),
    }
