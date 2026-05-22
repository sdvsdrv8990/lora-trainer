import json
import shutil
import subprocess
from pathlib import Path

_RHUBARB_CANDIDATES = [
    Path("/usr/local/bin/rhubarb"),
    Path("/usr/bin/rhubarb"),
    Path.home() / ".local" / "bin" / "rhubarb",
]

MOUTH_MAP = {
    "A": "open_wide",
    "B": "closed",
    "C": "open",
    "D": "open",
    "E": "open_wide",
    "F": "closed",
    "G": "open",
    "H": "open",
    "X": "neutral",
}


def _find_rhubarb() -> Path:
    for p in _RHUBARB_CANDIDATES:
        if p.exists():
            return p
    found = shutil.which("rhubarb")
    if found:
        return Path(found)
    raise FileNotFoundError(
        "rhubarb binary not found. Install from "
        "https://github.com/DanielSWolf/rhubarb-lip-sync/releases"
    )


def generate_lipsync(audio_path: Path, output_path: Path) -> list[dict]:
    """
    Run rhubarb on audio_path, write mouth-cue JSON to output_path,
    and return the list of cue dicts with an added 'mouth_shape' key.
    """
    rhubarb = _find_rhubarb()
    proc = subprocess.run(
        [str(rhubarb), "-f", "json", str(audio_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"rhubarb failed: {proc.stderr}")

    raw = json.loads(proc.stdout)
    cues = raw.get("mouthCues", [])

    enriched = [
        {
            "start": c["start"],
            "end": c["end"],
            "value": c["value"],
            "mouth_shape": MOUTH_MAP.get(c["value"], "neutral"),
        }
        for c in cues
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(enriched, indent=2, ensure_ascii=False))

    return enriched
