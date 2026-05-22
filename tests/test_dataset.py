from pathlib import Path

from src.dataset import DatasetPreparer, slugify_trigger


def test_slugify_trigger_keeps_kohya_directory_safe() -> None:
    assert slugify_trigger("stickman style!") == "stickman_style"


def test_prepare_creates_repeated_trigger_directory_with_captions(tmp_path: Path) -> None:
    images = tmp_path / "images"
    images.mkdir()
    (images / "sample.PNG").write_bytes(b"fake image")
    (images / "sample.txt").write_text("thin black lines", encoding="utf-8")

    dataset_root = DatasetPreparer(images, tmp_path / "work", "stickman_style", 10).prepare()

    target = dataset_root / "10_stickman_style"
    assert (target / "0001.png").exists()
    assert (target / "0001.txt").read_text(encoding="utf-8") == "stickman_style, thin black lines\n"
