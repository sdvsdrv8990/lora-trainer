import json
from pathlib import Path

from src.entities.scenario import TTSBatch, TTSInstruction


def write_scenario(workspace: Path, tts_input: list[dict]) -> dict:
    """Validate and save Claude-structured tts_input. Build scenario.txt from scene texts."""
    if not tts_input:
        raise ValueError("tts_input must not be empty")

    scenes = [TTSInstruction.model_validate(item) for item in tts_input]
    batch = TTSBatch(scenes=scenes)

    md_dir = workspace / "md"
    md_dir.mkdir(parents=True, exist_ok=True)

    scenario_path = md_dir / "scenario.txt"
    tts_path = md_dir / "tts_input.json"

    scenario_path.write_text(
        "\n\n".join(scene.text for scene in batch.scenes) + "\n"
    )
    tts_path.write_text(
        json.dumps(
            [scene.model_dump(mode="json") for scene in batch.scenes],
            indent=2,
            ensure_ascii=False,
        )
    )

    return {
        "scenario_path": str(scenario_path),
        "tts_input_path": str(tts_path),
        "scene_count": len(batch.scenes),
    }


def load_tts_batch(workspace: Path) -> TTSBatch:
    path = workspace / "md" / "tts_input.json"
    if not path.exists():
        raise FileNotFoundError("md/tts_input.json not found. Run pipeline_submit_scenario first.")
    raw = json.loads(path.read_text())
    if isinstance(raw, dict) and "scenes" in raw:
        return TTSBatch.model_validate(raw)
    if isinstance(raw, list):
        return TTSBatch(scenes=[TTSInstruction.model_validate(item) for item in raw])
    raise ValueError("md/tts_input.json must contain a list of scenes or an object with scenes")
