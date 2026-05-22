"""Command assembly and execution for kohya-ss sd-scripts LoRA training."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from src.dataset import DatasetPreparer
from src.rocm_utils import AmdGpuFamily, build_rocm_environment


class TrainingConfig(BaseModel):
    """Validated training configuration."""

    base_model: str = "stabilityai/stable-diffusion-xl-base-1.0"
    output_dir: Path = Path("./output")
    output_name: str = "my_lora"
    trigger_word: str = "stickman_style"
    epochs: int = Field(default=20, ge=1)
    rank: int = Field(default=32, ge=16, le=64)
    repeats: int = Field(default=10, ge=1)
    resolution: int = Field(default=1024, ge=512)
    train_batch_size: int = Field(default=1, ge=1)
    learning_rate: float = Field(default=0.0001, gt=0)
    network_alpha: int = Field(default=16, ge=1)
    mixed_precision: str = "fp16"
    save_precision: str = "fp16"
    optimizer_type: str = "AdamW"
    cache_latents: bool = True
    gradient_checkpointing: bool = True
    shuffle_caption: bool = True
    caption_extension: str = ".txt"
    gpu: str = "auto"

    @field_validator("gpu")
    @classmethod
    def validate_gpu(cls, value: str) -> str:
        AmdGpuFamily(value)
        return value

    @field_validator("optimizer_type")
    @classmethod
    def reject_amd_unsafe_optimizers(cls, value: str) -> str:
        if value.lower() in {"adamw8bit", "paged_adamw_8bit"}:
            raise ValueError("AdamW8bit is unstable on AMD/ROCm. Use AdamW.")
        return value


def load_default_config(config_path: Path) -> TrainingConfig:
    data: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return TrainingConfig(**data)


class LoraTrainer:
    """Prepare data and run sd-scripts with ROCm-safe defaults."""

    def __init__(self, project_root: Path, config: TrainingConfig) -> None:
        self.project_root = project_root
        self.config = config

    def prepare_dataset(self, images_dir: Path) -> Path:
        preparer = DatasetPreparer(
            source_dir=images_dir,
            work_dir=self.project_root / ".work",
            trigger_word=self.config.trigger_word,
            repeats=self.config.repeats,
        )
        return preparer.prepare()

    def build_command(self, train_data_dir: Path) -> list[str]:
        output_dir = self.config.output_dir
        if not output_dir.is_absolute():
            output_dir = self.project_root / output_dir

        command = [
            sys.executable,
            str(self.project_root / "sd-scripts" / "sdxl_train_network.py"),
            "--pretrained_model_name_or_path",
            self.config.base_model,
            "--train_data_dir",
            str(train_data_dir),
            "--output_dir",
            str(output_dir),
            "--output_name",
            self.config.output_name,
            "--network_module",
            "networks.lora",
            "--network_dim",
            str(self.config.rank),
            "--network_alpha",
            str(self.config.network_alpha),
            "--resolution",
            str(self.config.resolution),
            "--train_batch_size",
            str(self.config.train_batch_size),
            "--max_train_epochs",
            str(self.config.epochs),
            "--learning_rate",
            str(self.config.learning_rate),
            "--optimizer_type",
            self.config.optimizer_type,
            "--mixed_precision",
            self.config.mixed_precision,
            "--save_precision",
            self.config.save_precision,
            "--caption_extension",
            self.config.caption_extension,
            "--save_model_as",
            "safetensors",
        ]

        if self.config.cache_latents:
            command.append("--cache_latents")
        if self.config.gradient_checkpointing:
            command.append("--gradient_checkpointing")
        if self.config.shuffle_caption:
            command.append("--shuffle_caption")

        return command

    def run(self, images_dir: Path, dry_run: bool = False) -> list[str]:
        dataset_dir = self.prepare_dataset(images_dir)
        command = self.build_command(dataset_dir)
        if dry_run:
            return command

        env = build_rocm_environment(self.config.gpu)
        output_dir = self.config.output_dir
        if not output_dir.is_absolute():
            output_dir = self.project_root / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(command, cwd=self.project_root / "sd-scripts", env=env, check=True)
        return command
