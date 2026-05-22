import struct
import zlib
from pathlib import Path

from src.entities.prompts import FramePrompt
from src.images.engine import ImageEngine


def _minimal_png() -> bytes:
    """Build a valid 1×1 black RGB PNG in memory."""
    def chunk(name: bytes, data: bytes) -> bytes:
        payload = name + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat_data = zlib.compress(b"\x00\x00\x00\x00")  # filter=None + R=0 G=0 B=0
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr_data)
        + chunk(b"IDAT", idat_data)
        + chunk(b"IEND", b"")
    )


_PNG_BYTES = _minimal_png()


class StubAdapter(ImageEngine):
    """Placeholder adapter — writes a 1×1 black PNG so the pipeline runs end-to-end."""

    def generate(self, prompt: FramePrompt, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"frame_{prompt.frame_id:04d}.png"
        output_path.write_bytes(_PNG_BYTES)
        return output_path
