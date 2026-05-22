from abc import ABC, abstractmethod
from pathlib import Path

from src.entities.prompts import FramePrompt


class ImageEngine(ABC):
    @abstractmethod
    def generate(self, prompt: FramePrompt, output_dir: Path) -> Path:
        """Generate one image for a frame prompt. Return the output file path."""


def get_image_engine(config: dict) -> ImageEngine:
    image_cfg = config.get("image", {})
    profile_id = image_cfg.get("profile", "")

    if profile_id:
        try:
            from src.images.engine_profiles import load_profile
            profile = load_profile(config, profile_id)
            engine_name = profile.engine
        except Exception:
            engine_name = image_cfg.get("engine", "stub")
            profile = None
    else:
        engine_name = image_cfg.get("engine", "stub")
        profile = None

    if engine_name == "stub":
        from src.images.adapters.stub import StubAdapter
        return StubAdapter()
    elif engine_name == "diffusers":
        from src.images.adapters.diffusers import DiffusersAdapter
        return DiffusersAdapter(profile)

    raise ValueError(f"Unknown image engine: {engine_name!r}. Available: stub, diffusers")
