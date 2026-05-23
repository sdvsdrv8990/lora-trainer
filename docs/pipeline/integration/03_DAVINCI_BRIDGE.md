# Group 2 — DaVinci Bridge

## Status

| Component | Status | Location |
|---|---|---|
| FCPXML generator | ✅ done (1 bug) | `src/davinci/exporter.py` |
| MCP tool | ✅ done | `server.py` lines 2285–2325 |
| resolve-mcp installation | ❌ not done | local PC only |
| `instructions.py` update | ❌ needed | add resolve-mcp workflow |
| FCPXML path bug | ❌ blocking | `exporter.py` line 52 |

## Layer Map (pipe-dev-guide)

```
Layer 0 — Entity: timeline scene dicts (from timeline.json)
Layer 1 — MCP tool: pipeline_export_davinci (done)
Layer 2 — Python module: src/davinci/exporter.py (done, 1 bug)
Layer 3 — External: resolve-mcp (separate MCP server, local PC)
Layer 4 — External: DaVinci Resolve running locally
```

## The FCPXML Path Bug (MUST FIX BEFORE PHASE 3)

### Problem

`exporter.py` line 52 generates invalid file URLs:
```python
mp4_rel = f"renders/scenes/scene_{sid:03d}.mp4"
src=f"file://{mp4_rel}"   # → file://renders/scenes/scene_001.mp4
```

DaVinci Resolve requires absolute file URLs:
```
file:///home/admin/projects/lora-trainer/data/mychannel/ep01/renders/scenes/scene_001.mp4
```

### Fix

**File:** `pipeline/src/davinci/exporter.py`

```python
# Change function signature:
def export_fcpxml(
    timeline_scenes: list[dict],
    output_path: Path,
    project_name: str = "Video",
    workspace_path: Path | None = None,   # ADD THIS
) -> Path:
    ...
    for scene in timeline_scenes:
        sid = scene["scene_id"]
        dur = float(scene.get("duration", 0))
        chapter = scene.get("chapter", f"Scene {sid}")

        asset_id = f"r_asset_{sid:03d}"

        # Fix: use absolute path
        if workspace_path:
            mp4_abs = (workspace_path / f"renders/scenes/scene_{sid:03d}.mp4").resolve()
            mp4_src = f"file://{mp4_abs}"
        else:
            mp4_src = f"file://renders/scenes/scene_{sid:03d}.mp4"  # fallback (broken)
```

**File:** `pipeline/src/mcp/server.py` — update the call:
```python
# line ~2307: change
davinci_exporter.export_fcpxml(scenes, out_path, project_name=project_name)
# to:
davinci_exporter.export_fcpxml(scenes, out_path, project_name=project_name, workspace_path=ws)
```

### Verification after fix

```bash
python3 -c "
from pathlib import Path
from src.davinci.exporter import export_fcpxml
scenes = [{'scene_id': 1, 'duration': 5.0, 'chapter': 'Test'}]
ws = Path('/tmp/test_ws')
out = Path('/tmp/test.fcpxml')
export_fcpxml(scenes, out, 'test', workspace_path=ws)
content = out.read_text()
assert 'file:///tmp/test_ws/renders' in content, 'Absolute path missing!'
print('OK:', content[content.find('file://'):content.find('file://')+60])
"
```

## FCPXML Format Reference

Generated format: FCPXML 1.10
Compatible with: DaVinci Resolve 18+, Final Cut Pro

Structure produced by `exporter.py`:
```xml
<?xml version="1.0" ?>
<fcpxml version="1.10">
  <resources>
    <format id="r_fmt_1080p30" name="FFVideoFormat1080p30"
            width="1920" height="1080" frameDuration="100/3000s"/>
    <asset id="r_asset_001" name="scene_001"
           src="file:///abs/path/renders/scenes/scene_001.mp4"
           format="r_fmt_1080p30" duration="8.200s" hasVideo="1" hasAudio="1"/>
    ...
  </resources>
  <library>
    <event name="channel_scenario">
      <project name="channel_scenario">
        <sequence duration="147.357s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">
          <spine>
            <asset-clip ref="r_asset_001" offset="0.000s" duration="8.200s"
                        name="Chapter 1" tcFormat="NDF"/>
            ...
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
```

## resolve-mcp Integration Workflow

After `pipeline_export_davinci` runs, Claude calls resolve-mcp tools to automate DaVinci.

### Step-by-step with resolve-mcp

```
1. resolve_create_project(project_name="channel_scenario")
   ← Creates new Resolve project

2. resolve_create_bin(bin_name="Scenes")
   ← Creates "Scenes" bin in media pool

3. resolve_import_media(
     file_paths="/abs/.../renders/scenes/scene_001.mp4, /abs/.../scene_002.mp4, ...",
     target_bin="Scenes"
   )
   ← Imports all scene mp4s

4. resolve_import_into_timeline(
     file_path="/abs/.../renders/channel_scenario_davinci.fcpxml",
     import_options="{}"
   )
   ← Builds timeline from FCPXML, all clips in correct order

5. [Optional] resolve_add_marker_at(frame=0, color="Blue", name="Chapter 1", note="", duration=1)
   resolve_add_marker_at(frame=246, color="Blue", name="Chapter 2", ...)  ← frame = round(start_sec * fps)
   ...for each scene with chapter name

6. resolve_get_render_presets()
   ← Lists presets; choose "YouTube 1080p" or similar

7. resolve_load_render_preset(preset_name="YouTube 1080p")
   ← Configures render settings

8. resolve_add_render_job()
   ← Returns job_id

9. resolve_start_render(job_ids="<job_id>")
   ← Starts encoding

10. resolve_get_render_status(job_id="<job_id>")
    ← Poll until CompletionPercentage == 100
    ← Output file path in render settings
```

### Chapter frame calculation (Python helper for instructions)

```python
def chapters_to_frames(timeline_scenes: list[dict], fps: int = 30) -> list[dict]:
    return [
        {
            "frame": round(float(s["start"]) * fps),
            "name": s.get("chapter", f"Scene {s['scene_id']}"),
        }
        for s in timeline_scenes
        if s.get("chapter")
    ]
```

This runs inside the `pipeline_export_davinci` tool to include chapter frames in the response data.

## pipeline_export_davinci data shape — after fix

```json
{
  "ok": true,
  "data": {
    "export_path": "renders/channel_ep01_davinci.fcpxml",
    "export_path_abs": "/home/.../renders/channel_ep01_davinci.fcpxml",
    "scenes_included": 7,
    "total_duration": 147.357,
    "format": "fcpxml",
    "chapter_frames": [
      {"frame": 0,   "name": "Intro"},
      {"frame": 246, "name": "Problem"},
      {"frame": 651, "name": "Solution"}
    ],
    "resolve_mcp_steps": "If resolve-mcp available: resolve_create_project → resolve_import_media → resolve_import_into_timeline → resolve_add_marker_at × N → resolve_load_render_preset → resolve_add_render_job → resolve_start_render"
  }
}
```

## instructions.py Update

Replace current `pipeline_export_davinci` instruction with:

```python
"pipeline_export_davinci": (
    "FCPXML exported: {export_path}. {scenes_included} scenes, {total_duration}s.\n\n"
    "─── With resolve-mcp (DaVinci running on local PC) ───\n"
    "  resolve_create_project → resolve_create_bin('Scenes') → resolve_import_media\n"
    "  → resolve_import_into_timeline → resolve_add_marker_at × {scene_count}\n"
    "  → resolve_load_render_preset → resolve_add_render_job → resolve_start_render\n"
    "  → resolve_get_render_status (poll until 100%)\n\n"
    "─── Without resolve-mcp ───\n"
    "  DaVinci: File → Import → Timeline → select .fcpxml\n"
    "  All {scenes_included} scenes appear in timeline. Add transitions, grade, Deliver.\n"
),
```

## Phase 3 Checklist

- [ ] Fix `exporter.py` — absolute paths (blocking)
- [ ] Add `export_path_abs` and `chapter_frames` to tool response data
- [ ] Update `instructions.py` entry
- [ ] Install resolve-mcp on local PC: `pip install resolve-mcp` or `uvx resolve-mcp`
- [ ] Enable Resolve scripting: Preferences → System → General
- [ ] Test: open Resolve → call `resolve_import_into_timeline` → timeline appears
- [ ] Test: `resolve_start_render` → final mp4 produced

## Module Boundary Rule

`src/davinci/exporter.py` has one responsibility:
**Generate valid FCPXML from a list of timeline scene dicts.**

It does NOT:
- Call resolve-mcp (that's Claude's job via the separate MCP server)
- Know about workspace state or `state.json`
- Read `timeline.json` directly (server.py passes the data)
