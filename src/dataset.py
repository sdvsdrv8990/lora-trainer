"""Dataset preparation for kohya-ss sd-scripts."""

from __future__ import annotations

import re
import shutil
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def slugify_trigger(trigger_word: str) -> str:
    """Convert a trigger word into a safe kohya directory suffix."""

    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", trigger_word.strip()).strip("_")
    return slug or "lora_style"


class DatasetPreparer:
    """Prepare `{repeats}_{trigger}/image.ext + image.txt` kohya datasets."""

    def __init__(self, source_dir: Path, work_dir: Path, trigger_word: str, repeats: int) -> None:
        self.source_dir = source_dir
        self.work_dir = work_dir
        self.trigger_word = trigger_word
        self.repeats = repeats

    def prepare(self) -> Path:
        if not self.source_dir.is_dir():
            raise FileNotFoundError(f"Images directory does not exist: {self.source_dir}")

        images = sorted(
            path for path in self.source_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS
        )
        if not images:
            raise ValueError(f"No supported images found in {self.source_dir}")

        dataset_root = self.work_dir / "dataset"
        target_dir = dataset_root / f"{self.repeats}_{slugify_trigger(self.trigger_word)}"
        target_dir.mkdir(parents=True, exist_ok=True)

        for index, image in enumerate(images, start=1):
            target_image = target_dir / f"{index:04d}{image.suffix.lower()}"
            shutil.copy2(image, target_image)

            source_caption = image.with_suffix(".txt")
            target_caption = target_image.with_suffix(".txt")
            if source_caption.exists():
                caption = source_caption.read_text(encoding="utf-8").strip()
                if self.trigger_word not in caption:
                    caption = f"{self.trigger_word}, {caption}" if caption else self.trigger_word
            else:
                caption = self.trigger_word
            target_caption.write_text(f"{caption}\n", encoding="utf-8")

        return dataset_root
