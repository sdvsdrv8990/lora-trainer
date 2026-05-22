import json
from pathlib import Path

from src.entities.layout import SceneLayout

_FILENAME = "scene_layout.json"


def _detect_schema(data: dict) -> str:
    """Return 'v2' if data contains events-based scenes, 'v1' otherwise."""
    if "_schema_version" in data:
        return data["_schema_version"]
    # v2: top-level "scenes" list where each scene has "events"
    scenes = data.get("scenes", [])
    if scenes and "events" in scenes[0]:
        return "v2"
    # v1: top-level "frames" list
    return "v1"


def save_layout(workspace: Path, data: dict) -> dict:
    schema = _detect_schema(data)
    data["_schema_version"] = schema

    path = workspace / "md" / _FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)

    if schema == "v2":
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        scene_count = len(data.get("scenes", []))
        return {
            "layout_path": str(path),
            "schema_version": "v2",
            "scene_count": scene_count,
            "total_frames": None,
            "frame_count": None,
            "canvas": data.get("scenes", [{}])[0].get("canvas", {}),
        }

    # v1 path — Pydantic validation
    layout = SceneLayout.model_validate(data)
    path.write_text(json.dumps(layout.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return {
        "layout_path": str(path),
        "schema_version": "v1",
        "total_frames": layout.total_frames,
        "frame_count": len(layout.frames),
        "canvas": layout.canvas.model_dump(),
    }


def load_layout(workspace: Path) -> SceneLayout:
    """Load v1 layout. Raises ValueError for v2 layouts (use load_layout_raw instead)."""
    path = workspace / "md" / _FILENAME
    if not path.exists():
        raise FileNotFoundError(f"{_FILENAME} not found. Run pipeline_submit_scene_layouts first.")
    raw = json.loads(path.read_text())
    if raw.get("_schema_version") == "v2":
        raise ValueError("This workspace uses v2 (events-based) layout. Use load_layout_raw().")
    return SceneLayout.model_validate(raw)


def load_layout_raw(workspace: Path) -> dict:
    path = workspace / "md" / _FILENAME
    if not path.exists():
        raise FileNotFoundError(f"{_FILENAME} not found.")
    return json.loads(path.read_text())


def get_schema_version(workspace: Path) -> str:
    path = workspace / "md" / _FILENAME
    if not path.exists():
        return "none"
    return json.loads(path.read_text()).get("_schema_version", "v1")


def get_layout_data(workspace: Path) -> dict:
    raw = load_layout_raw(workspace)
    if raw.get("_schema_version") != "v2":
        return SceneLayout.model_validate(raw).model_dump(mode="json")
    return raw


def update_frame(workspace: Path, frame_id: int, layers_data: list) -> dict:
    path = workspace / "md" / _FILENAME
    if not path.exists():
        raise FileNotFoundError(f"{_FILENAME} not found.")
    raw = json.loads(path.read_text())
    if raw.get("_schema_version") == "v2":
        raise ValueError("update_frame only works on v1 layouts. Use pipeline_update_scene_event for v2.")
    for frame in raw.get("frames", []):
        if frame["frame_id"] == frame_id:
            frame["layers"] = layers_data
            break
    else:
        raise ValueError(f"Frame {frame_id} not found in {_FILENAME}")
    layout = SceneLayout.model_validate(raw)
    path.write_text(json.dumps(layout.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return {"frame_id": frame_id, "layers_updated": len(layers_data)}


def update_scene_event(workspace: Path, scene_id: int, event_index: int, field: str, value: str) -> dict:
    """Mutate a single event field in a v2 layout without full resubmit."""
    path = workspace / "md" / _FILENAME
    if not path.exists():
        raise FileNotFoundError(f"{_FILENAME} not found.")
    raw = json.loads(path.read_text())
    if raw.get("_schema_version") != "v2":
        raise ValueError("update_scene_event only works on v2 layouts.")

    scenes = raw.get("scenes", [])
    scene = next((s for s in scenes if s["scene_id"] == scene_id), None)
    if scene is None:
        raise ValueError(f"Scene {scene_id} not found.")

    events = scene.get("events", [])
    if event_index < 0 or event_index >= len(events):
        raise IndexError(f"Event index {event_index} out of range (0–{len(events)-1}).")

    event = events[event_index]

    # Support dotted paths: "state.emotion", "position.x"
    parts = field.split(".", 1)
    if len(parts) == 2:
        parent, child = parts
        if parent not in event:
            event[parent] = {}
        old_value = event[parent].get(child)
        event[parent][child] = value
    else:
        old_value = event.get(field)
        event[field] = value

    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
    return {
        "scene_id": scene_id,
        "event_index": event_index,
        "field": field,
        "old_value": old_value,
        "new_value": value,
    }


def move_event(workspace: Path, scene_id: int, event_index: int, new_time: float) -> dict:
    path = workspace / "md" / _FILENAME
    if not path.exists():
        raise FileNotFoundError(f"{_FILENAME} not found.")
    raw = json.loads(path.read_text())
    if raw.get("_schema_version") != "v2":
        raise ValueError("move_event only works on v2 layouts.")

    scenes = raw.get("scenes", [])
    scene = next((s for s in scenes if s["scene_id"] == scene_id), None)
    if scene is None:
        raise ValueError(f"Scene {scene_id} not found.")

    events = scene.get("events", [])
    if event_index < 0 or event_index >= len(events):
        raise IndexError(f"Event index {event_index} out of range.")

    old_time = events[event_index]["time"]
    events[event_index]["time"] = new_time
    events.sort(key=lambda e: e["time"])

    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
    return {
        "scene_id": scene_id,
        "event_index": event_index,
        "old_time": old_time,
        "new_time": new_time,
    }
