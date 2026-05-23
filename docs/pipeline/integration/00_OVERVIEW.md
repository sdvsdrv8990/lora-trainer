# Pipeline Integration — Master Map

> Temporary working docs. Promote to `PRODUCTION_PIPELINE.md` after each phase is verified.

## What Exists Right Now

| Surface | Status | File count |
|---|---|---|
| MCP server | ✅ 95 tools, all syntax-clean | `pipeline/src/mcp/server.py` |
| Remotion Python bridge | ✅ done | `src/remotion/render_jobs.py` + `renderer.py` |
| FCPXML exporter | ✅ done (1 known bug) | `src/davinci/exporter.py` |
| Lipsync wrapper | ✅ done | `src/audio/lipsync.py` |
| Remotion TypeScript | ❌ not built yet | `pipeline/remotion/` — missing |
| resolve-mcp integration | ❌ not wired | separate MCP server — needs install |

## The Three Groups

```
Group 1 — Remotion rendering
  Python bridge: done
  TypeScript layer: missing → must build
  Tools: pipeline_render_scene, pipeline_render_all_scenes,
         pipeline_get_remotion_status, pipeline_stop_render,
         pipeline_update_scene_event, pipeline_move_event,
         pipeline_preview_scene_event, pipeline_list_scene_events

Group 2 — DaVinci bridge
  FCPXML export: done (1 bug: relative paths)
  Tool: pipeline_export_davinci
  Extension: resolve-mcp makes this fully automated (no manual DaVinci steps)

Group 3 — Character rig + lipsync
  Lipsync module: done (rhubarb wrapper)
  Tool: pipeline_generate_lipsync
  Stickman components: missing → must build in pipeline/remotion/src/components/
```

## resolve-mcp: the key decision

**What it is:** 295-tool MCP server covering the entire DaVinci Resolve scripting API.
Source: https://github.com/jenkinsm13/resolve-mcp

**Architecture decision: separate MCP server, NOT wrapped inside our tools.**

Reasons:
- Wrapping 295 tools would double implementation work with no benefit
- Claude.ai can call both MCP servers in the same conversation
- resolve-mcp requires DaVinci Resolve running locally — impossible in cloud
- Our tools stay cloud-runnable; resolve-mcp runs only on user's local PC

**The handoff protocol:**
```
Our pipeline tools                          resolve-mcp tools
──────────────────────────────────────────  ─────────────────────────────────
pipeline_render_all_scenes                →  scenes ready in renders/scenes/
pipeline_export_davinci                   →  FCPXML written
                                              resolve_create_project (or load)
                                              resolve_import_media (mp4 files)
                                              resolve_import_into_timeline (FCPXML)
                                              resolve_add_marker_at × N (chapters)
                                              resolve_load_render_preset ("YouTube 1080p")
                                              resolve_add_render_job
                                              resolve_start_render
                                              resolve_get_render_status (monitor)
```

**What we do NOT build because resolve-mcp covers it:**

| Would have been our tool | resolve-mcp covers it with |
|---|---|
| DaVinci project creation | `resolve_create_project` |
| DaVinci media import | `resolve_import_media` |
| DaVinci timeline import | `resolve_import_into_timeline` |
| DaVinci render queue | `resolve_add_render_job`, `resolve_start_render`, `resolve_get_render_status`, `resolve_stop_render` |
| DaVinci render presets | `resolve_load_render_preset`, `resolve_set_render_settings` |
| DaVinci color grade | `resolve_apply_lut` + 11 more tools |
| DaVinci chapter markers | `resolve_add_marker_at` |

**Saved work: ~20 tools we don't need to implement.**

## Phase Order

```
Phase 0  pip install stable-ts[fw]          — DONE (code side); verify on local PC
Phase 1  Remotion TypeScript layer          — MISSING: build pipeline/remotion/
Phase 2  Remotion tools verify              — test pipeline_render_scene end-to-end
Phase 3  FCPXML bug fix + resolve-mcp wire  — fix relative paths; install resolve-mcp
Phase 4  Stickman + lipsync in Remotion    — build components/ and presets/
```

## Known Bugs to Fix

| Bug | File | Line | Fix |
|---|---|---|---|
| Relative file:// paths in FCPXML | `src/davinci/exporter.py` | 52 | Use `workspace / mp4_rel` to get absolute path |
| `render_scene_preview` raises NotImplementedError | `src/remotion/renderer.py` | 37 | Implement via Remotion renderStill CLI flag |

## Local PC Phase 2 Checklist (after each push)

1. `git pull origin claude/tender-albattani-75yGr`
2. `cd pipeline && source venv/bin/activate`
3. `pip install --upgrade setuptools && pip install stable-ts[fw]`
4. `pip install resolve-mcp` (or `uvx resolve-mcp` as separate process)
5. Build `pipeline/remotion/` TypeScript (see `02_REMOTION_LAYER.md`)
6. `bash pipeline/start.sh` → MCP server up
7. MCP SDK verify: expected count **95**
8. Test `pipeline_render_scene` on 1-scene workspace
9. Test `pipeline_export_davinci` → verify absolute paths in FCPXML
10. Open Resolve → `resolve_import_into_timeline` → check timeline
