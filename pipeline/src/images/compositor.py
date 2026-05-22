from pathlib import Path

from src.entities.layout import (
    AssetLayer, AssetCompositeLayer, Canvas, CharacterCompositeLayer,
    CharacterLayer, FrameLayout, GeneratedLayer, SpeechBubbleLayer, TextLayer,
)
from pathlib import Path as _Path
from typing import Optional as _Optional

from src.images.assets import resolve_asset_by_id, resolve_asset_path, save_comp_asset

try:
    import cairosvg as _cairosvg_probe  # noqa: F401
    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _svg_to_pil(svg_path: Path, scale: float = 1.0, color_map: dict | None = None):
    from PIL import Image
    import io

    try:
        import cairosvg
        content = svg_path.read_text(encoding="utf-8")
        if color_map:
            for old, new in color_map.items():
                content = content.replace(old, new)
        png_bytes = cairosvg.svg2png(bytestring=content.encode(), scale=scale)
        return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    except ImportError:
        # cairosvg not installed — return a translucent grey placeholder
        w = max(1, int(80 * scale))
        h = max(1, int(160 * scale))
        return Image.new("RGBA", (w, h), (180, 180, 180, 160))


class Compositor:
    def __init__(self, canvas: Canvas, output_dir: Path, image_engine=None, workspace: _Optional[_Path] = None):
        self.canvas = canvas
        self.output_dir = output_dir
        self.image_engine = image_engine
        self.workspace = workspace

    def _resolve(self, asset_path: str) -> _Path:
        return resolve_asset_path(asset_path, self.workspace)

    # ── public interface ──────────────────────────────────────────────────────

    def render_frame(self, frame: FrameLayout) -> Path:
        from PIL import Image

        img = self._blank_canvas(frame.background)
        for layer in frame.layers:
            try:
                self._render_layer(img, layer)
            except Exception:
                pass  # non-fatal per-layer errors

        output_dir = self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        out = output_dir / f"frame_{frame.frame_id:04d}.png"
        img.convert("RGB").save(str(out), "PNG")
        return out

    def render_scene_sequence(self, frame: FrameLayout) -> list[Path]:
        """Return a list of PNGs — one per element in appearance_order.

        Elements not in appearance_order appear on every frame.
        If appearance_order is empty, returns a single full render.
        """
        from PIL import Image

        ordered_ids = frame.appearance_order
        if not ordered_ids:
            return [self.render_frame(frame)]

        sequential = {l.id for l in frame.layers if l.id in ordered_ids}
        base_layers = [l for l in frame.layers if l.id not in sequential]
        by_id = {l.id: l for l in frame.layers if l.id in sequential}

        output_dir = self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        paths: list[Path] = []
        for i, lid in enumerate(ordered_ids):
            img = self._blank_canvas(frame.background)
            for layer in base_layers:
                try:
                    self._render_layer(img, layer)
                except Exception:
                    pass
            for prev_id in ordered_ids[: i + 1]:
                if prev_id in by_id:
                    try:
                        self._render_layer(img, by_id[prev_id])
                    except Exception:
                        pass
            out = output_dir / f"frame_{frame.frame_id:04d}_seq_{i:02d}.png"
            img.convert("RGB").save(str(out), "PNG")
            paths.append(out)

        return paths

    # ── canvas helpers ────────────────────────────────────────────────────────

    def _blank_canvas(self, background: str):
        from PIL import Image

        r, g, b = _hex_to_rgb(background)
        return Image.new("RGBA", (self.canvas.width, self.canvas.height), (r, g, b, 255))

    # ── layer dispatch ────────────────────────────────────────────────────────

    def _render_layer(self, canvas, layer) -> None:
        if isinstance(layer, CharacterCompositeLayer):
            self._render_character_composite(canvas, layer)
        elif isinstance(layer, AssetCompositeLayer):
            self._render_asset_composite(canvas, layer)
        elif isinstance(layer, AssetLayer):
            self._render_asset(canvas, layer)
        elif isinstance(layer, CharacterLayer):
            self._render_character(canvas, layer)
        elif isinstance(layer, SpeechBubbleLayer):
            self._render_speech_bubble(canvas, layer)
        elif isinstance(layer, GeneratedLayer):
            self._render_generated(canvas, layer)
        elif isinstance(layer, TextLayer):
            self._render_text(canvas, layer)

    # ── per-type renderers ────────────────────────────────────────────────────

    def _render_asset(self, canvas, layer: AssetLayer) -> None:
        from PIL import Image

        asset = self._resolve(layer.asset_path)
        if not asset.exists():
            return
        img = _svg_to_pil(asset, scale=layer.scale)
        if layer.flip_x:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if layer.opacity < 1.0:
            r, g, b, a = img.split()
            a = a.point(lambda x: int(x * layer.opacity))
            img = Image.merge("RGBA", (r, g, b, a))
        canvas.paste(img, (layer.x, layer.y), img)

    def _render_character(self, canvas, layer: CharacterLayer) -> None:
        from PIL import Image

        asset = self._resolve(layer.asset_path)
        if not asset.exists():
            return
        img = _svg_to_pil(asset, scale=layer.scale, color_map={"#PLACEHOLDER_COLOR": layer.color})
        if layer.flip_x:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        canvas.paste(img, (layer.x, layer.y), img)

    def _render_speech_bubble(self, canvas, layer: SpeechBubbleLayer) -> None:
        import io
        from PIL import Image, ImageDraw, ImageFont

        bubble_path = self._resolve(f"global_assets/speech_bubbles/{layer.template}.svg")
        if bubble_path.exists():
            try:
                import cairosvg
                png_bytes = cairosvg.svg2png(bytestring=bubble_path.read_bytes())
                bubble_img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
                canvas.paste(bubble_img, (layer.x, layer.y), bubble_img)
            except (ImportError, Exception):
                pass

        draw = ImageDraw.Draw(canvas)
        font = self._load_font(layer.font_size)
        r, g, b = _hex_to_rgb(layer.color)
        draw.text((layer.x + 12, layer.y + 12), layer.text, fill=(r, g, b, 255), font=font)

    def _render_generated(self, canvas, layer: GeneratedLayer) -> None:
        if self.image_engine is None:
            return
        import io
        import tempfile
        from PIL import Image
        from src.entities.prompts import FramePrompt

        fp = FramePrompt(
            frame_id=0, scene_id=0, start=0.0, end=1.0, duration=1.0,
            prompt=layer.prompt, negative_prompt=layer.negative_prompt,
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = self.image_engine.generate(fp, Path(tmp))
            img = Image.open(result).convert("RGBA")
            if layer.scale != 1.0:
                img = img.resize(
                    (int(img.width * layer.scale), int(img.height * layer.scale)),
                    Image.LANCZOS,
                )
            canvas.paste(img, (layer.x, layer.y), img)

    def _render_text(self, canvas, layer: TextLayer) -> None:
        from PIL import ImageDraw

        draw = ImageDraw.Draw(canvas)
        font = self._load_font(layer.font_size)
        r, g, b = _hex_to_rgb(layer.color)
        draw.text((layer.x, layer.y), layer.text, fill=(r, g, b, 255), font=font)

    # ── composite renderers ───────────────────────────────────────────────────

    def _render_character_composite(self, canvas, layer: CharacterCompositeLayer) -> None:
        from PIL import Image

        composite = self._build_composite_image(
            layer.components,
            color_replace=layer.color,
            scale=layer.scale,
        )
        if composite is None:
            return
        if layer.flip_x:
            composite = composite.transpose(Image.FLIP_LEFT_RIGHT)
        canvas.paste(composite, (layer.x, layer.y), composite)

        if layer.save_as_comp:
            comp_name = f"{layer.id}"
            png_bytes = self._image_to_png_bytes(composite)
            try:
                save_comp_asset(layer.group_id, comp_name, png_bytes, self.workspace)
            except Exception:
                pass

    def _render_asset_composite(self, canvas, layer: AssetCompositeLayer) -> None:
        composite = self._build_composite_image(
            layer.components,
            color_replace=None,
            scale=layer.scale,
        )
        if composite is None:
            return
        canvas.paste(composite, (layer.x, layer.y), composite)

        if layer.save_as_comp:
            comp_name = f"{layer.id}"
            png_bytes = self._image_to_png_bytes(composite)
            try:
                save_comp_asset(layer.group_id, comp_name, png_bytes, self.workspace)
            except Exception:
                pass

    def _build_composite_image(self, components, color_replace, scale: float):
        from PIL import Image

        sorted_components = sorted(components, key=lambda c: c.z_index)
        base_img = None

        for comp in sorted_components:
            try:
                asset_path = resolve_asset_by_id(comp.asset_id, self.workspace)
            except (FileNotFoundError, Exception):
                continue

            color_map = {"#PLACEHOLDER_COLOR": color_replace} if color_replace else None
            layer_img = _svg_to_pil(asset_path, scale=scale, color_map=color_map)

            if base_img is None:
                base_img = Image.new("RGBA", layer_img.size, (0, 0, 0, 0))
            elif layer_img.size != base_img.size:
                layer_img = layer_img.resize(base_img.size, Image.LANCZOS)

            base_img.paste(layer_img, (0, 0), layer_img)

        return base_img

    @staticmethod
    def _image_to_png_bytes(img) -> bytes:
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    # ── font helper ───────────────────────────────────────────────────────────

    @staticmethod
    def _load_font(size: int):
        from PIL import ImageFont

        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()
