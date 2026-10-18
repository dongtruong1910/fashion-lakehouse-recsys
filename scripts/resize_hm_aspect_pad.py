"""Aspect-ratio preserving image resizer with white letterbox padding (`256x256` or `384x384`)."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from PIL import Image, ImageOps


def resize_with_white_padding(
    img: Image.Image,
    target_size: tuple[int, int] = (256, 256),
    fill_color: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Resize a PIL image while strictly preserving its original aspect ratio, padding with white."""
    rgb = img.convert("RGB")
    return ImageOps.pad(rgb, target_size, method=Image.Resampling.BICUBIC, color=fill_color)


def resize_directory_with_white_padding(
    input_dir: Path,
    output_dir: Path,
    target_size: tuple[int, int] = (256, 256),
    limit: int | None = None,
) -> dict[str, object]:
    """Batch-resize original images from `input_dir` into an isolated `output_dir` with letterbox padding (A15)."""
    if input_dir.resolve() == output_dir.resolve():
        raise ValueError("input_dir and output_dir must be distinct directories to protect raw data.")

    files = sorted(input_dir.rglob("*.jpg"))
    if limit is not None:
        files = files[:limit]

    processed = 0
    for src_path in files:
        rel = src_path.relative_to(input_dir)
        dst_path = output_dir / rel
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src_path) as im:
            padded = resize_with_white_padding(im, target_size=target_size)
            padded.save(dst_path, format="JPEG", quality=92)
        processed += 1

    return {
        "status": "ok",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "target_size": list(target_size),
        "processed_images": processed,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch resize H&M original images with aspect-ratio preserving white letterbox padding."
    )
    parser.add_argument("--input-dir", type=Path, required=True, help="Path to original unstretched images.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory for padded images.")
    parser.add_argument("--size", type=int, default=256, help="Target square resolution (default: 256).")
    parser.add_argument("--limit", type=int, default=None, help="Optional max images for smoke testing.")
    args = parser.parse_args()

    summary = resize_directory_with_white_padding(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        target_size=(args.size, args.size),
        limit=args.limit,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
