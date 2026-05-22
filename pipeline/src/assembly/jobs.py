import threading
from pathlib import Path

from src.assembly import ffmpeg as assembler


def start_assemble(workspace: Path, wait: bool = False) -> dict:
    if wait:
        return assembler.assemble_scenes(workspace)
    t = threading.Thread(target=assembler.assemble_scenes, args=(workspace,), daemon=True)
    t.start()
    return assembler.read_render_status(workspace)


def start_concat(workspace: Path, wait: bool = False) -> dict:
    if wait:
        return assembler.concat_scenes(workspace)
    t = threading.Thread(target=assembler.concat_scenes, args=(workspace,), daemon=True)
    t.start()
    return assembler.read_render_status(workspace)
