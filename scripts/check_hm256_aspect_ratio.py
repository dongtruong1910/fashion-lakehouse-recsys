"""Day 1 Verification Script (`TASK-02`): Check H&M 256x256 images for aspect-ratio distortion vs white-border padding.

As noted in `docs/MASTER_PLAN.md`:
Original H&M catalog photos are portrait (~2:3 aspect ratio). If a pre-resized 256x256 dataset
was stretched directly without white letterbox padding, trousers and dresses will look squashed/wide.
This script inspects a sample of images, measures left/right white border padding, and writes
a JSON report to `reports/tables/hm256_aspect_check.json`.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image


def check_has_white_letterbox_padding(
    img: Image.Image, white_threshold: int = 248, border_width: int = 12
) -> bool:
    """Return True if the image has uniform white padding strips on its left and right edges."""
    arr = np.asarray(img.convert("RGB"))
    left_strip = arr[:, :border_width, :]
    right_strip = arr[:, -border_width:, :]
    return bool(np.mean(left_strip) >= white_threshold and np.mean(right_strip) >= white_threshold)


def analyze_image_directory(image_dir: Path, sample_size: int = 50, seed: int = 42) -> dict:
    """Sample images from `image_dir` and check dimensions and white letterbox padding."""
    all_jpgs = list(image_dir.rglob("*.jpg"))
    if not all_jpgs:
        return {
            "status": "no_images_found",
            "image_dir": str(image_dir),
            "total_images": 0,
        }

    rng = random.Random(seed)
    sampled = rng.sample(all_jpgs, min(sample_size, len(all_jpgs)))

    sizes: dict[str, int] = {}
    padded_count = 0
    for p in sampled:
        with Image.open(p) as im:
            sz = f"{im.width}x{im.height}"
            sizes[sz] = sizes.get(sz, 0) + 1
            if im.width == im.height and check_has_white_letterbox_padding(im):
                padded_count += 1

    padded_ratio = padded_count / len(sampled)
    return {
        "status": "ok",
        "image_dir": str(image_dir),
        "total_images": len(all_jpgs),
        "sampled_images": len(sampled),
        "resolutions": sizes,
        "white_padded_ratio": round(padded_ratio, 4),
        "recommendation": (
            "USE_DIRECTLY"
            if padded_ratio >= 0.6
            else "WARNING_UNPADDED_SQUARE_DETECTED_CONSIDER_LETTERBOX_RESIZE"
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect H&M 256x256 dataset aspect ratio & padding.")
    parser.add_argument("--image-dir", type=Path, default=Path("data/raw/hm/images"))
    parser.add_argument(
        "--output", type=Path, default=Path("reports/tables/hm256_aspect_check.json")
    )
    args = parser.parse_args()

    report = analyze_image_directory(args.image_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
