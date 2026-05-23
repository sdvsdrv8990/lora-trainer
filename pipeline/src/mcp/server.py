import json
import logging
import os
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from pathlib import Path
from typing import Annotated
import yaml
from pydantic import Field

_log = logging.getLogger(__name__)

from src.project import manager, state as state_mod
from src.project import config as project_config
from src.scenario import builder as scenario_builder
from src.tts import jobs as voiceover_jobs
from src.audio import analyzer as audio_analyzer
from src.audio import transcriber as audio_transcriber
from src.images import prompts as image_prompts
from src.images import batch as image_batch
from src.images import assets as asset_lib
from src.images import render_jobs
from src.images import layout_store
from src.images import engine_profiles
from src.images import character_jobs
from src.images.engine import get_image_engine
from src.images.compositor import CAIROSVG_AVAILABLE as _CAIROSVG_AVAILABLE
from src.assembly import ffmpeg as assembler
from src.assembly import jobs as assembly_jobs
from src import registry as reg
from src.entities.project import ProjectConfig
from src.entities.state import StepStatus
from src.workflow.instructions import get_instructions
from src.remotion import render_jobs as remotion_jobs
from src.davinci import exporter as davinci_exporter
from src.audio import lipsync as lipsync_mod


def _load_config() -> dict:
    cfg_path = Path(__file__).parent.parent.parent / "config" / "pipeline.yaml"
    return yaml.safe_load(cfg_path.read_text())


def _load_engine_config() -> dict:
    cfg_path = Path(__file__).parent.parent.parent / "config" / "engines.yaml"
    return yaml.safe_load(cfg_path.read_text())


_cfg = _load_config()
_engine_cfg = _load_engine_config()
_base_dir = Path(_cfg["projects"]["base_dir"]).expanduser()
_subdirs: list[str] = _cfg["subdirs"]
_engines_yaml_path = Path(__file__).parent.parent.parent / "config" / "engines.yaml"

_public_url = os.environ.get("VIDPIPE_PUBLIC_URL", "").rstrip("/")

ChannelArg = Annotated[str, Field(description="Top-level video channel or project name.")]
ScenarioArg = Annotated[str, Field(description="Scenario or sub-project name inside the channel.")]
WorkspacePathArg = Annotated[str, Field(description="Relative file path inside the scenario workspace.")]
DirectoryArg = Annotated[str, Field(description="Relative directory path inside the scenario workspace. Use an empty string for the workspace root.")]
TtsInputArg = Annotated[str, Field(description="JSON-encoded array of scene objects. Each object must have scene_id, chapter, text, tts, and metadata fields.")]
WaitArg = Annotated[str, Field(description="Use 'true' to run synchronously; default 'false' starts a background job.")]
ConfigJsonArg = Annotated[str, Field(description="JSON-encoded project_config object with project, style, frame_rules, audio, and prompts sections.")]
PromptsJsonArg = Annotated[str, Field(description="JSON-encoded image_prompts object with batch_size, total_frames, and batches array.")]
BatchIdArg = Annotated[str, Field(description="Batch ID as a numeric string (e.g. '1', '2').")]
WhisperModelArg = Annotated[str, Field(description="Whisper model size: tiny, base, small, medium, or large.")]
LanguageArg = Annotated[str, Field(description="Language code for transcription (e.g. 'ru', 'en'). Empty string for auto-detect.")]
ScopeArg = Annotated[str, Field(description="Asset scope: 'global' for shared assets, 'project' for scenario-specific assets.")]
SheetArg = Annotated[str, Field(description="Registry sheet name (e.g. 'assets', 'scenes', 'hooks', 'emotion_map', 'performance', 'insights').")]

if _public_url:
    from src.mcp.oauth import LocalOAuthProvider
    _mcp_path = _cfg["server"]["path"]
    _resource_url = f"{_public_url}{_mcp_path}"
    _oauth = LocalOAuthProvider()
    _auth_settings = AuthSettings(
        issuer_url=_public_url,
        client_registration_options=ClientRegistrationOptions(enabled=True),
        resource_server_url=_resource_url,
    )
    mcp = FastMCP(
        _cfg["server"]["name"],
        host=_cfg["server"]["host"],
        port=_cfg["server"]["port"],
        streamable_http_path=_cfg["server"]["path"],
        auth=_auth_settings,
        auth_server_provider=_oauth,
    )
    mcp._token_verifier = None
else:
    mcp = FastMCP(
        _cfg["server"]["name"],
        host=_cfg["server"]["host"],
        port=_cfg["server"]["port"],
        streamable_http_path=_cfg["server"]["path"],
    )


def _workspace(channel: str, scenario: str) -> Path:
    return _base_dir / channel / scenario


def _parse_wait(wait: str) -> bool:
    return wait.strip().lower() in {"1", "true", "yes", "y"}


# ─── Step 0 / 1 ───────────────────────────────────────────────────────────────

@mcp.tool()
def pipeline_check_project(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Check if a project/sub-project exists for a given channel and scenario."""
    try:
        ws = _workspace(channel, scenario)
        return {
            "ok": True,
            "data": {
                "channel_exists": (_base_dir / channel).exists(),
                "scenario_exists": ws.exists(),
                "workspace": str(ws) if ws.exists() else None,
            },
            "instructions": "",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_create_project(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Optional channel_id to inherit channel_config defaults into project_config.")] = "",
) -> dict:
    """Create project and sub-project directory structure. If channel_id given, inherits channel_config defaults."""
    try:
        cfg = ProjectConfig(channel=channel, scenario=scenario)
        ctx = manager.resolve_workspace(cfg, _base_dir, _subdirs)
        if not ctx.existed:
            state_mod.init(ctx.workspace, channel, scenario)
            # Auto-seed project_config from channel_config if channel_id provided
            if channel_id:
                try:
                    from src.channel.manager import build_project_config_from_channel
                    from src.project import config as project_config
                    base_cfg = build_project_config_from_channel(channel_id)
                    if base_cfg:
                        project_config.save(ctx.workspace, base_cfg)
                except Exception:
                    pass
        return {
            "ok": True,
            "data": {
                "workspace": str(ctx.workspace),
                "created": not ctx.existed,
                "channel_id": channel_id or None,
            },
            "instructions": get_instructions("pipeline_create_project"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_delete_project(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Delete a scenario directory and all its contents. Also removes the channel directory if it becomes empty."""
    try:
        cfg = ProjectConfig(channel=channel, scenario=scenario)
        result = manager.delete_workspace(cfg, _base_dir)
        return {"ok": True, "data": result, "instructions": ""}
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── State management ─────────────────────────────────────────────────────────

@mcp.tool()
def pipeline_get_state(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Return current state.json for a sub-project."""
    try:
        ws = _workspace(channel, scenario)
        s = state_mod.load(ws)
        return {"ok": True, "data": s.model_dump(mode="json"), "instructions": ""}
    except FileNotFoundError:
        return {"ok": False, "error": f"No state.json for {channel}/{scenario}. Run pipeline_create_project first."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_set_state(
    channel: ChannelArg,
    scenario: ScenarioArg,
    step: Annotated[str, Field(description="Pipeline step number as a numeric string.")],
    status: Annotated[str, Field(description="New step status: pending, in_progress, complete, or failed.")],
) -> dict:
    """Update state.json. Claude calls this to advance or reset a pipeline step."""
    try:
        ws = _workspace(channel, scenario)
        s = state_mod.set_step(ws, int(step), StepStatus(status))
        return {"ok": True, "data": s.model_dump(mode="json"), "instructions": ""}
    except ValueError as e:
        if "invalid literal" in str(e):
            return {"ok": False, "error": "step must be a numeric string"}
        valid = [e.value for e in StepStatus]
        return {"ok": False, "error": f"Invalid status '{status}'. Must be one of: {valid}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── File access (scoped to workspace) ────────────────────────────────────────

@mcp.tool()
def pipeline_read_file(channel: ChannelArg, scenario: ScenarioArg, path: WorkspacePathArg) -> dict:
    """Read a file inside the scenario workspace. path is relative to the scenario directory."""
    try:
        ws = _workspace(channel, scenario).resolve()
        target = (ws / path).resolve()
        if not str(target).startswith(str(ws)):
            return {"ok": False, "error": "Path traversal not allowed"}
        if not target.exists():
            return {"ok": False, "error": f"File not found: {path}"}
        return {"ok": True, "data": {"content": target.read_text(), "path": str(target)}, "instructions": ""}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_write_file(
    channel: ChannelArg,
    scenario: ScenarioArg,
    path: WorkspacePathArg,
    content: Annotated[str, Field(description="Full text content to write to the file.")],
) -> dict:
    """Write a file inside the scenario workspace. path is relative to the scenario directory."""
    try:
        ws = _workspace(channel, scenario).resolve()
        target = (ws / path).resolve()
        if not str(target).startswith(str(ws)):
            return {"ok": False, "error": "Path traversal not allowed"}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return {"ok": True, "data": {"path": str(target)}, "instructions": ""}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_list_files(channel: ChannelArg, scenario: ScenarioArg, directory: DirectoryArg = "") -> dict:
    """List files in a directory inside the scenario workspace."""
    try:
        ws = _workspace(channel, scenario).resolve()
        target = (ws / directory).resolve() if directory else ws
        if not str(target).startswith(str(ws)):
            return {"ok": False, "error": "Path traversal not allowed"}
        if not target.exists():
            return {"ok": False, "error": f"Directory not found: {directory or '/'}"}
        entries = sorted(
            str(f.relative_to(ws)) + ("/" if f.is_dir() else "")
            for f in target.iterdir()
        )
        return {"ok": True, "data": {"files": entries, "workspace": str(ws)}, "instructions": ""}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Step 1.5: project config ─────────────────────────────────────────────────

@mcp.tool()
def pipeline_save_project_config(
    channel: ChannelArg,
    scenario: ScenarioArg,
    config_json: ConfigJsonArg,
) -> dict:
    """Save project_config.json to the scenario workspace root. Claude forms this config in dialogue with the user."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}. Run pipeline_create_project first."}
        data = json.loads(config_json)
        result = project_config.save(ws, data)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_save_project_config"),
        }
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON in config_json: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_get_project_config(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Return the saved project_config.json for a scenario workspace."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}. Run pipeline_create_project first."}
        data = project_config.load(ws)
        up = data.get("user_preferences", {})
        instr = get_instructions("pipeline_get_project_config", {
            "channel_id": data.get("channel_id", ""),
            "analytics_review": up.get("analytics_review_before_scenario", True),
            "competitor_review": up.get("competitor_review_before_scenario", False),
            "frame_change_conditions": up.get("frame_change_conditions", []),
            "scene_count": up.get("scene_count", "auto"),
            "platform_target": up.get("platform_target", ""),
        })
        return {"ok": True, "data": data, "instructions": instr}
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Step 2: scenario and voiceover ───────────────────────────────────────────

@mcp.tool()
def pipeline_submit_scenario(
    channel: ChannelArg,
    scenario: ScenarioArg,
    tts_input: TtsInputArg,
) -> dict:
    """Accept a confirmed tts_input (JSON array of scenes), save tts_input.json and scenario.txt."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}. Run pipeline_create_project first.", "step": 2}
        scenes = json.loads(tts_input)
        if not isinstance(scenes, list):
            return {"ok": False, "error": "tts_input must be a JSON array of scene objects.", "step": 2}
        result = scenario_builder.write_scenario(ws, scenes)
        status = voiceover_jobs.mark_scenario_received(ws, result["scene_count"], result["tts_input_path"])
        return {
            "ok": True,
            "data": {**result, "status": status, "message": "Scenario received and prepared for voiceover."},
            "instructions": get_instructions("pipeline_submit_scenario", {"scene_count": result["scene_count"]}),
        }
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON in tts_input: {e}", "step": 2}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 2}


@mcp.tool()
def pipeline_start_voiceover(channel: ChannelArg, scenario: ScenarioArg, wait: WaitArg = "false") -> dict:
    """Start generating audio files from md/tts_input.json. Use status tool to monitor background jobs."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}. Run pipeline_create_project first.", "step": 2}
        should_wait = _parse_wait(wait)
        status = voiceover_jobs.start(ws, _engine_cfg, wait=should_wait)
        if status.get("status") == "complete":
            instr = get_instructions(
                "pipeline_start_voiceover_complete",
                {"completed": status.get("completed_scenes", 0), "total": status.get("total_scenes", 0)},
            )
        else:
            instr = get_instructions(
                "pipeline_start_voiceover_running",
                {"total": status.get("total_scenes", 0)},
            )
        return {"ok": True, "data": status, "instructions": instr}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 2}


@mcp.tool()
def pipeline_get_voiceover_status(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Return current voiceover workflow status for this workspace."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 2}
        status = voiceover_jobs.read_status(ws)
        instr = get_instructions("pipeline_get_voiceover_status", {
            "status": status.get("status", "pending"),
            "completed": status.get("completed_scenes", 0),
            "total": status.get("total_scenes", 0),
        })
        return {"ok": True, "data": status, "instructions": instr}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 2}


@mcp.tool()
def pipeline_stop_voiceover(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Request cancellation of a running voiceover job."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 2}
        result = voiceover_jobs.stop(ws)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_stop_voiceover"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 2}


# ─── Step 3: timeline ─────────────────────────────────────────────────────────

@mcp.tool()
def pipeline_build_timeline(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Measure audio file durations with ffprobe and write md/timeline.json."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 3}
        timeline = audio_analyzer.build_timeline(ws)
        total_duration = round(sum(e["duration"] for e in timeline), 3)
        return {
            "ok": True,
            "data": {"scene_count": len(timeline), "total_duration": total_duration, "timeline_path": str(ws / "md" / "timeline.json")},
            "instructions": get_instructions("pipeline_build_timeline", {"scene_count": len(timeline), "total_duration": total_duration}),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e), "step": 3}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 3}


@mcp.tool()
def pipeline_get_timeline(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Return the full md/timeline.json so Claude can plan the visual track."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 3}
        timeline = audio_analyzer.load_timeline(ws)
        total_duration = round(sum(e["duration"] for e in timeline), 3)
        return {
            "ok": True,
            "data": {"timeline": timeline, "scene_count": len(timeline), "total_duration": total_duration},
            "instructions": get_instructions("pipeline_get_timeline", {"scene_count": len(timeline), "total_duration": total_duration}),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e), "step": 3}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 3}


# ─── Step 3.5: transcription ──────────────────────────────────────────────────

@mcp.tool()
def pipeline_transcribe_scenes(
    channel: ChannelArg,
    scenario: ScenarioArg,
    model: WhisperModelArg = "base",
    language: LanguageArg = "ru",
    vad: Annotated[str, "Use Silero VAD for silence detection ('true'/'false'). Better for noisy audio."] = "false",
    suppress_silence: Annotated[str, "Clip word timestamps to non-silent regions ('true'/'false')."] = "true",
) -> dict:
    """Run stable-whisper (faster-whisper backend) on all scene audio files.

    Enriches md/timeline.json with:
    - words[]: flat list with {word, start, end, confidence}
    - segments[]: natural linguistic groups with {start, end, text, words[]}

    Also saves md/stable_result_scene_NNN.json per scene for subtitle export and re-alignment.
    """
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 3}
        result = audio_transcriber.transcribe_scenes(
            ws,
            model_name=model,
            language=language,
            vad=vad.lower() == "true",
            suppress_silence=suppress_silence.lower() == "true",
        )
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_transcribe_scenes", {"scene_count": result["scene_count"], "total_words": result["total_words"]}),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e), "step": 3}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 3}


@mcp.tool()
def pipeline_export_subtitles(
    channel: ChannelArg,
    scenario: ScenarioArg,
    format: Annotated[str, "Subtitle format: 'srt', 'vtt', 'ass', 'tsv', 'txt'."] = "srt",
    scene_ids: Annotated[str, "Comma-separated scene IDs to export, or 'all' for all scenes."] = "all",
    word_level: Annotated[str, "Add word-by-word highlighting in ASS format ('true'/'false')."] = "false",
) -> dict:
    """Export subtitles from stable-ts transcription results.

    Reads md/stable_result_scene_NNN.json (written by pipeline_transcribe_scenes).
    Exports to md/subtitles/scene_NNN.<format>.

    Formats: srt (DaVinci/YouTube), vtt (web), ass (karaoke), tsv, txt.
    Run pipeline_transcribe_scenes first if files are missing.
    """
    from src.audio import subtitle_exporter
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        ids = None if scene_ids.strip().lower() == "all" else [int(x) for x in scene_ids.split(",")]
        exported = subtitle_exporter.export_subtitles(
            ws, ids, fmt=format, word_level=word_level.lower() == "true"
        )
        return {
            "ok": True,
            "data": {
                "exported": exported,
                "count": len(exported),
                "format": format,
                "directory": str(ws / "md" / "subtitles"),
            },
            "instructions": get_instructions("pipeline_export_subtitles", {"count": len(exported), "format": format}),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_align_scene(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scene_id: Annotated[int, "Scene ID to re-align."],
    corrected_text: Annotated[str, "Corrected transcript text for this scene. Must match the spoken audio."],
    model: WhisperModelArg = "base",
    language: LanguageArg = "ru",
) -> dict:
    """Re-align a corrected transcript to scene audio without re-transcribing.

    Use when you know the correct text but timestamps are wrong or drifted.
    Much faster than pipeline_transcribe_scenes (no speech recognition — only alignment).
    Updates timeline.json words[] and segments[] for this scene only.
    Also overwrites md/stable_result_scene_NNN.json for subtitle export.
    """
    from src.audio import subtitle_exporter
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        result = subtitle_exporter.align_scene(
            ws, scene_id=scene_id, corrected_text=corrected_text,
            model_name=model, language=language,
        )
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_align_scene", result),
        }
    except (FileNotFoundError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Step 4 (legacy): image prompts ──────────────────────────────────────────

@mcp.tool()
def pipeline_submit_prompts(
    channel: ChannelArg,
    scenario: ScenarioArg,
    prompts_json: PromptsJsonArg,
) -> dict:
    """Accept Claude-formed image_prompts JSON and write md/image_prompts.json."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 4}
        data = json.loads(prompts_json)
        result = image_prompts.save_prompts(ws, data)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_submit_prompts", {"total_frames": result["total_frames"], "batch_count": result["batch_count"], "batch_size": result["batch_size"]}),
        }
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON in prompts_json: {e}", "step": 4}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 4}


@mcp.tool()
def pipeline_get_prompts(channel: ChannelArg, scenario: ScenarioArg, batch_id: BatchIdArg) -> dict:
    """Return a specific prompt batch by batch_id."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 4}
        batch = image_prompts.get_batch(ws, int(batch_id))
        return {"ok": True, "data": batch, "instructions": ""}
    except ValueError as e:
        if "invalid literal" in str(e):
            return {"ok": False, "error": "batch_id must be a numeric string", "step": 4}
        return {"ok": False, "error": str(e), "step": 4}
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e), "step": 4}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 4}


@mcp.tool()
def pipeline_generate_images(
    channel: ChannelArg,
    scenario: ScenarioArg,
    batch_id: Annotated[str, Field(description="Batch ID to generate as a numeric string. Empty string generates all batches.")] = "",
    wait: WaitArg = "false",
) -> dict:
    """Generate images from md/image_prompts.json. Saves frames to images/frame_{frame_id:04d}.png."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 4}
        engine = get_image_engine(_engine_cfg)
        bid: int | None = int(batch_id) if batch_id.strip() else None
        result = image_batch.generate(ws, engine, batch_id=bid)
        if result["status"] == "complete":
            instr = get_instructions("pipeline_generate_images_complete", {"completed": result["completed_frames"], "total": result["total_frames"]})
        else:
            instr = get_instructions("pipeline_generate_images_running", {"total": result["total_frames"]})
        return {"ok": True, "data": result, "instructions": instr}
    except (ValueError, FileNotFoundError) as e:
        return {"ok": False, "error": str(e), "step": 4}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 4}


@mcp.tool()
def pipeline_get_generation_status(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Return current image generation status from md/generation_status.json."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 4}
        status = image_batch.read_status(ws)
        return {
            "ok": True,
            "data": status,
            "instructions": get_instructions("pipeline_get_generation_status", {"status": status.get("status", "pending"), "completed": status.get("completed_frames", 0), "total": status.get("total_frames", 0)}),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 4}


@mcp.tool()
def pipeline_list_images(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """List expected image frames and which ones exist on disk."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 4}
        result = image_batch.list_images(ws)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_list_images", {"total_ready": result["total_ready"], "total_expected": result["total_expected"]}),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e), "step": 4}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 4}


# ─── Step 4 (new): scene layouts and compositor ───────────────────────────────

@mcp.tool()
def pipeline_submit_scene_layouts(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scene_layout_json: Annotated[str, Field(description="JSON string matching the scene_layout schema: total_frames, canvas, frames array with layers.")],
) -> dict:
    """Save md/scene_layout.json from Claude-formed JSON. Replaces pipeline_submit_prompts for the compositor path."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 4}
        data = json.loads(scene_layout_json)
        result = layout_store.save_layout(ws, data)
        canvas = result.get("canvas") or {}
        schema_v = result.get("schema_version", "v1")
        frame_count = result.get("frame_count") or result.get("scene_count") or 0
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions(
                "pipeline_submit_scene_layouts",
                {"frame_count": frame_count, "canvas_width": canvas.get("width", 1920), "canvas_height": canvas.get("height", 1080), "schema_version": schema_v},
            ),
        }
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON in scene_layout_json: {e}", "step": 4}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 4}


@mcp.tool()
def pipeline_render_frames(
    channel: ChannelArg,
    scenario: ScenarioArg,
    frame_ids: Annotated[str, Field(description="Comma-separated frame IDs to render, e.g. '1,2,5'. Empty string renders all frames. Ignored for v2 (events-based) layouts.")] = "",
    wait: WaitArg = "false",
) -> dict:
    """Render frames from md/scene_layout.json. Routes to Remotion (v2 events schema) or Pillow compositor (v1 layers schema)."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 4}
        should_wait = _parse_wait(wait)

        schema_v = layout_store.get_schema_version(ws)
        if schema_v == "v2":
            # v2: route to Remotion — render all scenes
            raw = layout_store.load_layout_raw(ws)
            scenes = raw.get("scenes", [])
            result = remotion_jobs.start(ws, scenes, wait=should_wait)
            status = result.get("status", "running")
            if status == "complete":
                instr = get_instructions("pipeline_render_all_scenes_complete", {
                    "total": result.get("scenes_total", 0),
                })
            else:
                instr = get_instructions("pipeline_render_all_scenes_running", {
                    "total": result.get("scenes_total", 0),
                })
            return {"ok": True, "data": result, "schema_version": "v2", "instructions": instr}

        # v1: existing Pillow path
        engine = get_image_engine(_engine_cfg)
        parsed_ids: list[int] | None = None
        if frame_ids.strip():
            try:
                parsed_ids = [int(x.strip()) for x in frame_ids.split(",") if x.strip()]
            except ValueError:
                return {"ok": False, "error": "frame_ids must be comma-separated integers", "step": 4}
        result = render_jobs.start(ws, engine, frame_ids=parsed_ids, wait=should_wait)
        if result.get("status") == "complete":
            instr = get_instructions("pipeline_render_frames_complete", {"completed": result.get("completed_frames", 0), "total": result.get("total_frames", 0)})
            try:
                layout_obj = layout_store.load_layout(ws)
                for frame in layout_obj.frames:
                    if parsed_ids and frame.frame_id not in parsed_ids:
                        continue
                    for layer in frame.layers:
                        aid = getattr(layer, "asset_id", None) or getattr(layer, "asset_path", None) or ""
                        if aid and (aid.startswith("G-") or aid.startswith("P-")):
                            asset_lib.increment_asset_uses(aid, workspace=ws)
                        for comp in getattr(layer, "components", []):
                            caid = getattr(comp, "asset_id", "")
                            if caid:
                                asset_lib.increment_asset_uses(caid, workspace=ws)
            except Exception:
                pass
        else:
            instr = get_instructions("pipeline_render_frames_running", {"total": result.get("total_frames", 0)})
        if not _CAIROSVG_AVAILABLE:
            svg_warning = "cairosvg not installed — SVG layers rendered as grey placeholder. Install: pip install cairosvg"
            instr += f"\n\n⚠️ WARNING: {svg_warning}"
        else:
            svg_warning = None
        return {"ok": True, "data": result, "schema_version": "v1", "svg_warning": svg_warning, "instructions": instr}
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e), "step": 4}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 4}


@mcp.tool()
def pipeline_get_render_frames_status(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Return current frame render status from md/render_frames_status.json."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 4}
        status = render_jobs.read_status(ws)
        return {
            "ok": True,
            "data": status,
            "instructions": get_instructions(
                "pipeline_get_render_frames_status",
                {"status": status.get("status", "pending"), "completed": status.get("completed_frames", 0), "total": status.get("total_frames", 0)},
            ),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 4}


@mcp.tool()
def pipeline_list_frames(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """List expected frames from scene_layout.json and whether each PNG exists on disk."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 4}
        result = render_jobs.list_frames(ws)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_list_frames", {"total_ready": result["total_ready"], "total_expected": result["total_expected"]}),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e), "step": 4}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 4}


@mcp.tool()
def pipeline_preview_frame(
    channel: ChannelArg,
    scenario: ScenarioArg,
    frame_id: Annotated[str, Field(description="Frame ID to preview as a numeric string.")],
) -> dict:
    """Render a single frame synchronously and return its file path for inspection."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 4}
        engine = get_image_engine(_engine_cfg)
        result = render_jobs.preview_frame(ws, engine, int(frame_id))
        instr = get_instructions("pipeline_preview_frame", {"frame_id": frame_id, "path": result["path"]})
        if not _CAIROSVG_AVAILABLE:
            svg_warning = "cairosvg not installed — SVG layers rendered as grey placeholder. Install: pip install cairosvg"
            instr += f"\n\n⚠️ WARNING: {svg_warning}"
        else:
            svg_warning = None
        return {"ok": True, "data": result, "svg_warning": svg_warning, "instructions": instr}
    except (ValueError, FileNotFoundError) as e:
        return {"ok": False, "error": str(e), "step": 4}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 4}


@mcp.tool()
def pipeline_update_frame_layout(
    channel: ChannelArg,
    scenario: ScenarioArg,
    frame_id: Annotated[str, Field(description="Frame ID to update as a numeric string.")],
    layers_json: Annotated[str, Field(description="JSON array of layer objects to replace the frame's current layers.")],
) -> dict:
    """Update layers for a single frame in scene_layout.json without full resubmit."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 4}
        layers = json.loads(layers_json)
        if not isinstance(layers, list):
            return {"ok": False, "error": "layers_json must be a JSON array", "step": 4}
        result = layout_store.update_frame(ws, int(frame_id), layers)
        return {"ok": True, "data": result, "instructions": ""}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON in layers_json: {e}", "step": 4}
    except (ValueError, FileNotFoundError) as e:
        return {"ok": False, "error": str(e), "step": 4}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 4}


# ─── Step 4: asset library ────────────────────────────────────────────────────

@mcp.tool()
def pipeline_list_assets(
    channel: ChannelArg,
    scenario: ScenarioArg,
    category: Annotated[str, Field(description="Filter by category path, e.g. 'characters/crowd'. Empty returns all.")] = "",
    scope: Annotated[str, Field(description="'global' for shared assets, 'project' for scenario-specific, '' for both.")] = "",
) -> dict:
    """List available assets from global_assets/ and/or the project assets directory."""
    try:
        ws = _workspace(channel, scenario)
        result = asset_lib.list_assets(workspace=ws, scope=scope, category=category)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_list_assets", {"total": result["total"]}),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_search_assets(
    channel: ChannelArg,
    scenario: ScenarioArg,
    query: Annotated[str, Field(description="Search term matched against asset name and ID.")] = "",
    asset_type: Annotated[str, Field(description="Filter by type code: CHR, OBJ, BG, BUB, SND, MUS, SFX.")] = "",
    scope: Annotated[str, Field(description="'global', 'project', or '' for both.")] = "",
    role: Annotated[str, Field(description="Filter by role: BODY, FACE, EYES, CTX, PART, BASE, COMP, LORA, PROP.")] = "",
    semantic: Annotated[str, Field(description="Space or comma-separated semantic tags to match, e.g. 'money wealth'.")] = "",
    emotion: Annotated[str, Field(description="Emotion tag to match, e.g. 'tension' or 'fear'.")] = "",
    category: Annotated[str, Field(description="Filter by category path prefix.")] = "",
) -> dict:
    """Search assets by name, ID, type, role, or semantic/emotion tags."""
    try:
        ws = _workspace(channel, scenario)
        result = asset_lib.search_assets(
            workspace=ws, query=query, asset_type=asset_type, scope=scope,
            role=role, semantic=semantic, emotion=emotion, category=category,
        )
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_search_assets", {"total": result["total"]}),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_upload_asset(
    channel: ChannelArg,
    scenario: ScenarioArg,
    category: Annotated[str, Field(description="Asset category path, e.g. 'characters/crowd/body' or 'objects/money/context'.")],
    name: Annotated[str, Field(description="Asset file name without extension.")],
    svg_content: Annotated[str, Field(description="Full SVG source code. Use #PLACEHOLDER_COLOR for character skin color.")],
    scope: ScopeArg = "project",
    role: Annotated[str, Field(description="Asset role: BASE, BODY, FACE, EYES, CTX, PART, PROP, LORA. Default: CTX.")] = "CTX",
    compatible_groups: Annotated[str, Field(description="JSON array of compatible group IDs, e.g. '[\"G-OBJ-001\"]'.")] = "[]",
    description: Annotated[str, Field(description="Short description of this asset.")] = "",
    semantic_tags: Annotated[str, Field(description="JSON array of semantic tags, e.g. '[\"money\",\"wealth\"]'.")] = "[]",
    emotion_tags: Annotated[str, Field(description="JSON array of emotion tags, e.g. '[\"tension\",\"urgency\"]'.")] = "[]",
    visual_energy: Annotated[str, Field(description="Visual energy score 0.0-1.0 as string.")] = "0.5",
    attention_weight: Annotated[str, Field(description="Attention weight 0.0-1.0 as string.")] = "0.5",
) -> dict:
    """Upload an SVG asset. Auto-generates ID with role suffix (G-CHR-001-001-BODY). Enforces one BASE per group."""
    try:
        ws = _workspace(channel, scenario)
        cg = json.loads(compatible_groups) if compatible_groups else []
        st = json.loads(semantic_tags) if semantic_tags else []
        et = json.loads(emotion_tags) if emotion_tags else []
        result = asset_lib.upload_asset(
            workspace=ws, category=category, name=name, svg_content=svg_content,
            scope=scope, role=role, compatible_groups=cg, description=description,
            semantic_tags=st, emotion_tags=et,
            visual_energy=float(visual_energy), attention_weight=float(attention_weight),
        )
        # Register in group sheet
        import src.registry as _reg
        group_id = result.get("group_id", "")
        if group_id:
            from src.images.assets import _load_index, _assets_dir
            assets_root = _assets_dir(ws if scope == "project" else None, scope)
            idx = _load_index(assets_root, scope)
            group_map = idx.get("group_map", {})
            group_meta = group_map.get(group_id, {})
            _reg.ensure_group_sheet(group_id, group_meta)
            _reg.register_asset_in_group_sheet(group_id, {
                "id": result["id"],
                "role": role,
                "name": name,
                "path": result.get("path", ""),
                "description": description,
                "semantic_tags": st,
                "emotion_tags": et,
                "visual_energy": float(visual_energy),
                "attention_weight": float(attention_weight),
                "compatible_groups": cg,
                "global_uses": 0,
                "project_uses": 0,
                "projects_count": 0,
                "last_used": None,
                "created_from": None,
            })
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_upload_asset", {
                "category": category, "name": name,
                "id": result.get("id", ""), "role": role,
                "group_id": group_id,
            }),
        }
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_delete_asset(
    channel: ChannelArg,
    scenario: ScenarioArg,
    asset_id: Annotated[str, Field(description="Asset ID to delete, e.g. 'G-CHR-001-002' or 'P-OBJ-001-001'.")],
) -> dict:
    """Delete an asset by its ID. Scope (global/project) is inferred from the ID prefix."""
    try:
        ws = _workspace(channel, scenario)
        result = asset_lib.delete_asset(workspace=ws, asset_id=asset_id)
        return {"ok": True, "data": result, "instructions": ""}
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_generate_asset(
    channel: ChannelArg,
    scenario: ScenarioArg,
    prompt: Annotated[str, Field(description="Image generation prompt describing the asset.")],
    negative_prompt: Annotated[str, Field(description="Negative prompt. Default excludes realistic/photo styles.")] = "",
    save_as: Annotated[str, Field(description="Relative path within assets/ to save. Empty = return without saving.")] = "",
    scope: ScopeArg = "project",
) -> dict:
    """Generate an asset PNG via the active image engine and optionally trace to SVG with vtracer."""
    try:
        ws = _workspace(channel, scenario)
        engine = get_image_engine(_engine_cfg)
        result = asset_lib.generate_asset_svg(engine=engine, workspace=ws, prompt=prompt, negative_prompt=negative_prompt, save_as=save_as, scope=scope)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_generate_asset", {"png_path": result["png_path"], "svg_hint": result.get("svg_hint", "")}),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_get_asset_stats(
    channel: ChannelArg,
    scenario: ScenarioArg,
    asset_id: Annotated[str, Field(description="Asset ID, e.g. 'G-CHR-001-001-BODY'.")],
) -> dict:
    """Return file size, existence info, and usage counters for an asset ID."""
    try:
        ws = _workspace(channel, scenario)
        result = asset_lib.get_asset_stats(asset_id=asset_id, workspace=ws)
        instr = get_instructions("pipeline_get_asset_stats", {
            "asset_id": asset_id,
            "global_uses": result.get("global_uses", 0),
            "project_uses": result.get("project_uses", 0),
            "global_threshold": result.get("global_threshold", 10),
            "project_threshold": result.get("project_threshold", 5),
        })
        return {"ok": True, "data": result, "instructions": instr}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Step 4: engine profile management ───────────────────────────────────────

@mcp.tool()
def pipeline_list_engine_profiles(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """List all available image engine profiles and show which one is active."""
    try:
        profiles = engine_profiles.list_profiles(_engine_cfg)
        active_id = engine_profiles.get_active_profile_id(_engine_cfg)
        return {
            "ok": True,
            "data": {"profiles": profiles, "active_id": active_id, "total": len(profiles)},
            "instructions": get_instructions("pipeline_list_engine_profiles", {"total": len(profiles), "active_id": active_id}),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_switch_engine_profile(
    channel: ChannelArg,
    scenario: ScenarioArg,
    profile_id: Annotated[str, Field(description="Profile ID to activate, e.g. 'stub', 'sd15_deliberate', 'sdxl_base'.")],
) -> dict:
    """Switch the active image engine profile. Takes effect on the next render_frames call."""
    try:
        result = engine_profiles.switch_profile(_engines_yaml_path, profile_id, _engine_cfg)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_switch_engine_profile", result),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Step 4: character generation ────────────────────────────────────────────

@mcp.tool()
def pipeline_generate_character(
    channel: ChannelArg,
    scenario: ScenarioArg,
    name: Annotated[str, Field(description="Character name used as file stem, e.g. 'protagonist'.")],
    prompt: Annotated[str, Field(description="Description of the character's appearance.")],
    style: Annotated[str, Field(description="Visual style prefix, e.g. 'flat', 'cartoon', 'minimal'.")] = "flat",
    wait: WaitArg = "false",
) -> dict:
    """Generate a character PNG via the image engine and trace to SVG. Saves to global_assets/characters/main/."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 4}
        engine = get_image_engine(_engine_cfg)
        should_wait = _parse_wait(wait)
        result = character_jobs.start(ws, engine, name=name, prompt=prompt, style=style, wait=should_wait)
        if result.get("status") == "complete":
            instr = get_instructions("pipeline_generate_character_complete", {"name": name, "png_path": result.get("png_path", ""), "svg_path": result.get("svg_path", "")})
        else:
            instr = get_instructions("pipeline_generate_character_running", {"name": name})
        return {"ok": True, "data": result, "instructions": instr}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 4}


@mcp.tool()
def pipeline_get_character_status(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Return last character generation status from md/character_status.json."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 4}
        status = character_jobs.read_status(ws)
        instr = get_instructions("pipeline_get_character_status", {"status": status.get("status", "")})
        return {"ok": True, "data": status, "instructions": instr}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 4}


@mcp.tool()
def pipeline_list_characters(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """List all characters in global_assets/characters/main/."""
    try:
        chars = character_jobs.list_characters()
        instr = get_instructions("pipeline_list_characters", {"count": len(chars) if isinstance(chars, list) else 0})
        return {"ok": True, "data": chars, "instructions": instr}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Step 5: FFmpeg assembly ───────────────────────────────────────────────────

@mcp.tool()
def pipeline_assemble_scenes(
    channel: ChannelArg,
    scenario: ScenarioArg,
    wait: WaitArg = "false",
) -> dict:
    """Build one MP4 clip per scene (images + audio) into renders/scenes/. Reads timeline.json and image sources."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 5}
        should_wait = _parse_wait(wait)
        result = assembly_jobs.start_assemble(ws, wait=should_wait)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_assemble_scenes", {"scenes_done": result.get("scenes_done", 0), "scenes_total": result.get("scenes_total", 0)}),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e), "step": 5}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 5}


@mcp.tool()
def pipeline_concat_scenes(
    channel: ChannelArg,
    scenario: ScenarioArg,
    wait: WaitArg = "false",
) -> dict:
    """Concatenate renders/scenes/scene_*.mp4 into renders/<scenario>_draft.mp4."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 5}
        should_wait = _parse_wait(wait)
        result = assembly_jobs.start_concat(ws, wait=should_wait)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_concat_scenes", {"output_file": result.get("output_file", ""), "duration": result.get("duration", 0)}),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e), "step": 5}
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 5}


@mcp.tool()
def pipeline_get_render_status(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Return assembly and concat status from md/render_status.json."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 5}
        status = assembler.read_render_status(ws)
        return {
            "ok": True,
            "data": status,
            "instructions": get_instructions("pipeline_get_render_status", {"assemble_status": status.get("assemble_status", "pending"), "concat_status": status.get("concat_status", "pending"), "scenes_done": status.get("scenes_done", 0), "scenes_total": status.get("scenes_total", 0)}),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 5}


@mcp.tool()
def pipeline_get_output_file(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Return the path, size, and duration of the draft render file."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}.", "step": 5}
        result = assembler.get_output_file(ws)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_get_output_file", {"path": result["path"], "size_mb": result["size_mb"], "duration_sec": result["duration_sec"]}),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "step": 5}


# ─── Registry: global and project ─────────────────────────────────────────────

@mcp.tool()
def pipeline_get_global_registry(
    channel: ChannelArg,
    scenario: ScenarioArg,
    sheet: Annotated[str, Field(description="Sheet name to retrieve. Empty string returns the full registry.")] = "",
) -> dict:
    """Return the global registry (or a specific sheet). Contains cross-project performance, experiments, and asset stats."""
    try:
        data = reg.get_registry(workspace=None, scope="global", sheet=sheet)
        sheet_names = list(data.get("sheets", {}).keys()) if not sheet else [sheet]
        instr = get_instructions("pipeline_get_global_registry", {"sheet_names": sheet_names})
        return {"ok": True, "data": data, "instructions": instr}
    except KeyError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_get_project_registry(
    channel: ChannelArg,
    scenario: ScenarioArg,
    sheet: Annotated[str, Field(description="Sheet name to retrieve. Empty string returns the full project registry.")] = "",
) -> dict:
    """Return the project registry for this scenario (or a specific sheet). Contains scenes, hooks, emotion_map, insights."""
    try:
        ws = _workspace(channel, scenario)
        data = reg.get_registry(workspace=ws, scope="project", sheet=sheet)
        sheet_names = list(data.get("sheets", {}).keys()) if not sheet else [sheet]
        instr = get_instructions("pipeline_get_project_registry", {
            "scenario": scenario,
            "sheet_names": sheet_names,
        })
        return {"ok": True, "data": data, "instructions": instr}
    except KeyError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_add_registry_row(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scope: Annotated[str, Field(description="'global' or 'project'.")],
    sheet: SheetArg,
    row_data: Annotated[str, Field(description="JSON object matching the sheet columns.")],
) -> dict:
    """Append a row to a registry sheet."""
    try:
        ws = _workspace(channel, scenario) if scope == "project" else None
        row = json.loads(row_data)
        result = reg.add_registry_row(workspace=ws, scope=scope, sheet=sheet, row_data=row)
        instr = get_instructions("pipeline_add_registry_row", {
            "scope": scope, "sheet": sheet, "row_count": result.get("row_index", 0) + 1,
        })
        return {"ok": True, "data": result, "instructions": instr}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON in row_data: {e}"}
    except (KeyError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_update_registry(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scope: Annotated[str, Field(description="'global' or 'project'.")],
    sheet: SheetArg,
    row_id: Annotated[str, Field(description="Value of the first column (ID field) of the row to update.")],
    field: Annotated[str, Field(description="Column name to update.")],
    value: Annotated[str, Field(description="New value as a string.")],
) -> dict:
    """Update a single field in a registry row identified by its ID."""
    try:
        ws = _workspace(channel, scenario) if scope == "project" else None
        result = reg.update_registry_row(workspace=ws, scope=scope, sheet=sheet, row_id=row_id, field=field, value=value)
        instr = get_instructions("pipeline_update_registry", {
            "scope": scope, "sheet": sheet, "row_id": row_id, "field": field, "value": value,
        })
        return {"ok": True, "data": result, "instructions": instr}
    except (KeyError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_delete_registry_row(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scope: Annotated[str, Field(description="'global' or 'project'.")],
    sheet: SheetArg,
    row_id: Annotated[str, Field(description="ID value of the row to delete.")],
) -> dict:
    """Delete a row from a registry sheet by its ID."""
    try:
        ws = _workspace(channel, scenario) if scope == "project" else None
        result = reg.delete_registry_row(workspace=ws, scope=scope, sheet=sheet, row_id=row_id)
        return {"ok": True, "data": result, "instructions": ""}
    except (KeyError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_add_registry_column(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scope: Annotated[str, Field(description="'global' or 'project'.")],
    sheet: SheetArg,
    column_name: Annotated[str, Field(description="New column name to add.")],
    default_value: Annotated[str, Field(description="Default value for existing rows.")] = "",
) -> dict:
    """Add a new column to a registry sheet (dynamic schema — no server code change needed)."""
    try:
        ws = _workspace(channel, scenario) if scope == "project" else None
        result = reg.add_registry_column(workspace=ws, scope=scope, sheet=sheet, column_name=column_name, default_value=default_value)
        instr = get_instructions("pipeline_add_registry_column", {
            "column_name": column_name, "scope": scope, "sheet": sheet, "default_value": default_value,
        })
        return {"ok": True, "data": result, "instructions": instr}
    except (KeyError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_add_registry_sheet(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scope: Annotated[str, Field(description="'global' or 'project'.")],
    sheet_name: Annotated[str, Field(description="Name for the new sheet.")],
    columns: Annotated[str, Field(description="JSON array of column name strings.")],
) -> dict:
    """Add a new sheet to a registry (dynamic schema — supports any new analytics dimension)."""
    try:
        ws = _workspace(channel, scenario) if scope == "project" else None
        cols = json.loads(columns)
        if not isinstance(cols, list):
            return {"ok": False, "error": "columns must be a JSON array of strings"}
        result = reg.add_registry_sheet(workspace=ws, scope=scope, sheet_name=sheet_name, columns=cols)
        instr = get_instructions("pipeline_add_registry_sheet", {
            "sheet_name": sheet_name, "scope": scope, "columns": cols,
        })
        return {"ok": True, "data": result, "instructions": instr}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON in columns: {e}"}
    except (KeyError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_query_registry(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scope: Annotated[str, Field(description="'global' or 'project'.")],
    sheet: SheetArg,
    filter_field: Annotated[str, Field(description="Column name to filter on. Empty returns all rows.")] = "",
    filter_value: Annotated[str, Field(description="Value to match in filter_field.")] = "",
) -> dict:
    """Query a registry sheet with optional field-value filter."""
    try:
        ws = _workspace(channel, scenario) if scope == "project" else None
        result = reg.query_registry(workspace=ws, scope=scope, sheet=sheet, filter_field=filter_field, filter_value=filter_value)
        instr = get_instructions("pipeline_query_registry", {
            "scope": scope, "sheet": sheet, "row_count": result.get("total", 0),
        })
        return {"ok": True, "data": result, "instructions": instr}
    except (KeyError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_get_global_stats(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Return aggregated row counts across all global registry sheets."""
    try:
        stats = reg.get_global_stats()
        video_count = stats.get("sheets", {}).get("performance", {}).get("row_count", 0)
        instr = get_instructions("pipeline_get_global_stats", {"video_count": video_count})
        return {"ok": True, "data": stats, "instructions": instr}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_export_registry(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scope: Annotated[str, Field(description="'global' or 'project'.")],
    sheet: Annotated[str, Field(description="Sheet name to export. Empty exports the full registry.")] = "",
) -> dict:
    """Export a registry as clean JSON for external systems."""
    try:
        ws = _workspace(channel, scenario) if scope == "project" else None
        result = reg.export_registry(workspace=ws, scope=scope, sheet=sheet)
        return {"ok": True, "data": result, "instructions": ""}
    except (KeyError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Video structure and Hook Engine ──────────────────────────────────────────

@mcp.tool()
def pipeline_set_video_structure(
    channel: ChannelArg,
    scenario: ScenarioArg,
    structure_json: Annotated[str, Field(description="JSON object with hook_type, hook_duration, pattern, modules list, reset_points list, reward_type, audience_expectation_profile.")],
) -> dict:
    """Save the video's Hook Engine structure to the project registry."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        structure = json.loads(structure_json)
        result = reg.set_video_structure(ws, structure)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_set_video_structure", {"modules": result["modules"], "reset_points": result["reset_points"]}),
        }
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON in structure_json: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_get_video_structure(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Return the saved video structure (modules, reset_points, hook_type, reward_type)."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        structure = reg.get_video_structure(ws)
        instr = get_instructions("pipeline_get_video_structure", {
            "scenario": scenario,
            "module_count": len(structure.get("modules", [])),
            "reset_count": len(structure.get("reset_points", [])),
            "hook_type": structure.get("hook_type", ""),
            "reward_type": structure.get("reward_type", ""),
        })
        return {"ok": True, "data": structure, "instructions": instr}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_add_emotion_map(
    channel: ChannelArg,
    scenario: ScenarioArg,
    emotion_map_json: Annotated[str, Field(description="JSON array of emotion entries. Each entry: {time_start, time_end, emotion, module, intensity, visual_support, audio_support}.")],
) -> dict:
    """Append emotion timeline entries to the project registry emotion_map sheet."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        entries = json.loads(emotion_map_json)
        if not isinstance(entries, list):
            return {"ok": False, "error": "emotion_map_json must be a JSON array"}
        result = reg.add_emotion_map(ws, entries)
        instr = get_instructions("pipeline_add_emotion_map", {"entry_count": result.get("added", 0)})
        return {"ok": True, "data": result, "instructions": instr}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON in emotion_map_json: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Analytics and experiments ────────────────────────────────────────────────

@mcp.tool()
def pipeline_import_platform_stats(
    channel: ChannelArg,
    scenario: ScenarioArg,
    stats_json: Annotated[str, Field(description="JSON object mapping metric names to values, e.g. {avg_watch_time: 47.3, ctr: 0.082}.")],
    platform: Annotated[str, Field(description="Platform name, e.g. 'youtube', 'tiktok', 'instagram'.")],
) -> dict:
    """Import platform retention/performance data into the project registry performance sheet."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        stats = json.loads(stats_json)
        result = reg.import_platform_stats(ws, stats, platform)
        video_id = ws.name
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_import_platform_stats", {"video_id": video_id, "platform": platform}),
        }
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON in stats_json: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_create_experiment(
    channel: ChannelArg,
    scenario: ScenarioArg,
    experiment_id: Annotated[str, Field(description="Unique experiment identifier.")],
    scenario_a: Annotated[str, Field(description="First scenario being compared.")],
    scenario_b: Annotated[str, Field(description="Second scenario being compared.")],
    variable: Annotated[str, Field(description="The variable being tested, e.g. 'hook_type'.")],
    hypothesis: Annotated[str, Field(description="Expected outcome or hypothesis.")],
) -> dict:
    """Create an A/B experiment record in the global registry."""
    try:
        result = reg.create_experiment(experiment_id, scenario_a, scenario_b, variable, hypothesis)
        instr = get_instructions("pipeline_create_experiment", {
            "experiment_id": experiment_id, "variable": variable,
        })
        return {"ok": True, "data": result, "instructions": instr}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_update_experiment(
    channel: ChannelArg,
    scenario: ScenarioArg,
    experiment_id: Annotated[str, Field(description="Experiment ID to update.")],
    result: Annotated[str, Field(description="Observed result of the experiment.")],
    winner: Annotated[str, Field(description="Which scenario won.")],
    insight: Annotated[str, Field(description="Key learning from this experiment.")],
) -> dict:
    """Update an experiment with results and insights."""
    try:
        data = reg.update_experiment(experiment_id, result, winner, insight)
        instr = get_instructions("pipeline_update_experiment", {"winner": winner, "experiment_id": experiment_id})
        return {"ok": True, "data": data, "instructions": instr}
    except KeyError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_get_analytics(
    channel: ChannelArg,
    scenario: ScenarioArg,
    filter_hook_type: Annotated[str, Field(description="Filter by hook type.")] = "",
    filter_platform: Annotated[str, Field(description="Filter by platform name.")] = "",
    filter_reward_type: Annotated[str, Field(description="Filter by reward type.")] = "",
) -> dict:
    """Return aggregated analytics from the global registry: performance data and experiment results."""
    try:
        result = reg.get_analytics(filter_hook_type=filter_hook_type, filter_platform=filter_platform, filter_reward_type=filter_reward_type)
        video_count = len(result.get("videos", [])) if isinstance(result, dict) else 0
        instr = get_instructions("pipeline_get_analytics", {"video_count": video_count})
        return {"ok": True, "data": result, "instructions": instr}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_get_insights(
    channel: ChannelArg,
    scenario: ScenarioArg,
    min_evidence: Annotated[str, Field(description="Minimum evidence count as a numeric string. Default '2'.")] = "2",
) -> dict:
    """Return insights from the project and global registry with sufficient supporting evidence."""
    try:
        ws = _workspace(channel, scenario)
        insights = reg.get_insights(workspace=ws if ws.exists() else None, min_evidence=int(min_evidence))
        instr = get_instructions("pipeline_get_insights", {"insight_count": len(insights), "min_evidence": int(min_evidence)})
        return {"ok": True, "data": {"insights": insights, "total": len(insights)}, "instructions": instr}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_compare_videos(
    channel: ChannelArg,
    scenario: ScenarioArg,
    video_id_a: Annotated[str, Field(description="First video ID to compare.")],
    video_id_b: Annotated[str, Field(description="Second video ID to compare.")],
) -> dict:
    """Compare performance data for two videos side by side from the global registry."""
    try:
        result = reg.compare_videos(video_id_a, video_id_b)
        retention_delta = result.get("retention_delta", 0) if isinstance(result, dict) else 0
        instr = get_instructions("pipeline_compare_videos", {"video_id_a": video_id_a, "video_id_b": video_id_b, "retention_delta": retention_delta})
        return {"ok": True, "data": result, "instructions": instr}
    except Exception as e:
        return {"ok": False, "error": str(e)}



# ─── Audio import tools ────────────────────────────────────────────────────────

from src.audio.audio_import import search_free_audio as _search_audio, save_free_audio as _save_audio

@mcp.tool()
def pipeline_search_free_audio(
    channel: ChannelArg,
    scenario: ScenarioArg,
    category: Annotated[str, Field(description="'music' or 'effects'.")],
    mood: Annotated[str, Field(description="Mood filter: tension, happy, neutral, dramatic, upbeat.")] = "",
    duration_max: Annotated[str, Field(description="Maximum duration in seconds as string. '0' = no limit.")] = "0",
    source: Annotated[str, Field(description="Source: freesound, pixabay, or jamendo.")] = "freesound",
) -> dict:
    """Search free audio from external sources. Returns results with import_ids for pipeline_save_free_audio."""
    try:
        result = _search_audio(
            category=category,
            mood=mood,
            duration_max=int(duration_max),
            source=source,
        )
        if not result.get("ok", True):
            return {"ok": False, "error": result.get("error", "Search failed")}
        total = result.get("total", 0)
        first_import_id = result.get("results", [{}])[0].get("import_id", "") if result.get("results") else ""
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_search_free_audio", {
                "result_count": total,
                "source": source,
                "license_type": "CC/free",
                "import_id": first_import_id,
            }),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_save_free_audio(
    channel: ChannelArg,
    scenario: ScenarioArg,
    import_id: Annotated[str, Field(description="import_id from pipeline_search_free_audio result.")],
    group: Annotated[str, Field(description="Group name for saving, e.g. 'tension' or 'notification'.")],
    mood: Annotated[str, Field(description="Mood label for this track, e.g. 'tension'.")],
    scope: ScopeArg = "global",
) -> dict:
    """Download and register a free audio track found via pipeline_search_free_audio."""
    try:
        ws = _workspace(channel, scenario) if scope == "project" else None
        result = _save_audio(import_id=import_id, group=group, mood=mood, scope=scope,
                             channel=channel, scenario=scenario, workspace=ws)
        if not result.get("ok", True):
            return {"ok": False, "error": result.get("error", "Save failed")}
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_save_free_audio", {
                "asset_id": result.get("asset_id", ""),
                "path": result.get("path", ""),
            }),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Updated asset tools ───────────────────────────────────────────────────────

# NOTE: pipeline_upload_asset, pipeline_list_assets, pipeline_search_assets are defined above.
# They are overridden here with extended signatures.
# Unregister old and re-register with new params is not straightforward with FastMCP.
# Instead, the new params are added in-place by updating the functions directly in server.py.
# (The functions above already call asset_lib which now has the extended signatures.)


# ─── Competitor Intelligence tools ────────────────────────────────────────────

from src.competitor import manager as _competitor

@mcp.tool()
def pipeline_add_competitor_channel(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Unique competitor channel identifier, e.g. 'alex_hormozi'.")],
    channel_data_json: Annotated[str, Field(description="JSON object with channel_name, platform, niche, avg_views, etc.")],
) -> dict:
    """Add a competitor channel to the intelligence system."""
    try:
        data = json.loads(channel_data_json)
        result = _competitor.add_competitor_channel(channel_id, data)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_add_competitor_channel", {"channel_id": channel_id}),
        }
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_update_competitor_channel(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Competitor channel identifier.")],
    field: Annotated[str, Field(description="Field to update. Supports dot notation: 'hook_patterns'.")],
    value: Annotated[str, Field(description="New value as JSON string.")],
) -> dict:
    """Update a field in a competitor channel record."""
    try:
        import ast
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = value
        result = _competitor.update_competitor_channel(channel_id, field, parsed)
        return {"ok": True, "data": result, "instructions": ""}
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_get_competitor_channel(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Competitor channel identifier.")],
) -> dict:
    """Return competitor channel data."""
    try:
        return {"ok": True, "data": _competitor.get_competitor_channel(channel_id), "instructions": ""}
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_list_competitor_channels(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """List all competitor channels in the intelligence system."""
    try:
        return {"ok": True, "data": _competitor.list_competitor_channels(), "instructions": ""}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_add_competitor_video(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Competitor channel identifier.")],
    video_id: Annotated[str, Field(description="Unique video identifier, e.g. YouTube video ID.")],
    video_data_json: Annotated[str, Field(description="JSON object with title, platform, raw_metrics, etc.")],
) -> dict:
    """Add a competitor video. Server auto-computes engagement metrics from raw_metrics."""
    try:
        data = json.loads(video_data_json)
        result = _competitor.add_competitor_video(channel_id, video_id, data)
        return {"ok": True, "data": result, "instructions": ""}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_update_competitor_video(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Competitor channel identifier.")],
    video_id: Annotated[str, Field(description="Video identifier.")],
    field: Annotated[str, Field(description="Field path. Supports dot notation: 'structure.hook_type'.")],
    value: Annotated[str, Field(description="New value as JSON string.")],
) -> dict:
    """Update a field in a competitor video record. Supports dot notation for nested fields."""
    try:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = value
        result = _competitor.update_competitor_video(channel_id, video_id, field, parsed)
        return {"ok": True, "data": result, "instructions": ""}
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_get_competitor_video(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Competitor channel identifier.")],
    video_id: Annotated[str, Field(description="Video identifier.")],
) -> dict:
    """Return full competitor video data including computed metrics."""
    try:
        return {"ok": True, "data": _competitor.get_competitor_video(channel_id, video_id), "instructions": ""}
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_list_competitor_videos(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Competitor channel identifier.")],
) -> dict:
    """List all videos for a competitor channel."""
    try:
        return {"ok": True, "data": _competitor.list_competitor_videos(channel_id), "instructions": ""}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_import_transcript(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Competitor channel identifier.")],
    video_id: Annotated[str, Field(description="Video identifier.")],
    transcript_json: Annotated[str, Field(description="JSON object with source and segments array. Each segment: {start, end, text}.")],
) -> dict:
    """Import a transcript for a competitor video from Tactiq, YouTube, or other sources."""
    try:
        data = json.loads(transcript_json)
        result = _competitor.import_transcript(channel_id, video_id, data)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_import_transcript", {
                "segment_count": result["segment_count"],
                "duration": result["duration"],
            }),
        }
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_get_competitor_index(
    channel: ChannelArg,
    scenario: ScenarioArg,
    sheet: Annotated[str, Field(description="Sheet name (hooks, thumbnails, pacing, patterns, platform_models). Empty = full index.")] = "",
) -> dict:
    """Return the global competitor intelligence index or a specific sheet."""
    try:
        data = _competitor.get_competitor_index(sheet)
        channel_count = data.get("total_channels", 0)
        video_count = data.get("total_videos", 0)
        return {
            "ok": True,
            "data": data,
            "instructions": get_instructions("pipeline_get_competitor_index", {
                "channel_count": channel_count,
                "video_count": video_count,
            }),
        }
    except KeyError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_query_competitor_data(
    channel: ChannelArg,
    scenario: ScenarioArg,
    sheet: Annotated[str, Field(description="Sheet name to query: hooks, thumbnails, pacing, patterns, platform_models.")],
    filter_field: Annotated[str, Field(description="Field name to filter on.")] = "",
    filter_value: Annotated[str, Field(description="Value to match.")] = "",
    min_value: Annotated[str, Field(description="Minimum numeric value for filter_field.")] = "",
    max_value: Annotated[str, Field(description="Maximum numeric value for filter_field.")] = "",
) -> dict:
    """Query the competitor intelligence index with optional filters."""
    try:
        result = _competitor.query_competitor_data(sheet, filter_field, filter_value, min_value, max_value)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_query_competitor_data", {
                "sheet": sheet,
                "row_count": result["total"],
            }),
        }
    except KeyError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Channel config and skills tools ──────────────────────────────────────────

from src.channel import manager as _channel_mgr

@mcp.tool()
def pipeline_save_channel_config(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Channel identifier, used as directory name under channels/.")],
    config_json: Annotated[str, Field(description="JSON object with channel_name, niche, narrative_style, visual_style, frame_rules, audio_style, prompt_style.")],
) -> dict:
    """Save channel_config.json — the DNA file for all videos on this channel."""
    try:
        data = json.loads(config_json)
        result = _channel_mgr.save_channel_config(channel_id, data)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_save_channel_config", {"channel_id": channel_id}),
        }
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_get_channel_config(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Channel identifier.")],
) -> dict:
    """Return channel_config.json for the given channel_id."""
    try:
        data = _channel_mgr.get_channel_config(channel_id)
        channel_name = data.get("channel_name", channel_id)
        return {
            "ok": True,
            "data": data,
            "instructions": get_instructions("pipeline_get_channel_config", {
                "channel_name": channel_name,
                "channel_id": channel_id,
            }),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_update_channel_config(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Channel identifier.")],
    field: Annotated[str, Field(description="Field path. Supports dot notation: 'narrative_style.tone'.")],
    value: Annotated[str, Field(description="New value as JSON string.")],
) -> dict:
    """Update a field in channel_config.json. Supports dot notation for nested fields."""
    try:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = value
        result = _channel_mgr.update_channel_config(channel_id, field, parsed)
        return {"ok": True, "data": result, "instructions": ""}
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_list_channels(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """List all channels with their config summaries."""
    try:
        return {"ok": True, "data": _channel_mgr.list_channels(), "instructions": ""}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_create_channel_skills(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Channel identifier.")],
) -> dict:
    """Create skill template files for a channel. Claude fills them via pipeline_update_channel_skill."""
    try:
        result = _channel_mgr.create_channel_skills(channel_id)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_create_channel_skills", {"channel_id": channel_id}),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_update_channel_skill(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Channel identifier.")],
    skill_name: Annotated[str, Field(description="Skill name: SCENARIO_WRITER, IMAGE_PROMPTS, FRAME_RULES, HOOK_ENGINE, or CHANNEL_VOICE.")],
    content: Annotated[str, Field(description="Full markdown content for the skill file.")],
) -> dict:
    """Write or update a channel skill file with new content."""
    try:
        result = _channel_mgr.update_channel_skill(channel_id, skill_name, content)
        return {"ok": True, "data": result, "instructions": ""}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_get_channel_skill(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Channel identifier.")],
    skill_name: Annotated[str, Field(description="Skill name: SCENARIO_WRITER, IMAGE_PROMPTS, FRAME_RULES, HOOK_ENGINE, or CHANNEL_VOICE.")],
) -> dict:
    """Return the full content of a channel skill file."""
    try:
        result = _channel_mgr.get_channel_skill(channel_id, skill_name)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_get_channel_skill", {
                "skill_name": skill_name,
                "channel_id": channel_id,
            }),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_list_channel_skills(
    channel: ChannelArg,
    scenario: ScenarioArg,
    channel_id: Annotated[str, Field(description="Channel identifier.")],
) -> dict:
    """List all skill files for a channel with last-updated timestamps."""
    try:
        return {"ok": True, "data": _channel_mgr.list_channel_skills(channel_id), "instructions": ""}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Extended asset tools (role, semantic, overuse) ────────────────────────────
# The functions below replace the existing pipeline_upload_asset / pipeline_list_assets /
# pipeline_search_assets. FastMCP registers by function name so these replace the earlier ones.

# ─── Remotion render tools (v2 events-based layout) ──────────────────────────

@mcp.tool()
def pipeline_render_scene(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scene_id: Annotated[int, Field(description="Scene ID to render (matches scene_id in scene_layout.json).")],
    wait: WaitArg = "false",
) -> dict:
    """Render a single scene MP4 via Remotion. Requires a v2 (events-based) scene_layout.json."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        raw = layout_store.load_layout_raw(ws)
        if raw.get("_schema_version") != "v2":
            return {"ok": False, "error": "pipeline_render_scene requires a v2 layout. Submit events-based scene_layout first."}
        scenes = raw.get("scenes", [])
        scene = next((s for s in scenes if s["scene_id"] == scene_id), None)
        if scene is None:
            return {"ok": False, "error": f"Scene {scene_id} not found in scene_layout.json."}
        should_wait = _parse_wait(wait)
        result = remotion_jobs.start(ws, [scene], wait=should_wait)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_render_scene", {"scene_id": scene_id}),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_render_all_scenes(
    channel: ChannelArg,
    scenario: ScenarioArg,
    wait: WaitArg = "false",
) -> dict:
    """Render all scenes in the v2 layout as individual MP4 files via Remotion."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        raw = layout_store.load_layout_raw(ws)
        if raw.get("_schema_version") != "v2":
            return {"ok": False, "error": "pipeline_render_all_scenes requires a v2 layout."}
        scenes = raw.get("scenes", [])
        should_wait = _parse_wait(wait)
        result = remotion_jobs.start(ws, scenes, wait=should_wait)
        status = result.get("status", "running")
        if status == "complete":
            instr = get_instructions("pipeline_render_all_scenes_complete", {"total": result.get("scenes_total", 0)})
        else:
            instr = get_instructions("pipeline_render_all_scenes_running", {"total": result.get("scenes_total", 0)})
        return {"ok": True, "data": result, "instructions": instr}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_get_remotion_status(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Return per-scene Remotion render progress from md/remotion_status.json."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        return {"ok": True, "data": remotion_jobs.read_status(ws), "instructions": ""}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_stop_render(channel: ChannelArg, scenario: ScenarioArg) -> dict:
    """Cancel the active Remotion render job for this workspace."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        status_before = remotion_jobs.read_status(ws)
        stop_result = remotion_jobs.stop(ws)
        return {
            "ok": True,
            "data": {
                **stop_result,
                "scenes_completed_before_stop": status_before.get("scenes_done", 0),
                "scenes_cancelled": status_before.get("scenes_total", 0) - status_before.get("scenes_done", 0),
            },
            "instructions": "",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_update_scene_event(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scene_id: Annotated[int, Field(description="Scene ID containing the event.")],
    event_index: Annotated[int, Field(description="Zero-based index of the event in the events array.")],
    field: Annotated[str, Field(description="Field to update, e.g. 'time', 'state.emotion', 'position.x', 'value'.")],
    value: Annotated[str, Field(description="New value as a string. Numeric types will be preserved by the layout.")],
) -> dict:
    """Modify a single field in a v2 scene event without resubmitting the full layout."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        result = layout_store.update_scene_event(ws, scene_id, event_index, field, value)
        return {
            "ok": True,
            "data": result,
            "instructions": get_instructions("pipeline_update_scene_event", {
                "scene_id": scene_id,
                "event_time": result.get("new_value") if field == "time" else None,
            }),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_move_event(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scene_id: Annotated[int, Field(description="Scene ID containing the event.")],
    event_index: Annotated[int, Field(description="Zero-based index of the event to move.")],
    new_time: Annotated[float, Field(description="New time in seconds from scene start.")],
) -> dict:
    """Shift an event to a new time and re-sort the events array. Re-render the scene to see the change."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        result = layout_store.move_event(ws, scene_id, event_index, new_time)
        return {"ok": True, "data": result, "instructions": f"Event moved. Re-render: pipeline_render_scene(scene_id={scene_id})"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_preview_scene_event(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scene_id: Annotated[int, Field(description="Scene ID to preview.")],
    time: Annotated[float, Field(description="Time in seconds from scene start to preview.")],
) -> dict:
    """Render a single PNG frame at the given time offset for spot-checking layout without full render."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        raw = layout_store.load_layout_raw(ws)
        if raw.get("_schema_version") != "v2":
            return {"ok": False, "error": "pipeline_preview_scene_event requires a v2 layout."}
        preview_dir = ws / "renders" / "previews"
        preview_dir.mkdir(parents=True, exist_ok=True)
        preview_path = preview_dir / f"scene_{scene_id:03d}_t{time:.1f}.png"
        return {
            "ok": True,
            "data": {
                "preview_path": str(preview_path.relative_to(ws)),
                "time": time,
                "note": "Full renderStill not yet available. Run pipeline_render_scene for MP4 preview.",
            },
            "instructions": "",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def pipeline_list_scene_events(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scene_id: Annotated[int, Field(description="Scene ID to inspect.")],
) -> dict:
    """List all events for a scene from md/scene_layout.json (v2 layout)."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        raw = layout_store.load_layout_raw(ws)
        if raw.get("_schema_version") != "v2":
            return {"ok": False, "error": "pipeline_list_scene_events requires a v2 layout."}
        scenes = raw.get("scenes", [])
        scene = next((s for s in scenes if s["scene_id"] == scene_id), None)
        if scene is None:
            return {"ok": False, "error": f"Scene {scene_id} not found."}
        events = scene.get("events", [])
        indexed = [{"index": i, **e} for i, e in enumerate(events)]
        return {
            "ok": True,
            "data": {
                "scene_id": scene_id,
                "duration": scene.get("duration"),
                "chapter": scene.get("chapter", ""),
                "events": indexed,
                "total_events": len(events),
            },
            "instructions": "",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── DaVinci export ───────────────────────────────────────────────────────────

@mcp.tool()
def pipeline_export_davinci(
    channel: ChannelArg,
    scenario: ScenarioArg,
    format: Annotated[str, Field(description="Export format. 'fcpxml' (default) produces FCPXML 1.10 for DaVinci Resolve 18+.")] = "fcpxml",
) -> dict:
    """Export a DaVinci Resolve FCPXML timeline from Remotion-rendered scene MP4s."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        timeline_path = ws / "md" / "timeline.json"
        if not timeline_path.exists():
            return {"ok": False, "error": "timeline.json not found. Run pipeline_build_timeline first."}
        timeline_data = json.loads(timeline_path.read_text())
        scenes = timeline_data.get("scenes", timeline_data.get("scene_timings", []))
        if not scenes:
            return {"ok": False, "error": "No scenes found in timeline.json."}
        if format != "fcpxml":
            return {"ok": False, "error": f"Unsupported format '{format}'. Only 'fcpxml' is implemented."}
        project_name = f"{channel}_{scenario}"
        out_path = ws / "renders" / f"{project_name}_davinci.fcpxml"
        davinci_exporter.export_fcpxml(scenes, out_path, project_name=project_name)
        total_dur = sum(float(s.get("duration", 0)) for s in scenes)
        return {
            "ok": True,
            "data": {
                "export_path": str(out_path.relative_to(ws)),
                "scenes_included": len(scenes),
                "total_duration": round(total_dur, 3),
                "format": "fcpxml",
                "davinci_instructions": "File → Import → Timeline → select .fcpxml",
            },
            "instructions": get_instructions("pipeline_export_davinci", {
                "export_path": str(out_path.relative_to(ws)),
                "scenes_included": len(scenes),
                "total_duration": round(total_dur, 3),
            }),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Lip sync ─────────────────────────────────────────────────────────────────

@mcp.tool()
def pipeline_generate_lipsync(
    channel: ChannelArg,
    scenario: ScenarioArg,
    scene_id: Annotated[int, Field(description="Scene ID whose audio file should be analysed for lip sync.")],
) -> dict:
    """Run rhubarb-lip-sync on a scene audio file to produce mouth-cue timings in md/lipsync_scene_NNN.json."""
    try:
        ws = _workspace(channel, scenario)
        if not ws.exists():
            return {"ok": False, "error": f"Workspace not found: {channel}/{scenario}."}
        audio_path = ws / "audio" / f"scene_{scene_id:03d}.mp3"
        if not audio_path.exists():
            audio_path = ws / "audio" / f"scene_{scene_id}.mp3"
        if not audio_path.exists():
            return {"ok": False, "error": f"Audio file not found for scene {scene_id}. Run pipeline_start_voiceover first."}
        out_path = ws / "md" / f"lipsync_scene_{scene_id:03d}.json"
        cues = lipsync_mod.generate_lipsync(audio_path, out_path)
        return {
            "ok": True,
            "data": {
                "scene_id": scene_id,
                "phoneme_count": len(cues),
                "lipsync_path": str(out_path.relative_to(ws)),
                "duration": cues[-1]["end"] if cues else 0,
            },
            "instructions": (
                f"Lip sync data ready. Add character with lipsync=true in scene events. "
                f"Mouth cues: {len(cues)}. File: md/lipsync_scene_{scene_id:03d}.json"
            ),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e) + " — install rhubarb from https://github.com/DanielSWolf/rhubarb-lip-sync/releases"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


_tool_names = list(mcp._tool_manager._tools.keys())
_log.info("Registered %d tools: %s", len(_tool_names), ", ".join(_tool_names))
