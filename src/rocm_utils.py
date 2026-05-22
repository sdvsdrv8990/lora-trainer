"""AMD/ROCm-specific helpers."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from enum import Enum


class AmdGpuFamily(str, Enum):
    """Supported AMD GPU architecture families for ROCm override."""

    AUTO = "auto"
    RDNA2 = "rdna2"
    RDNA3 = "rdna3"


HSA_OVERRIDE_BY_FAMILY: dict[AmdGpuFamily, str] = {
    AmdGpuFamily.RDNA2: "10.3.0",
    AmdGpuFamily.RDNA3: "11.0.0",
}


def detect_gpu_family() -> AmdGpuFamily:
    """Best-effort AMD GPU family detection using rocm-smi output."""

    if shutil.which("rocm-smi") is None:
        return AmdGpuFamily.RDNA2

    try:
        result = subprocess.run(
            ["rocm-smi", "--showproductname"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return AmdGpuFamily.RDNA2

    output = result.stdout.lower()
    if re.search(r"rx\s*7|7900|7800|7700|7600", output):
        return AmdGpuFamily.RDNA3
    if re.search(r"rx\s*6|6950|6900|6800|6700|6600|6500|6400", output):
        return AmdGpuFamily.RDNA2
    return AmdGpuFamily.RDNA2


def build_rocm_environment(gpu: str) -> dict[str, str]:
    """Return environment variables required for AMD ROCm training."""

    family = AmdGpuFamily(gpu)
    if family == AmdGpuFamily.AUTO:
        family = detect_gpu_family()

    env = os.environ.copy()
    env["HSA_OVERRIDE_GFX_VERSION"] = HSA_OVERRIDE_BY_FAMILY[family]
    env.setdefault("PYTORCH_HIP_ALLOC_CONF", "garbage_collection_threshold:0.8,max_split_size_mb:512")
    return env


def hsa_override_for(gpu: str) -> str:
    """Expose the selected HSA override for tests and dry-run output."""

    family = AmdGpuFamily(gpu)
    if family == AmdGpuFamily.AUTO:
        family = detect_gpu_family()
    return HSA_OVERRIDE_BY_FAMILY[family]
