"""CLI entry point for lora-trainer."""

from __future__ import annotations

import shlex
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.rocm_utils import hsa_override_for
from src.trainer import LoraTrainer, TrainingConfig, load_default_config
from src.validator import EnvironmentValidator, ValidationError


console = Console()


def _merged_config(project_root: Path, **overrides: object) -> TrainingConfig:
    config = load_default_config(project_root / "config" / "default.yaml")
    data = config.model_dump()
    data.update({key: value for key, value in overrides.items() if value is not None})
    return TrainingConfig(**data)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--images", "-i", type=click.Path(path_type=Path), required=True, help="Folder with images.")
@click.option("--output", "-o", "output_dir", type=click.Path(path_type=Path), help="Output folder.")
@click.option("--name", "-n", "output_name", default=None, help="LoRA output name.")
@click.option("--trigger", "-t", "trigger_word", default=None, help="Trigger word.")
@click.option("--epochs", "-e", type=int, default=None, help="Training epochs.")
@click.option("--rank", "-r", type=int, default=None, help="LoRA rank, 16-64.")
@click.option("--gpu", "-g", type=click.Choice(["auto", "rdna2", "rdna3"]), default=None, help="AMD GPU family.")
@click.option("--base-model", "-b", "base_model", default=None, help="Base SDXL model.")
@click.option("--dry-run", is_flag=True, help="Print command without launching training.")
def cli(
    images: Path,
    output_dir: Path | None,
    output_name: str | None,
    trigger_word: str | None,
    epochs: int | None,
    rank: int | None,
    gpu: str | None,
    base_model: str | None,
    dry_run: bool,
) -> None:
    """Train an SDXL LoRA on AMD/ROCm Linux with kohya-ss sd-scripts."""

    project_root = Path(__file__).resolve().parent
    config = _merged_config(
        project_root,
        output_dir=output_dir,
        output_name=output_name,
        trigger_word=trigger_word,
        epochs=epochs,
        rank=rank,
        gpu=gpu,
        base_model=base_model,
    )

    console.print(Panel.fit("LoRA Trainer for AMD/ROCm", style="bold magenta"))

    if not dry_run:
        try:
            warnings = EnvironmentValidator(project_root).validate(images)
        except ValidationError as exc:
            raise click.ClickException(str(exc)) from exc
        for warning in warnings:
            console.print(f"[yellow]Warning:[/] {warning}")

    trainer = LoraTrainer(project_root, config)
    command = trainer.run(images, dry_run=dry_run)

    table = Table(title="Training command")
    table.add_column("Setting")
    table.add_column("Value")
    table.add_row("HSA_OVERRIDE_GFX_VERSION", hsa_override_for(config.gpu))
    table.add_row("Output", str(config.output_dir / f"{config.output_name}.safetensors"))
    table.add_row("Command", shlex.join(command))
    console.print(table)

    if dry_run:
        console.print("[cyan]Dry run only. Training was not started.[/]")
    else:
        console.print("[green]Training finished.[/]")


if __name__ == "__main__":
    cli()
