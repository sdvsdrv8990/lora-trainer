"""Competitor Intelligence System — stores and retrieves competitor channel/video data."""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

_SERVER_ROOT = Path(__file__).parent.parent.parent
_CI_ROOT = _SERVER_ROOT / "competitor_intelligence"
_GLOBAL_INDEX_PATH = _CI_ROOT / "_global_index.json"

_GLOBAL_INDEX_DEFAULT: dict = {
    "last_updated": "",
    "total_channels": 0,
    "total_videos": 0,
    "sheets": {
        "hooks": {
            "columns": ["hook_type", "channel_id", "video_id", "duration_sec",
                        "engagement_rate", "click_quality_score", "notes"],
            "rows": [],
        },
        "thumbnails": {
            "columns": ["thumbnail_type", "channel_id", "video_id",
                        "estimated_ctr", "click_quality_score", "emotion"],
            "rows": [],
        },
        "pacing": {
            "columns": ["rhythm_type", "avg_cut_interval", "pattern_interrupts",
                        "channel_id", "video_id", "engagement_rate"],
            "rows": [],
        },
        "patterns": {
            "columns": ["pattern_type", "technique", "channel_id",
                        "video_id", "effect", "confidence"],
            "rows": [],
        },
        "platform_models": {
            "columns": ["platform", "format", "best_hook_types",
                        "optimal_duration", "rhythm_type", "reward_type"],
            "rows": [],
        },
    },
}


def _load_engagement_formulas() -> dict:
    try:
        import yaml
        cfg_path = _SERVER_ROOT / "config" / "engagement_formulas.yaml"
        return yaml.safe_load(cfg_path.read_text())
    except Exception:
        return {}


def _apply_formulas(raw_metrics: dict) -> dict:
    """Apply engagement formulas to raw_metrics. Pure math — no interpretation."""
    formulas = _load_engagement_formulas()
    views = float(raw_metrics.get("views", 0) or 0)
    likes = float(raw_metrics.get("likes", 0) or 0)
    comments = float(raw_metrics.get("comments", 0) or 0)
    retention_rate = float(raw_metrics.get("retention_rate", 0) or 0)
    key_points_count = float(raw_metrics.get("key_points_count", 0) or 0)
    duration_sec = float(raw_metrics.get("duration_sec", 0) or 0)
    duration_minutes = duration_sec / 60.0 if duration_sec > 0 else 1.0

    def safe_div(a, b):
        return round(a / b, 4) if b and b != 0 else 0.0

    computed = {
        "engagement_rate": safe_div(likes + comments, views),
        "estimated_reach": round(views * 1.3),
        "click_quality_score": round(retention_rate * safe_div(likes + comments, views), 4),
        "discussion_rate": safe_div(comments, views),
        "estimated_ctr": round(safe_div(likes, views) * 0.15, 4),
        "attention_compression": safe_div(key_points_count, duration_minutes),
    }
    return computed


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_global_index() -> dict:
    if not _GLOBAL_INDEX_PATH.exists():
        data = dict(_GLOBAL_INDEX_DEFAULT)
        data["last_updated"] = datetime.now().isoformat()
        _write_json(_GLOBAL_INDEX_PATH, data)
        return data
    return _read_json(_GLOBAL_INDEX_PATH)


def _save_global_index(data: dict) -> None:
    data["last_updated"] = datetime.now().isoformat()
    _write_json(_GLOBAL_INDEX_PATH, data)


def _channel_dir(channel_id: str) -> Path:
    return _CI_ROOT / "channels" / channel_id


def _video_dir(channel_id: str, video_id: str) -> Path:
    return _channel_dir(channel_id) / "videos" / video_id


# ── Channel management ─────────────────────────────────────────────────────────

def add_competitor_channel(channel_id: str, channel_data: dict) -> dict:
    channel_data.setdefault("channel_id", channel_id)
    channel_data.setdefault("last_updated", datetime.now().isoformat())
    ch_dir = _channel_dir(channel_id)
    ch_dir.mkdir(parents=True, exist_ok=True)
    _write_json(ch_dir / "channel.json", channel_data)

    idx = _load_global_index()
    idx["total_channels"] = len(list((_CI_ROOT / "channels").iterdir())) if (_CI_ROOT / "channels").exists() else 1
    _save_global_index(idx)
    return {"channel_id": channel_id, "created": True}


def update_competitor_channel(channel_id: str, field: str, value) -> dict:
    path = _channel_dir(channel_id) / "channel.json"
    if not path.exists():
        raise FileNotFoundError(f"Channel '{channel_id}' not found")
    data = _read_json(path)
    # Support dot notation
    parts = field.split(".")
    d = data
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = value
    data["last_updated"] = datetime.now().isoformat()
    _write_json(path, data)
    return {"channel_id": channel_id, "field": field, "updated": True}


def get_competitor_channel(channel_id: str) -> dict:
    path = _channel_dir(channel_id) / "channel.json"
    if not path.exists():
        raise FileNotFoundError(f"Channel '{channel_id}' not found")
    return _read_json(path)


def list_competitor_channels() -> dict:
    ci_channels = _CI_ROOT / "channels"
    if not ci_channels.exists():
        return {"channels": [], "total": 0}
    channels = []
    for ch_dir in sorted(ci_channels.iterdir()):
        if ch_dir.is_dir():
            cfg_path = ch_dir / "channel.json"
            if cfg_path.exists():
                try:
                    data = _read_json(cfg_path)
                    videos_dir = ch_dir / "videos"
                    video_count = len(list(videos_dir.iterdir())) if videos_dir.exists() else 0
                    channels.append({
                        "channel_id": ch_dir.name,
                        "channel_name": data.get("channel_name", ch_dir.name),
                        "niche": data.get("niche", ""),
                        "video_count": video_count,
                    })
                except Exception:
                    pass
    return {"channels": channels, "total": len(channels)}


# ── Video management ───────────────────────────────────────────────────────────

def add_competitor_video(channel_id: str, video_id: str, video_data: dict) -> dict:
    video_data.setdefault("video_id", video_id)
    video_data.setdefault("channel_id", channel_id)
    video_data.setdefault("last_updated", datetime.now().isoformat())
    video_data.setdefault("analyzed_by_claude", False)

    # Compute metrics from raw_metrics
    raw = video_data.get("raw_metrics", {})
    if raw:
        video_data["computed_metrics"] = _apply_formulas(raw)

    v_dir = _video_dir(channel_id, video_id)
    v_dir.mkdir(parents=True, exist_ok=True)
    _write_json(v_dir / "video.json", video_data)

    idx = _load_global_index()
    total = 0
    ci_channels = _CI_ROOT / "channels"
    if ci_channels.exists():
        for ch in ci_channels.iterdir():
            vd = ch / "videos"
            if vd.exists():
                total += len(list(vd.iterdir()))
    idx["total_videos"] = total
    _save_global_index(idx)
    return {"channel_id": channel_id, "video_id": video_id, "created": True,
            "computed_metrics": video_data.get("computed_metrics", {})}


def update_competitor_video(channel_id: str, video_id: str, field: str, value) -> dict:
    path = _video_dir(channel_id, video_id) / "video.json"
    if not path.exists():
        raise FileNotFoundError(f"Video '{video_id}' for channel '{channel_id}' not found")
    data = _read_json(path)
    parts = field.split(".")
    d = data
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = value
    data["last_updated"] = datetime.now().isoformat()
    _write_json(path, data)
    return {"channel_id": channel_id, "video_id": video_id, "field": field, "updated": True}


def get_competitor_video(channel_id: str, video_id: str) -> dict:
    path = _video_dir(channel_id, video_id) / "video.json"
    if not path.exists():
        raise FileNotFoundError(f"Video '{video_id}' not found in channel '{channel_id}'")
    return _read_json(path)


def list_competitor_videos(channel_id: str) -> dict:
    vd = _channel_dir(channel_id) / "videos"
    if not vd.exists():
        return {"channel_id": channel_id, "videos": [], "total": 0}
    videos = []
    for v_dir in sorted(vd.iterdir()):
        if v_dir.is_dir():
            vp = v_dir / "video.json"
            if vp.exists():
                try:
                    d = _read_json(vp)
                    videos.append({
                        "video_id": v_dir.name,
                        "title": d.get("title", ""),
                        "platform": d.get("platform", ""),
                        "analyzed_by_claude": d.get("analyzed_by_claude", False),
                        "engagement_rate": d.get("computed_metrics", {}).get("engagement_rate", 0),
                    })
                except Exception:
                    pass
    return {"channel_id": channel_id, "videos": videos, "total": len(videos)}


# ── Transcript management ──────────────────────────────────────────────────────

def import_transcript(channel_id: str, video_id: str, transcript_data: dict) -> dict:
    transcript_data.setdefault("video_id", video_id)
    transcript_data.setdefault("imported_at", datetime.now().isoformat())
    v_dir = _video_dir(channel_id, video_id)
    v_dir.mkdir(parents=True, exist_ok=True)
    _write_json(v_dir / "transcript.json", transcript_data)
    segments = transcript_data.get("segments", [])
    duration = segments[-1]["end"] if segments else 0
    return {
        "channel_id": channel_id,
        "video_id": video_id,
        "segment_count": len(segments),
        "duration": duration,
    }


def get_transcript(channel_id: str, video_id: str) -> dict:
    v_dir = _video_dir(channel_id, video_id)
    path = v_dir / "transcript.json"
    if not path.exists():
        raise FileNotFoundError(f"No transcript found for {channel_id}/{video_id}. Import one first.")
    return _read_json(path)


# ── Global index queries ───────────────────────────────────────────────────────

def get_competitor_index(sheet: str = "") -> dict:
    data = _load_global_index()
    if sheet:
        if sheet not in data.get("sheets", {}):
            raise KeyError(f"Sheet '{sheet}' not found in competitor index")
        channel_count = data.get("total_channels", 0)
        video_count = data.get("total_videos", 0)
        return {
            "channel_count": channel_count,
            "video_count": video_count,
            sheet: data["sheets"][sheet],
        }
    return data


def query_competitor_data(
    sheet: str,
    filter_field: str = "",
    filter_value: str = "",
    min_value: str = "",
    max_value: str = "",
) -> dict:
    data = _load_global_index()
    if sheet not in data.get("sheets", {}):
        raise KeyError(f"Sheet '{sheet}' not found")
    rows = data["sheets"][sheet]["rows"]
    if filter_field and filter_value:
        rows = [r for r in rows if str(r.get(filter_field, "")) == filter_value]
    if min_value and filter_field:
        try:
            mv = float(min_value)
            rows = [r for r in rows if float(r.get(filter_field, 0)) >= mv]
        except ValueError:
            pass
    if max_value and filter_field:
        try:
            mv = float(max_value)
            rows = [r for r in rows if float(r.get(filter_field, 0)) <= mv]
        except ValueError:
            pass
    return {"sheet": sheet, "rows": rows, "total": len(rows)}


def add_competitor_index_row(sheet: str, row_data: dict) -> dict:
    idx = _load_global_index()
    if sheet not in idx.get("sheets", {}):
        raise KeyError(f"Sheet '{sheet}' not found")
    idx["sheets"][sheet].setdefault("rows", []).append(row_data)
    _save_global_index(idx)
    return {"sheet": sheet, "row_count": len(idx["sheets"][sheet]["rows"])}
