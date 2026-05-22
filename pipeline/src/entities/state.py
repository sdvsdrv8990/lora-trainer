from pydantic import BaseModel, field_serializer
from datetime import datetime
from enum import Enum


class StepStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    complete = "complete"
    failed = "failed"


class PipelineState(BaseModel):
    channel: str
    scenario: str
    current_step: int = 0
    step_status: StepStatus = StepStatus.pending
    last_updated: datetime = datetime.now()
    errors: list[str] = []

    @field_serializer("last_updated")
    def serialize_dt(self, dt: datetime) -> str:
        return dt.isoformat()
