from abc import ABC, abstractmethod
from pathlib import Path

from src.entities.scenario import TTSInstruction


class TTSEngine(ABC):
    @abstractmethod
    def generate(self, scene: TTSInstruction, output_dir: Path) -> Path:
        """Generate audio for one scene and return the output file path."""


def get_tts_engine(config: dict) -> TTSEngine:
    tts_config = config.get("tts", {})
    engine = tts_config.get("engine", "espeak")
    if engine == "espeak":
        from src.tts.adapters.espeak import EspeakAdapter

        return EspeakAdapter(
            voice=tts_config.get("voice", "ru"),
            speed_wpm=int(tts_config.get("speed_wpm", 150)),
        )
    if engine == "tone":
        from src.tts.adapters.espeak import ToneAdapter

        return ToneAdapter()
    raise ValueError(f"Unknown TTS engine: {engine}")

