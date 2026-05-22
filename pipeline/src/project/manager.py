import shutil
from pathlib import Path
from src.entities.project import ProjectConfig, WorkspaceContext


def resolve_workspace(
    config: ProjectConfig,
    base_dir: Path,
    subdirs: list[str],
) -> WorkspaceContext:
    """
    Implements Cases 1-3 from PRODUCTION_PIPELINE.md Step 0.
    Case 4 (missing data) is handled upstream by the caller before calling this.
    """
    channel_dir = base_dir / config.channel
    scenario_dir = channel_dir / config.scenario
    existed = scenario_dir.exists()

    if not existed:
        for subdir in subdirs:
            (scenario_dir / subdir).mkdir(parents=True, exist_ok=True)

    return WorkspaceContext(
        channel=config.channel,
        scenario=config.scenario,
        workspace=scenario_dir,
        existed=existed,
    )


def delete_workspace(
    config: ProjectConfig,
    base_dir: Path,
) -> dict:
    """
    Delete a scenario directory and its contents.
    Also removes the channel directory if it becomes empty.
    Returns a dict describing what was deleted.
    """
    channel_dir = (base_dir / config.channel).resolve()
    scenario_dir = (channel_dir / config.scenario).resolve()

    # Safety: target must be inside base_dir
    if not str(scenario_dir).startswith(str(base_dir.resolve())):
        raise ValueError("Path traversal not allowed")

    if not scenario_dir.exists():
        raise FileNotFoundError(f"Scenario not found: {config.channel}/{config.scenario}")

    shutil.rmtree(scenario_dir)

    deleted_channel = False
    if channel_dir.exists() and not any(channel_dir.iterdir()):
        channel_dir.rmdir()
        deleted_channel = True

    return {
        "deleted_scenario": str(scenario_dir),
        "deleted_channel": str(channel_dir) if deleted_channel else None,
    }
