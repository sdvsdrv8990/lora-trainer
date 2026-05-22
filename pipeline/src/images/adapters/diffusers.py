from pathlib import Path

from src.entities.prompts import FramePrompt
from src.images.engine import ImageEngine


class DiffusersAdapter(ImageEngine):
    """SD/SDXL adapter via HuggingFace diffusers.

    Install: pip install diffusers accelerate
    AMD ROCm: pip install torch --index-url https://download.pytorch.org/whl/rocm6.0
    """

    def __init__(self, profile=None):
        self.profile = profile
        self._pipeline = None

    def _get_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        try:
            import torch
            from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline
        except ImportError as e:
            raise RuntimeError(
                "diffusers + torch required. "
                "Install: pip install diffusers accelerate; "
                "AMD: pip install torch --index-url https://download.pytorch.org/whl/rocm6.0"
            ) from e

        model_id = (self.profile.model_id if self.profile else None) or \
            "stabilityai/stable-diffusion-xl-base-1.0"
        device = (self.profile.device if self.profile else None) or "cpu"
        dtype_str = (self.profile.dtype if self.profile else None) or "float32"
        dtype = torch.float16 if dtype_str == "float16" else torch.float32

        PipeClass = StableDiffusionXLPipeline if "xl" in model_id.lower() else StableDiffusionPipeline
        pipe = PipeClass.from_pretrained(model_id, torch_dtype=dtype)

        try:
            pipe = pipe.to(device)
        except Exception:
            fallback = (self.profile.fallback_device if self.profile else None) or "cpu"
            pipe = pipe.to(fallback)

        self._pipeline = pipe
        return pipe

    def generate(self, prompt: FramePrompt, output_dir: Path) -> Path:
        pipe = self._get_pipeline()

        params: dict = {}
        if self.profile:
            p = self.profile.default_params
            params = {
                "num_inference_steps": p.steps,
                "guidance_scale": p.guidance_scale,
                "width": p.width,
                "height": p.height,
            }

        image = pipe(
            prompt=prompt.prompt,
            negative_prompt=prompt.negative_prompt or None,
            **params,
        ).images[0]

        output_dir.mkdir(parents=True, exist_ok=True)
        out = output_dir / f"frame_{prompt.frame_id:04d}.png"
        image.save(str(out))
        return out
