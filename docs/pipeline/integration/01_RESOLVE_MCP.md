# resolve-mcp Integration Plan

Source: https://github.com/jenkinsm13/resolve-mcp
License: MIT
Install: `pip install resolve-mcp` or `uvx resolve-mcp`

## How resolve-mcp Connects to DaVinci Resolve

resolve-mcp uses DaVinci Resolve's local Python scripting API:

```python
# resolve_mcp/resolve.py — connection mechanism
import DaVinciResolveScript as dvr_script
resolve = dvr_script.scriptapp("Resolve")  # connects to running Resolve instance
```

**Preconditions (local PC only):**
- DaVinci Resolve must be running
- Scripting must be enabled: Preferences → System → General → "Enable remote scripting"
- Python 3.11+ (resolve-mcp requirement)

**This means resolve-mcp ONLY works on the local PC where Resolve is installed.**
It cannot run in the cloud session.

## Tools We Use From resolve-mcp

These are the tools that fit directly into our pipeline handoff.

### Project setup (run once per episode)

```
resolve_create_project(project_name)
  → creates "channel_scenario" project in Resolve

resolve_load_project(project_name)
  → opens existing project (if re-doing a pass)
```

### Media import

```
resolve_import_media(file_paths, target_bin)
  file_paths: comma-separated absolute paths to scene_001.mp4, scene_002.mp4, ...
  target_bin: "Scenes"
  → imports all scene mp4s into media pool

resolve_create_bin(bin_name)
  → creates "Scenes" bin before import
```

### Timeline import

```
resolve_import_into_timeline(file_path, import_options)
  file_path: absolute path to channel_scenario_davinci.fcpxml
  import_options: "{}"  (defaults work for FCPXML 1.10)
  → builds timeline from our FCPXML
```

### Chapter markers (from our timeline.json)

```
resolve_add_marker_at(frame, color, name, note, duration)
  → add one chapter marker

Called N times — once per scene using chapter field from timeline.json:
  frame = round(scene["start"] * fps)
  name  = scene["chapter"]
  color = "Blue"
```

### Color grade

```
resolve_load_render_preset(preset_name)
  → load saved LUT/grade preset by name

resolve_apply_lut(lut_path, track_type, track_index, item_index)
  → apply LUT to all clips

resolve_get_render_presets()
  → list available presets (call first to see what's available)
```

### Final delivery

```
resolve_set_render_settings(settings_json)
  settings_json: '{"SelectAllFrames": true, "ExportVideo": true, "ExportAudio": true}'

resolve_set_render_format_and_codec(format_name, codec_name)
  format_name: "MP4"
  codec_name: "H.264 Master"

resolve_add_render_job()
  → queues current settings as render job, returns job_id

resolve_start_render(job_ids)
  → starts rendering

resolve_get_render_status(job_id)
  → monitor: returns {CompletionPercentage, JobStatus, TimeRemainingInMs}

resolve_stop_render()
  → cancel if needed
```

## Tools We Ignore From resolve-mcp

These exist in resolve-mcp but we don't need them in our workflow:

| Category | Why we skip |
|---|---|
| Fusion composition tools | We use Remotion, not Fusion |
| Fairlight audio tools | Audio is baked into scene mp4s by Remotion |
| Dolby Vision / Stereo 3D | Not our use case |
| AI bridge tools (Gemini) | We use Claude, not Gemini |
| Timeline scene cut detection | Scenes are pre-defined in our layout |
| Smart Reframe | Not needed for 1080p explainer videos |
| Photo RAW tools | Not video workflow relevant |
| Layout preset tools | UI layout, not production workflow |

## Update to pipeline_export_davinci instructions

Current instruction text (in `src/workflow/instructions.py`) ends with:
```
"Claude's work ends here. DaVinci handles the rest."
```

**Update this to:**
```python
"pipeline_export_davinci_complete": (
    "FCPXML exported to {export_path}. "
    "{scenes_included} scenes, total duration {total_duration}s.\n\n"
    "If resolve-mcp is available (DaVinci running on local PC):\n"
    "  1. resolve_create_project(project_name='{project_name}')\n"
    "  2. resolve_create_bin(bin_name='Scenes')\n"
    "  3. resolve_import_media(file_paths='<absolute renders/scenes/*.mp4 paths>')\n"
    "  4. resolve_import_into_timeline(file_path='<absolute path to .fcpxml>')\n"
    "  5. resolve_add_marker_at × N — one per chapter from timeline.json\n"
    "  6. resolve_get_render_presets() — pick 'YouTube 1080p' or equivalent\n"
    "  7. resolve_load_render_preset(preset_name='...')\n"
    "  8. resolve_add_render_job()\n"
    "  9. resolve_start_render()\n"
    " 10. resolve_get_render_status(job_id) — poll until complete\n\n"
    "If resolve-mcp is NOT available:\n"
    "  File → Import → Timeline → select .fcpxml in DaVinci Resolve manually."
),
```

## Installation (local PC only)

### Option A — uvx (recommended, isolated)

```bash
uvx resolve-mcp
```

Add to Claude Code `.mcp.json`:
```json
{
  "mcpServers": {
    "resolve-mcp": {
      "command": "uvx",
      "args": ["resolve-mcp"]
    }
  }
}
```

### Option B — pip in pipeline venv

```bash
cd pipeline && source venv/bin/activate
pip install resolve-mcp
```

Start separately from our pipeline server:
```bash
python -m resolve_mcp
```

### Option C — Claude.ai second connector

Add `resolve-mcp` as a second MCP connector in Claude.ai settings alongside our pipeline connector.
Claude.ai can use both servers simultaneously in the same conversation.

**Recommended: Option A (uvx) + Option C (Claude.ai second connector)**

## FCPXML Path Bug That Must Be Fixed First

Before resolve-mcp can import our FCPXML, the file paths must be ABSOLUTE.

Current (broken):
```python
# src/davinci/exporter.py line 52
mp4_rel = f"renders/scenes/scene_{sid:03d}.mp4"
src=f"file://{mp4_rel}"          # → file://renders/scenes/scene_001.mp4  ← invalid
```

Required fix:
```python
def export_fcpxml(timeline_scenes, output_path, project_name, workspace_path):
    ...
    mp4_abs = workspace_path / f"renders/scenes/scene_{sid:03d}.mp4"
    src=f"file://{mp4_abs}"      # → file:///home/admin/.../renders/scenes/scene_001.mp4
```

And update the MCP tool call in server.py:
```python
davinci_exporter.export_fcpxml(scenes, out_path, project_name=project_name, workspace_path=ws)
```

This is a **blocking bug** — FCPXML with relative paths will fail to load in DaVinci.
Fix this in Phase 3 before testing resolve-mcp integration.
