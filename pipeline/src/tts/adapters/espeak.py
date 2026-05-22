import shutil
import subprocess
from pathlib import Path

from src.entities.scenario import TTSInstruction
from src.tts.engine import TTSEngine


class ToneAdapter(TTSEngine):
    """Last-resort audio generator that creates a short MP3 tone via FFmpeg."""

    def generate(self, scene: TTSInstruction, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"scene_{scene.scene_id:03d}.mp3"
        duration = max(1.0, min(12.0, len(scene.text) / 18.0))
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=440:duration={duration}",
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "6",
                str(output_path),
            ],
            check=True,
        )
        return output_path


class EspeakAdapter(TTSEngine):
    """Simple local TTS adapter using espeak-ng and FFmpeg.

    This is intentionally basic: it gives the workflow real audio files without
    coupling the pipeline to a heavy model while Kokoro quality work is pending.
    """

    def __init__(self, voice: str = "ru", speed_wpm: int = 150) -> None:
        self.voice = voice
        self.speed_wpm = speed_wpm

    def generate(self, scene: TTSInstruction, output_dir: Path) -> Path:
        if shutil.which("espeak-ng") is None:
            return ToneAdapter().generate(scene, output_dir)
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("ffmpeg is required to convert espeak output to MP3")

        output_dir.mkdir(parents=True, exist_ok=True)
        wav_path = output_dir / f"scene_{scene.scene_id:03d}.wav"
        mp3_path = output_dir / f"scene_{scene.scene_id:03d}.mp3"

        subprocess.run(
            [
                "espeak-ng",
                "-v",
                self.voice,
                "-s",
                str(self.speed_wpm),
                "-w",
                str(wav_path),
                scene.text,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(wav_path),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "5",
                str(mp3_path),
            ],
            check=True,
        )
        wav_path.unlink(missing_ok=True)
        return mp3_path

