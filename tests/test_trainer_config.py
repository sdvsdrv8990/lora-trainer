import pytest
from pydantic import ValidationError

from src.trainer import TrainingConfig


def test_rejects_adamw8bit_on_amd() -> None:
    with pytest.raises(ValidationError):
        TrainingConfig(optimizer_type="AdamW8bit")


def test_rank_must_stay_inside_rocm_safe_bounds() -> None:
    with pytest.raises(ValidationError):
        TrainingConfig(rank=128)
