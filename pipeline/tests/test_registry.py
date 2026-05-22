"""Registry and asset library unit tests (no PIL required)."""
from pathlib import Path

from src.images import assets as asset_lib
from src.images import layout_store
from src.registry import (
    add_emotion_map, add_registry_column, add_registry_row, add_registry_sheet,
    get_global_stats, get_video_structure, load_project, query_registry,
    set_video_structure,
)

MINIMAL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
    '<rect width="100" height="100" fill="#PLACEHOLDER_COLOR"/>'
    "</svg>"
)


def test_upload_and_list_assets(tmp_path):
    ws = tmp_path / "chan" / "scen"
    ws.mkdir(parents=True)

    result = asset_lib.upload_asset(
        workspace=ws,
        category="characters/crowd",
        name="test_char",
        svg_content=MINIMAL_SVG,
        scope="project",
    )
    assert result["id"] is not None
    assert result["id"].startswith("P-CHR-")
    assert (ws / "assets" / "characters" / "crowd" / "test_char.svg").exists()

    listing = asset_lib.list_assets(workspace=ws, scope="project")
    assert listing["total"] >= 1
    assert any(a["name"] == "test_char" for a in listing["assets"])


def test_search_assets(tmp_path):
    ws = tmp_path / "chan" / "scen"
    ws.mkdir(parents=True)
    asset_lib.upload_asset(ws, "objects/money", "coin", MINIMAL_SVG, scope="project")
    asset_lib.upload_asset(ws, "objects/money", "banknote", MINIMAL_SVG, scope="project")

    result = asset_lib.search_assets(ws, query="coin", scope="project")
    assert result["total"] == 1
    assert result["assets"][0]["name"] == "coin"


def test_delete_asset(tmp_path):
    ws = tmp_path / "chan" / "scen"
    ws.mkdir(parents=True)
    upload = asset_lib.upload_asset(ws, "objects/money", "coin", MINIMAL_SVG, scope="project")
    asset_id = upload["id"]

    del_result = asset_lib.delete_asset(ws, asset_id)
    assert del_result["deleted"] == asset_id
    assert not (ws / "assets" / "objects" / "money" / "coin.svg").exists()


def test_resolve_asset_path(tmp_path):
    ws = tmp_path / "chan" / "scen"
    ws.mkdir(parents=True)
    asset_lib.upload_asset(ws, "characters/crowd", "hero", MINIMAL_SVG, scope="project")

    path = asset_lib.resolve_asset_path("assets/characters/crowd/hero.svg", workspace=ws)
    assert path.exists()


def test_layout_store_save_and_load(tmp_path):
    ws = tmp_path / "chan" / "scen"
    (ws / "md").mkdir(parents=True)

    layout = {
        "total_frames": 1,
        "canvas": {"width": 320, "height": 240},
        "frames": [
            {
                "frame_id": 1, "scene_id": 1, "start": 0.0, "end": 2.0,
                "module_type": "HOOK", "background": "#FFFFFF",
                "appearance_order": [],
                "layers": [
                    {"id": "t1", "type": "text", "text": "Test", "font": "Arial",
                     "font_size": 24, "color": "#000000", "x": 10, "y": 10}
                ],
                "notes": "",
            }
        ],
    }
    result = layout_store.save_layout(ws, layout)
    assert result["frame_count"] == 1

    loaded = layout_store.load_layout(ws)
    assert loaded.total_frames == 1
    assert loaded.frames[0].frame_id == 1

    updated = layout_store.update_frame(ws, 1, [
        {"id": "t2", "type": "text", "text": "Updated", "font": "Arial",
         "font_size": 24, "color": "#FF0000", "x": 20, "y": 20}
    ])
    assert updated["layers_updated"] == 1


def test_registry_project_operations(tmp_path):
    ws = tmp_path / "chan" / "scen"
    ws.mkdir(parents=True)

    data = load_project(ws)
    assert "sheets" in data
    assert "scenes" in data["sheets"]
    assert "emotion_map" in data["sheets"]

    row = add_registry_row(ws, "project", "scenes", {
        "scene_id": "1", "start": "0.0", "end": "3.5", "module_type": "HOOK", "notes": "test"
    })
    assert row["row"]["scene_id"] == "1"

    result = query_registry(ws, "project", "scenes", "module_type", "HOOK")
    assert result["total"] == 1

    add_registry_column(ws, "project", "scenes", "new_col", "default")
    data2 = load_project(ws)
    assert "new_col" in data2["sheets"]["scenes"]["columns"]

    add_registry_sheet(ws, "project", "custom_sheet", ["col_a", "col_b"])
    data3 = load_project(ws)
    assert "custom_sheet" in data3["sheets"]


def test_video_structure(tmp_path):
    ws = tmp_path / "chan" / "scen"
    ws.mkdir(parents=True)

    structure = {
        "hook_type": "price_conflict",
        "hook_duration": 5,
        "pattern": "HOOK→PAYOFF",
        "modules": ["HOOK", "SETUP", "PAYOFF"],
        "reset_points": [15, 45],
        "reward_type": "story",
        "audience_expectation_profile": "curious_buyer",
    }
    result = set_video_structure(ws, structure)
    assert result["modules"] == 3
    assert result["reset_points"] == 2

    retrieved = get_video_structure(ws)
    assert retrieved["hook_type"] == "price_conflict"


def test_emotion_map(tmp_path):
    ws = tmp_path / "chan" / "scen"
    ws.mkdir(parents=True)

    entries = [
        {"time_start": "0.0", "time_end": "5.0", "emotion": "curiosity",
         "module": "HOOK", "intensity": "high", "visual_support": "close-up", "audio_support": "tense"},
        {"time_start": "5.0", "time_end": "15.0", "emotion": "engagement",
         "module": "SETUP", "intensity": "medium", "visual_support": "wide", "audio_support": "calm"},
    ]
    result = add_emotion_map(ws, entries)
    assert result["added"] == 2
    assert result["total"] == 2


def test_global_stats():
    stats = get_global_stats()
    assert "sheets" in stats
    assert "total_sheets" in stats
