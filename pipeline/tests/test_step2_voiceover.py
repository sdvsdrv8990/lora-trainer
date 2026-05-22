import json
from pathlib import Path

from src.scenario import builder
from src.tts import jobs


_SCENE_1 = {"scene_id": 1, "chapter": "Ch 1", "text": "Scene one.", "tts": {"emotion": "neutral"}, "metadata": {}}
_SCENE_2 = {"scene_id": 2, "chapter": "Ch 1", "text": "Scene two.", "tts": {"emotion": "neutral"}, "metadata": {}}


def test_submit_scenario_writes_tts_input(tmp_path: Path) -> None:
    """SCN-P-010: Structured tts_input is validated and written as tts_input.json."""
    result = builder.write_scenario(tmp_path, [_SCENE_1, _SCENE_2])

    assert result["scene_count"] == 2
    assert Path(result["scenario_path"]).exists()
    tts_input = json.loads(Path(result["tts_input_path"]).read_text())
    assert tts_input[0]["scene_id"] == 1
    assert tts_input[0]["text"] == "Scene one."
    assert tts_input[0]["tts"]["emotion"] == "neutral"


def test_scenario_txt_joins_scene_texts(tmp_path: Path) -> None:
    """SCN-P-012: scenario.txt is built from scene texts joined by double newline."""
    builder.write_scenario(tmp_path, [_SCENE_1, _SCENE_2])
    scenario_txt = (tmp_path / "md" / "scenario.txt").read_text()
    assert "Scene one." in scenario_txt
    assert "Scene two." in scenario_txt
    assert "\n\n" in scenario_txt


def test_voiceover_job_generates_audio_and_status(tmp_path: Path) -> None:
    """SCN-P-011: Voiceover job writes audio files and completes status."""
    scenes = [{"scene_id": 1, "chapter": "", "text": "Hello this is a test", "tts": {"emotion": "neutral"}, "metadata": {}}]
    builder.write_scenario(tmp_path, scenes)
    jobs.mark_scenario_received(tmp_path, 1, str(tmp_path / "md" / "tts_input.json"))

    status = jobs.start(
        tmp_path,
        {"tts": {"engine": "espeak", "voice": "ru", "speed_wpm": 150}},
        wait=True,
    )

    assert status["status"] == "complete"
    assert status["completed_scenes"] == 1
    assert Path(status["audio_files"][0]).exists()
    assert Path(status["audio_files"][0]).suffix == ".mp3"
