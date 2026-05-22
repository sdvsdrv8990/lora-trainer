import json
from pathlib import Path
from datetime import datetime
from src.entities.state import PipelineState, StepStatus


def load(workspace: Path) -> PipelineState:
    state_file = workspace / "state.json"
    if not state_file.exists():
        raise FileNotFoundError(f"state.json not found in {workspace}")
    return PipelineState.model_validate_json(state_file.read_text())


def save(workspace: Path, state: PipelineState) -> None:
    state_file = workspace / "state.json"
    state_file.write_text(state.model_dump_json(indent=2))


def init(workspace: Path, channel: str, scenario: str) -> PipelineState:
    state = PipelineState(channel=channel, scenario=scenario)
    save(workspace, state)
    return state


def set_step(workspace: Path, step: int, status: StepStatus) -> PipelineState:
    state = load(workspace)
    updated = state.model_copy(
        update={
            "current_step": step,
            "step_status": status,
            "last_updated": datetime.now(),
        }
    )
    save(workspace, updated)
    return updated
