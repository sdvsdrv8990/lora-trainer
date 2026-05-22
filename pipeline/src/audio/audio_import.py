"""Free audio search and import — freesound, pixabay, jamendo."""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.parse

_SERVER_ROOT = Path(__file__).parent.parent.parent
_AUDIO_CFG_PATH = _SERVER_ROOT / "config" / "audio_sources.yaml"
_TEMP_STORE: dict[str, dict] = {}  # import_id → result metadata


def _load_audio_config() -> dict:
    try:
        import yaml
        return yaml.safe_load(_AUDIO_CFG_PATH.read_text())
    except Exception:
        return {}


def _freesound_search(api_key: str, category: str, mood: str, duration_max: int) -> list[dict]:
    query_parts = []
    if mood:
        query_parts.append(mood)
    if category == "music":
        query_parts.append("music loop")
    elif category == "effects":
        query_parts.append("sound effect")
    query = " ".join(query_parts) or "ambient"

    params = {
        "query": query,
        "token": api_key,
        "fields": "id,name,duration,license,previews,tags",
        "page_size": "10",
        "filter": "duration:[1 TO 300]",
    }
    if duration_max > 0:
        params["filter"] = f"duration:[1 TO {duration_max}]"

    url = f"https://freesound.org/apiv2/search/text/?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "vidpipe/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())

    results = []
    for r in data.get("results", []):
        import_id = str(uuid.uuid4())[:8]
        entry = {
            "title": r.get("name", ""),
            "duration": int(r.get("duration", 0)),
            "license": r.get("license", ""),
            "bpm": 0,
            "preview_url": r.get("previews", {}).get("preview-lq-mp3", ""),
            "import_id": import_id,
            "_source": "freesound",
            "_source_id": str(r.get("id", "")),
            "_download_url": r.get("previews", {}).get("preview-hq-mp3", ""),
        }
        _TEMP_STORE[import_id] = entry
        results.append({k: v for k, v in entry.items() if not k.startswith("_")})
    return results


def search_free_audio(
    category: str,
    mood: str = "",
    duration_max: int = 0,
    source: str = "freesound",
) -> dict:
    """Search free audio sources. Returns results with import_ids for save_free_audio."""
    cfg = _load_audio_config()

    if source == "freesound":
        api_key = cfg.get("freesound", {}).get("api_key", "")
        if not api_key:
            return {
                "ok": False,
                "error": (
                    "Freesound API key not configured. "
                    "Add it to config/audio_sources.yaml under freesound.api_key. "
                    "Get a free key at https://freesound.org/apiv2/apply/"
                ),
            }
        try:
            results = _freesound_search(api_key, category, mood, duration_max)
            return {"ok": True, "results": results, "source": source, "total": len(results)}
        except Exception as e:
            return {"ok": False, "error": f"Freesound search failed: {e}"}

    elif source == "pixabay":
        api_key = cfg.get("pixabay", {}).get("api_key", "")
        if not api_key:
            return {
                "ok": False,
                "error": (
                    "Pixabay API key not configured. "
                    "Add it to config/audio_sources.yaml under pixabay.api_key."
                ),
            }
        return {"ok": False, "error": "Pixabay audio search not yet implemented."}

    elif source == "jamendo":
        api_key = cfg.get("jamendo", {}).get("api_key", "")
        if not api_key:
            return {
                "ok": False,
                "error": (
                    "Jamendo API key not configured. "
                    "Add it to config/audio_sources.yaml under jamendo.api_key."
                ),
            }
        return {"ok": False, "error": "Jamendo search not yet implemented."}

    return {"ok": False, "error": f"Unknown source '{source}'. Supported: freesound, pixabay, jamendo"}


def save_free_audio(
    import_id: str,
    group: str,
    mood: str,
    scope: str = "global",
    channel: str = "",
    scenario: str = "",
    workspace: Optional[Path] = None,
) -> dict:
    """Download and register a free audio track from a previous search result."""
    if import_id not in _TEMP_STORE:
        return {
            "ok": False,
            "error": f"import_id '{import_id}' not found. Run pipeline_search_free_audio first.",
        }

    entry = _TEMP_STORE[import_id]
    download_url = entry.get("_download_url", entry.get("preview_url", ""))
    if not download_url:
        return {"ok": False, "error": "No download URL available for this track."}

    title_safe = entry["title"].lower().replace(" ", "_")[:40]
    ext = ".mp3"

    if scope == "global":
        from src.images.assets import _GLOBAL_ASSETS_DIR, _load_index, _save_index, _scope_prefix
        assets_root = _GLOBAL_ASSETS_DIR
        prefix = "G"
    else:
        if not workspace:
            return {"ok": False, "error": "workspace required for project scope"}
        assets_root = workspace / "assets"
        prefix = "P"

    # Determine audio subdirectory based on group type
    subdir = "music" if "music" in group.lower() else "effects"
    save_dir = assets_root / "sounds" / subdir / group
    save_dir.mkdir(parents=True, exist_ok=True)

    # Find next track number
    existing = list(save_dir.glob("*.mp3")) + list(save_dir.glob("*.wav"))
    next_num = len(existing) + 1
    file_name = f"track_{next_num:02d}{ext}"
    dest_path = save_dir / file_name

    # Download file
    try:
        req = urllib.request.Request(download_url, headers={"User-Agent": "vidpipe/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest_path.write_bytes(resp.read())
    except Exception as e:
        return {"ok": False, "error": f"Download failed: {e}"}

    # Register in asset index
    from src.images.assets import _load_index, _save_index, _derive_group_id, _next_role_seq

    index = _load_index(assets_root, scope if scope == "global" else "project")
    category = f"sounds/{subdir}/{group}"
    group_id, tcode = _derive_group_id(assets_root, scope if scope == "global" else "project", category)

    seq = _next_role_seq(index, group_id, "CTX")
    asset_id = f"{prefix}-{tcode}-{group_id.split('-')[2]}-{seq:03d}"
    rel = f"sounds/{subdir}/{group}/{file_name}"
    index["id_map"][asset_id] = rel
    index.setdefault("meta_map", {})[asset_id] = {
        "role": "CTX",
        "group_id": group_id,
        "name": title_safe,
        "mood": mood,
        "license": entry.get("license", ""),
        "duration_sec": entry.get("duration", 0),
        "global_uses": 0,
        "project_uses": 0,
        "last_used": None,
        "created_at": datetime.now().isoformat(),
    }
    _save_index(assets_root, index)

    # Clean up temp store
    del _TEMP_STORE[import_id]

    path_str = f"{'global_assets' if scope == 'global' else 'assets'}/{rel}"
    return {
        "ok": True,
        "asset_id": asset_id,
        "path": path_str,
        "group": group,
        "mood": mood,
    }
