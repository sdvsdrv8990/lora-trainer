"""Registry management — global_registry.json and project_registry.json."""
import fcntl
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

_SERVER_ROOT = Path(__file__).parent.parent
_GLOBAL_REGISTRY_PATH = _SERVER_ROOT / "global_registry.json"

# Per-file threading locks prevent TOCTOU in concurrent MCP tool calls.
# fcntl provides additional cross-process safety on Linux.
_GLOBAL_LOCK = threading.Lock()
_PROJECT_LOCKS: dict[str, threading.Lock] = {}
_PROJECT_LOCKS_MU = threading.Lock()


def _get_project_lock(path: Path) -> threading.Lock:
    key = str(path)
    with _PROJECT_LOCKS_MU:
        if key not in _PROJECT_LOCKS:
            _PROJECT_LOCKS[key] = threading.Lock()
        return _PROJECT_LOCKS[key]


def _load_registry(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            return json.load(f)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _save_registry(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(data, f, indent=2, ensure_ascii=False)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


_GROUP_SHEET_COLUMNS = [
    "id", "role", "name", "path", "description",
    "semantic_tags", "emotion_tags", "visual_energy",
    "attention_weight", "compatible_groups",
    "global_uses", "project_uses", "projects_count",
    "last_used", "created_from",
]

_GLOBAL_DEFAULT: dict = {
    "version": "1.0",
    "schema_version": "dynamic",
    "sheets": {
        "assets": {
            "columns": ["id", "name", "type", "role", "path", "created_at",
                        "total_uses", "total_scenarios", "last_used"],
            "rows": [],
        },
        "experiments": {
            "columns": ["experiment_id", "scenario_a", "scenario_b",
                        "variable", "result", "winner", "insight"],
            "rows": [],
        },
        "performance": {
            "columns": ["video_id", "platform", "avg_watch_time",
                        "retention_73s", "ctr", "rewatch_rate"],
            "rows": [],
        },
    },
    "custom_fields": {},
}

_PROJECT_DEFAULT: dict = {
    "version": "1.0",
    "video_id": "",
    "scenario": "",
    "duration": 0,
    "platform": "",
    "sheets": {
        "assets": {
            "columns": ["id", "name", "type", "scope", "path", "uses_in_scenario"],
            "rows": [],
        },
        "scenes": {
            "columns": ["scene_id", "start", "end", "chapter",
                        "module_type", "emotion", "visual_pattern",
                        "audio_pattern", "reset_point", "notes"],
            "rows": [],
        },
        "hooks": {
            "columns": ["hook_id", "type", "duration", "trigger",
                        "reward_type", "audience_expectation", "effectiveness_score"],
            "rows": [],
        },
        "emotion_map": {
            "columns": ["time_start", "time_end", "emotion",
                        "module", "intensity", "visual_support", "audio_support"],
            "rows": [],
        },
        "attention_graph": {
            "columns": ["time", "module_type", "reset_point",
                        "fatigue_level", "trigger_type", "expected_retention"],
            "rows": [],
        },
        "performance": {
            "columns": ["metric", "value", "source", "recorded_at"],
            "rows": [],
        },
        "insights": {
            "columns": ["insight_id", "type", "description",
                        "evidence", "action", "created_at"],
            "rows": [],
        },
    },
    "structure": {
        "hook_type": "",
        "hook_duration": 0,
        "pattern": "",
        "modules": [],
        "reset_points": [],
        "reward_type": "",
        "audience_expectation_profile": "",
    },
    "custom_fields": {},
}


def _project_registry_path(workspace: Path) -> Path:
    return workspace / "project_registry.json"


def load_global() -> dict:
    if not _GLOBAL_REGISTRY_PATH.exists():
        _save_registry(_GLOBAL_REGISTRY_PATH, _GLOBAL_DEFAULT.copy())
        return _GLOBAL_DEFAULT.copy()
    return _load_registry(_GLOBAL_REGISTRY_PATH)


def _save_global(data: dict) -> None:
    _save_registry(_GLOBAL_REGISTRY_PATH, data)


def load_project(workspace: Path) -> dict:
    path = _project_registry_path(workspace)
    if not path.exists():
        data = _PROJECT_DEFAULT.copy()
        data["scenario"] = workspace.name
        _save_registry(path, data)
        return data
    return _load_registry(path)


def _save_project(workspace: Path, data: dict) -> None:
    _save_registry(_project_registry_path(workspace), data)


def get_registry(workspace: Optional[Path], scope: str, sheet: str = "") -> dict:
    if scope == "global":
        data = load_global()
    else:
        if not workspace:
            raise ValueError("workspace required for project scope")
        data = load_project(workspace)
    if sheet:
        if sheet not in data.get("sheets", {}):
            raise KeyError(f"Sheet '{sheet}' not found")
        return {sheet: data["sheets"][sheet]}
    return data


def add_registry_row(workspace: Optional[Path], scope: str, sheet: str, row_data: dict) -> dict:
    lock = _GLOBAL_LOCK if scope == "global" else _get_project_lock(_project_registry_path(workspace))  # type: ignore[arg-type]
    with lock:
        if scope == "global":
            data = load_global()
        else:
            if not workspace:
                raise ValueError("workspace required for project scope")
            data = load_project(workspace)

        if sheet not in data.get("sheets", {}):
            raise KeyError(f"Sheet '{sheet}' not found")

        rows = data["sheets"][sheet]["rows"]
        rows.append(row_data)

        if scope == "global":
            _save_global(data)
        else:
            _save_project(workspace, data)  # type: ignore[arg-type]
    return {"sheet": sheet, "row_index": len(rows) - 1, "row": row_data}


def update_registry_row(
    workspace: Optional[Path],
    scope: str,
    sheet: str,
    row_id: str,
    field: str,
    value,
) -> dict:
    lock = _GLOBAL_LOCK if scope == "global" else _get_project_lock(_project_registry_path(workspace))  # type: ignore[arg-type]
    with lock:
        if scope == "global":
            data = load_global()
        else:
            if not workspace:
                raise ValueError("workspace required for project scope")
            data = load_project(workspace)

        if sheet not in data.get("sheets", {}):
            raise KeyError(f"Sheet '{sheet}' not found")

        rows = data["sheets"][sheet]["rows"]
        id_field = data["sheets"][sheet]["columns"][0] if data["sheets"][sheet]["columns"] else "id"
        updated = False
        for row in rows:
            if str(row.get(id_field, "")) == str(row_id):
                row[field] = value
                updated = True
                break

        if not updated:
            raise KeyError(f"Row '{row_id}' not found in sheet '{sheet}'")

        if scope == "global":
            _save_global(data)
        else:
            _save_project(workspace, data)  # type: ignore[arg-type]
    return {"sheet": sheet, "row_id": row_id, "field": field, "value": value}


def delete_registry_row(workspace: Optional[Path], scope: str, sheet: str, row_id: str) -> dict:
    lock = _GLOBAL_LOCK if scope == "global" else _get_project_lock(_project_registry_path(workspace))  # type: ignore[arg-type]
    with lock:
        if scope == "global":
            data = load_global()
        else:
            if not workspace:
                raise ValueError("workspace required for project scope")
            data = load_project(workspace)

        if sheet not in data.get("sheets", {}):
            raise KeyError(f"Sheet '{sheet}' not found")

        rows = data["sheets"][sheet]["rows"]
        id_field = data["sheets"][sheet]["columns"][0] if data["sheets"][sheet]["columns"] else "id"
        before = len(rows)
        data["sheets"][sheet]["rows"] = [r for r in rows if str(r.get(id_field, "")) != str(row_id)]
        removed = before - len(data["sheets"][sheet]["rows"])

        if scope == "global":
            _save_global(data)
        else:
            _save_project(workspace, data)  # type: ignore[arg-type]
    return {"sheet": sheet, "row_id": row_id, "removed": removed}


def add_registry_column(
    workspace: Optional[Path],
    scope: str,
    sheet: str,
    column_name: str,
    default_value: str = "",
) -> dict:
    lock = _GLOBAL_LOCK if scope == "global" else _get_project_lock(_project_registry_path(workspace))  # type: ignore[arg-type]
    with lock:
        if scope == "global":
            data = load_global()
        else:
            if not workspace:
                raise ValueError("workspace required for project scope")
            data = load_project(workspace)

        if sheet not in data.get("sheets", {}):
            raise KeyError(f"Sheet '{sheet}' not found")

        cols = data["sheets"][sheet]["columns"]
        if column_name in cols:
            return {"sheet": sheet, "column": column_name, "added": False, "reason": "already exists"}
        cols.append(column_name)
        for row in data["sheets"][sheet]["rows"]:
            row.setdefault(column_name, default_value)

        if scope == "global":
            _save_global(data)
        else:
            _save_project(workspace, data)  # type: ignore[arg-type]
    return {"sheet": sheet, "column": column_name, "added": True}


def add_registry_sheet(
    workspace: Optional[Path],
    scope: str,
    sheet_name: str,
    columns: list[str],
) -> dict:
    lock = _GLOBAL_LOCK if scope == "global" else _get_project_lock(_project_registry_path(workspace))  # type: ignore[arg-type]
    with lock:
        if scope == "global":
            data = load_global()
        else:
            if not workspace:
                raise ValueError("workspace required for project scope")
            data = load_project(workspace)

        if sheet_name in data.get("sheets", {}):
            return {"sheet": sheet_name, "added": False, "reason": "already exists"}
        data.setdefault("sheets", {})[sheet_name] = {"columns": columns, "rows": []}

        if scope == "global":
            _save_global(data)
        else:
            _save_project(workspace, data)  # type: ignore[arg-type]
    return {"sheet": sheet_name, "added": True, "columns": columns}


def query_registry(
    workspace: Optional[Path],
    scope: str,
    sheet: str,
    filter_field: str = "",
    filter_value: str = "",
) -> dict:
    if scope == "global":
        data = load_global()
    else:
        if not workspace:
            raise ValueError("workspace required for project scope")
        data = load_project(workspace)

    if sheet not in data.get("sheets", {}):
        raise KeyError(f"Sheet '{sheet}' not found")

    rows = data["sheets"][sheet]["rows"]
    if filter_field and filter_value:
        rows = [r for r in rows if str(r.get(filter_field, "")) == filter_value]
    return {"sheet": sheet, "rows": rows, "total": len(rows)}


def get_global_stats() -> dict:
    data = load_global()
    stats: dict = {}
    for sheet_name, sheet in data.get("sheets", {}).items():
        stats[sheet_name] = {"row_count": len(sheet.get("rows", []))}
    return {"sheets": stats, "total_sheets": len(data.get("sheets", {}))}


def export_registry(workspace: Optional[Path], scope: str, sheet: str = "") -> dict:
    return get_registry(workspace, scope, sheet)


def set_video_structure(workspace: Path, structure: dict) -> dict:
    with _get_project_lock(_project_registry_path(workspace)):
        data = load_project(workspace)
        data["structure"] = structure
        _save_project(workspace, data)
    modules = len(structure.get("modules", []))
    reset_points = len(structure.get("reset_points", []))
    return {"saved": True, "modules": modules, "reset_points": reset_points}


def get_video_structure(workspace: Path) -> dict:
    data = load_project(workspace)
    return data.get("structure", {})


def add_emotion_map(workspace: Path, emotion_entries: list[dict]) -> dict:
    with _get_project_lock(_project_registry_path(workspace)):
        data = load_project(workspace)
        sheet = data["sheets"]["emotion_map"]
        for entry in emotion_entries:
            sheet["rows"].append(entry)
        _save_project(workspace, data)
    return {"added": len(emotion_entries), "total": len(sheet["rows"])}


def import_platform_stats(workspace: Path, stats: dict, platform: str) -> dict:
    with _get_project_lock(_project_registry_path(workspace)):
        data = load_project(workspace)
        sheet = data["sheets"]["performance"]
        now = datetime.now().isoformat()
        for metric, value in stats.items():
            sheet["rows"].append({
                "metric": metric,
                "value": str(value),
                "source": platform,
                "recorded_at": now,
            })
        _save_project(workspace, data)
    return {"platform": platform, "metrics_imported": len(stats)}


def create_experiment(
    experiment_id: str,
    scenario_a: str,
    scenario_b: str,
    variable: str,
    hypothesis: str,
) -> dict:
    with _GLOBAL_LOCK:
        data = load_global()
        row = {
            "experiment_id": experiment_id,
            "scenario_a": scenario_a,
            "scenario_b": scenario_b,
            "variable": variable,
            "hypothesis": hypothesis,
            "result": "",
            "winner": "",
            "insight": "",
        }
        data["sheets"]["experiments"]["rows"].append(row)
        _save_global(data)
    return {"experiment_id": experiment_id, "created": True}


def update_experiment(experiment_id: str, result: str, winner: str, insight: str) -> dict:
    with _GLOBAL_LOCK:
        data = load_global()
        rows = data["sheets"]["experiments"]["rows"]
        for row in rows:
            if row.get("experiment_id") == experiment_id:
                row["result"] = result
                row["winner"] = winner
                row["insight"] = insight
                _save_global(data)
                return {"experiment_id": experiment_id, "updated": True}
        raise KeyError(f"Experiment '{experiment_id}' not found")


def get_analytics(
    filter_hook_type: str = "",
    filter_platform: str = "",
    filter_reward_type: str = "",
) -> dict:
    data = load_global()
    perf_rows = data.get("sheets", {}).get("performance", {}).get("rows", [])
    if filter_platform:
        perf_rows = [r for r in perf_rows if r.get("platform") == filter_platform]
    exp_rows = data.get("sheets", {}).get("experiments", {}).get("rows", [])
    return {
        "performance": perf_rows,
        "experiments": exp_rows,
        "total_performance_records": len(perf_rows),
        "total_experiments": len(exp_rows),
    }


def get_insights(workspace: Optional[Path], min_evidence: int = 2) -> list[dict]:
    results = []
    if workspace:
        proj_data = load_project(workspace)
        proj_insights = proj_data.get("sheets", {}).get("insights", {}).get("rows", [])
        results.extend([r for r in proj_insights
                        if len(str(r.get("evidence", "")).split(",")) >= min_evidence])
    global_data = load_global()
    for row in global_data.get("sheets", {}).get("experiments", {}).get("rows", []):
        if row.get("insight") and row.get("winner"):
            results.append({
                "insight_id": row["experiment_id"],
                "type": "experiment",
                "description": row.get("insight", ""),
                "evidence": f"{row.get('scenario_a')},{row.get('scenario_b')}",
                "action": f"Use {row.get('winner')} pattern",
            })
    return results


def ensure_group_sheet(group_id: str, group_meta: dict) -> None:
    """Ensure a group sheet exists in global_registry.json. Creates it if absent."""
    with _GLOBAL_LOCK:
        data = load_global()
        if group_id not in data.get("sheets", {}):
            tcode = group_id.split("-")[1] if "-" in group_id else "OBJ"
            is_music = tcode in ("MUS", "SFX", "SND")
            if is_music:
                cols = ["id", "name", "path", "mood", "bpm",
                        "duration_sec", "license", "global_uses", "project_uses"]
            else:
                cols = _GROUP_SHEET_COLUMNS
            data.setdefault("sheets", {})[group_id] = {
                "name": group_meta.get("name", group_id),
                "description": group_meta.get("description", ""),
                "base_id": group_meta.get("base_id", None),
                "lora_id": group_meta.get("lora_id", None),
                "columns": cols,
                "rows": [],
            }
            _save_global(data)


def register_asset_in_group_sheet(group_id: str, asset_meta: dict) -> None:
    """Add or update an asset row in its group sheet."""
    with _GLOBAL_LOCK:
        data = load_global()
        if group_id not in data.get("sheets", {}):
            return
        sheet = data["sheets"][group_id]
        rows = sheet["rows"]
        asset_id = asset_meta.get("id", "")
        # Update if exists
        for row in rows:
            if row.get("id") == asset_id:
                row.update(asset_meta)
                _save_global(data)
                return
        rows.append(asset_meta)
        # Also update assets sheet
        assets_sheet = data["sheets"].get("assets", {})
        if assets_sheet:
            for row in assets_sheet.get("rows", []):
                if row.get("id") == asset_id:
                    row.update(asset_meta)
                    _save_global(data)
                    return
            assets_sheet.setdefault("rows", []).append(asset_meta)
        _save_global(data)


def remove_asset_from_group_sheet(group_id: str, asset_id: str) -> None:
    """Remove asset from its group sheet and assets sheet."""
    with _GLOBAL_LOCK:
        data = load_global()
        for sheet_name in [group_id, "assets"]:
            sheet = data.get("sheets", {}).get(sheet_name)
            if sheet:
                sheet["rows"] = [r for r in sheet["rows"] if r.get("id") != asset_id]
        _save_global(data)


def increment_asset_global_uses(asset_id: str, group_id: str = "") -> None:
    """Increment global_uses and update last_used in group sheet row."""
    from datetime import datetime
    with _GLOBAL_LOCK:
        data = load_global()
        now = datetime.now().isoformat()
        for sheet_name in ([group_id] if group_id else []) + ["assets"]:
            sheet = data.get("sheets", {}).get(sheet_name)
            if not sheet:
                continue
            for row in sheet.get("rows", []):
                if row.get("id") == asset_id:
                    row["global_uses"] = row.get("global_uses", 0) + 1
                    row["last_used"] = now
        _save_global(data)


def compare_videos(video_id_a: str, video_id_b: str) -> dict:
    global_data = load_global()
    perf_rows = global_data.get("sheets", {}).get("performance", {}).get("rows", [])
    a_rows = [r for r in perf_rows if r.get("video_id") == video_id_a]
    b_rows = [r for r in perf_rows if r.get("video_id") == video_id_b]
    return {
        "video_a": {"video_id": video_id_a, "performance": a_rows},
        "video_b": {"video_id": video_id_b, "performance": b_rows},
    }
