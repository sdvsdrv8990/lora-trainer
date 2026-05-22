"""Preflight checks before running LoRA training."""

from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path


class ValidationError(RuntimeError):
    """Raised when the local machine is not ready for training."""


class EnvironmentValidator:
    """Validate Python, ROCm, sd-scripts, and dataset preconditions."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def validate(self, images_dir: Path) -> list[str]:
        warnings: list[str] = []

        if platform.system() != "Linux":
            raise ValidationError("Linux is required for ROCm LoRA training.")

        if sys.version_info[:2] != (3, 10):
            raise ValidationError("Python 3.10 is required for ROCm PyTorch wheels.")

        if not images_dir.is_dir():
            raise ValidationError(f"Images directory does not exist: {images_dir}")

        if shutil.which("rocm-smi") is None:
            warnings.append("rocm-smi not found. Training may still work if ROCm is installed.")

        train_script = self.project_root / "sd-scripts" / "sdxl_train_network.py"
        if not train_script.exists():
            raise ValidationError("sd-scripts is missing. Run ./install.sh first.")

        try:
            import torch
        except ImportError as exc:
            raise ValidationError("PyTorch is missing. Run ./install.sh first.") from exc

        if not getattr(torch.version, "hip", None):
            raise ValidationError("Installed PyTorch is not a ROCm/HIP build.")

        return warnings
