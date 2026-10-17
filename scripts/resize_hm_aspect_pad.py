"""Aspect-ratio preserving image resizer with white letterbox padding (`256x256` or `384x384`)."""

from __future__ import annotations

from PIL import Image, ImageOps


def resize_with_white_padding(
    img: Image.Image,
    target_size: tuple[int, int] = (256, 256),
    fill_color: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Resize a PIL image while strictly preserving its original aspect ratio, padding with white."""
    rgb = img.convert("RGB")
    return ImageOps.pad(rgb, target_size, method=Image.Resampling.BICUBIC, color=fill_color)
