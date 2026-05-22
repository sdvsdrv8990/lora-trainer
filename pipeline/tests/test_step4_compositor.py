"""E2E smoke test: create project → upload SVG asset → submit scene_layout → render_frames → verify PNGs.

Compositor tests require Pillow: pip install "vidpipe[compositing]"
"""
import json
import tempfile
from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL", reason="Pillow not installed; install with: pip install 'vidpipe[compositing]'")

from src.images import assets as asset_lib
from src.images import layout_store
from src.images import render_jobs
from src.images.adapters.stub import StubAdapter
from src.registry import load_project, add_registry_row, get_video_structure, set_video_structure

MINIMAL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
    '<rect width="100" height="100" fill="#PLACEHOLDER_COLOR"/>'
    "</svg>"
)

SCENE_LAYOUT = {
    "total_frames": 2,
    "canvas": {"width": 320, "height": 240},
    "frames": [
        {
            "frame_id": 1,
            "scene_id": 1,
            "start": 0.0,
            "end": 2.0,
            "module_type": "HOOK",
            "background": "#FFFFFF",
            "appearance_order": [],
            "layers": [
                {
                    "id": "char1",
                    "type": "character",
                    "asset_id": "P-CHR-001-001",
                    "asset_path": "assets/characters/crowd/test_char.svg",
                    "color": "#FFD700",
                    "emotion": "happy",
                    "x": 10, "y": 10, "scale": 0.5, "flip_x": False,
                }
            ],
            "notes": "test frame 1",
        },
        {
            "frame_id": 2,
            "scene_id": 1,
            "start": 2.0,
            "end": 4.0,
            "module_type": "SETUP",
            "background": "#F0F0F0",
            "appearance_order": [],
            "layers": [
                {
                    "id": "text1",
                    "type": "text",
                    "text": "Hello",
                    "font": "Arial",
                    "font_size": 24,
                    "color": "#000000",
                    "x": 50, "y": 50,
                }
            ],
            "notes": "test frame 2",
        },
    ],
}


def test_e2e_compositor(tmp_path):
    workspace = tmp_path / "testchannel" / "test_scenario"
    workspace.mkdir(parents=True)
    (workspace / "images").mkdir()
    (workspace / "assets").mkdir(parents=True)
    (workspace / "md").mkdir()

    # Upload project-scoped SVG asset
    result = asset_lib.upload_asset(
        workspace=workspace,
        category="characters/crowd",
        name="test_char",
        svg_content=MINIMAL_SVG,
        scope="project",
    )
    assert result["id"] is not None
    asset_path = workspace / "assets" / "characters" / "crowd" / "test_char.svg"
    assert asset_path.exists()

    # List assets - project scope
    listing = asset_lib.list_assets(workspace=workspace, scope="project")
    assert listing["total"] >= 1
    assert any(a["name"] == "test_char" for a in listing["assets"])

    # Search assets
    search = asset_lib.search_assets(workspace=workspace, query="test", scope="project")
    assert search["total"] >= 1

    # Submit scene_layout
    save_result = layout_store.save_layout(workspace, SCENE_LAYOUT)
    assert save_result["frame_count"] == 2
    assert save_result["total_frames"] == 2

    # Render frames (synchronous with stub engine)
    engine = StubAdapter()
    status = render_jobs.start(workspace, engine, wait=True)
    assert status["status"] == "complete"
    assert status["completed_frames"] == 2

    # Verify PNGs exist
    for fid in [1, 2]:
        png = workspace / "images" / f"frame_{fid:04d}.png"
        assert png.exists(), f"Expected frame PNG not found: {png}"

    # List frames
    frames = render_jobs.list_frames(workspace)
    assert frames["total_ready"] == 2
    assert frames["total_expected"] == 2

    # Preview frame
    preview = render_jobs.preview_frame(workspace, engine, 1)
    assert preview["exists"]


def test_registry_operations(tmp_path):
    workspace = tmp_path / "chan" / "scen"
    workspace.mkdir(parents=True)

    # Load (creates default)
    data = load_project(workspace)
    assert "sheets" in data
    assert "scenes" in data["sheets"]

    # Add row
    result = add_registry_row(workspace, "project", "scenes", {"scene_id": "1", "start": "0.0", "end": "3.5", "module_type": "HOOK", "notes": ""})
    assert result["row"]["scene_id"] == "1"

    # Set video structure
    structure = {
        "hook_type": "price_conflict",
        "hook_duration": 5,
        "pattern": "HOOK→SETUP→DISRUPTION→PAYOFF",
        "modules": ["HOOK", "SETUP", "DISRUPTION", "PAYOFF"],
        "reset_points": [15, 45],
        "reward_type": "story",
        "audience_expectation_profile": "curious_buyer",
    }
    s_result = set_video_structure(workspace, structure)
    assert s_result["modules"] == 4
    assert s_result["reset_points"] == 2

    # Get structure back
    retrieved = get_video_structure(workspace)
    assert retrieved["hook_type"] == "price_conflict"
    assert retrieved["reward_type"] == "story"
