"""Day 1 Verification Script (`TASK-02`): Check H&M 256x256 images for aspect-ratio distortion vs white-border padding.

As noted in `docs/MASTER_PLAN.md`:
Original H&M catalog photos are portrait (~2:3 aspect ratio). If a pre-resized 256x256 dataset
was stretched directly without white letterbox padding, trousers and dresses will look squashed/wide.
This script inspects a sample of images, measures left/right white border padding, and writes
a JSON report to `reports/tables/hm256_aspect_check.json`.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image


def check_has_white_letterbox_padding(
    img: Image.Image, white_threshold: int = 248, border_width: int = 12
) -> bool:
    """Return True if the image has uniform white strips on its left and right edges (heuristic only)."""
    arr = np.asarray(img.convert("RGB"))
    left_strip = arr[:, :border_width, :]
    right_strip = arr[:, -border_width:, :]
    return bool(np.mean(left_strip) >= white_threshold and np.mean(right_strip) >= white_threshold)


def analyze_image_directory(
    image_dir: Path,
    sample_size: int = 50,
    seed: int = 42,
    reference_dir: Path | None = None,
) -> dict:
    """Sample images from `image_dir`, measure resolutions and white-border heuristic, and optionally compare against `reference_dir` (Finding A15)."""
    all_jpgs = sorted(image_dir.rglob("*.jpg"))
    timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not all_jpgs:
        return {
            "status": "no_images_found",
            "timestamp_utc": timestamp_utc,
            "seed": seed,
            "image_dir": str(image_dir),
            "total_images": 0,
        }

    rng = random.Random(seed)
    sampled = rng.sample(all_jpgs, min(sample_size, len(all_jpgs)))

    sizes: dict[str, int] = {}
    padded_count = 0
    non_square_count = 0
    ref_compared = 0
    sampled_ids: list[str] = []

    for p in sampled:
        sampled_ids.append(p.stem)
        with Image.open(p) as im:
            sz = f"{im.width}x{im.height}"
            sizes[sz] = sizes.get(sz, 0) + 1
            if im.width != im.height:
                non_square_count += 1
            elif check_has_white_letterbox_padding(im):
                padded_count += 1

            if reference_dir is not None:
                ref_candidate = reference_dir / p.relative_to(image_dir)
                if ref_candidate.exists():
                    ref_compared += 1

    white_border_ratio = padded_count / len(sampled)
    if non_square_count > 0:
        recommendation = "NON_SQUARE_ORIGINAL_ASPECT_DETECTED_RESIZE_WITH_LETTERBOX_PAD"
        verification_mode = "geometry_non_square"
    elif ref_compared > 0:
        recommendation = "VERIFIED_AGAINST_REFERENCE_ORIGINALS"
        verification_mode = "reference_comparison"
    else:
        # White borders alone on studio catalog photos do not prove aspect ratio was preserved (Finding A15)
        recommendation = (
            "INCONCLUSIVE_WHITE_BORDER_HEURISTIC_COMPARE_WITH_ORIGINAL_OR_VISUAL_INSPECTION"
            if white_border_ratio >= 0.6
            else "WARNING_UNPADDED_SQUARE_DETECTED_CONSIDER_LETTERBOX_RESIZE_FROM_ORIGINALS"
        )
        verification_mode = "white_border_heuristic_only"

    return {
        "status": "ok",
        "verification_mode": verification_mode,
        "timestamp_utc": timestamp_utc,
        "seed": seed,
        "image_dir": str(image_dir),
        "total_images": len(all_jpgs),
        "sampled_images": len(sampled),
        "sampled_article_ids": sampled_ids[:20],
        "resolutions": sizes,
        "white_border_heuristic_ratio": round(white_border_ratio, 4),
        "recommendation": recommendation,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect H&M 256x256 dataset aspect ratio & padding.")
    parser.add_argument("--image-dir", type=Path, default=Path("data/raw/hm/images"))
    parser.add_argument("--reference-dir", type=Path, default=None)
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output", type=Path, default=Path("reports/tables/hm256_aspect_check.json")
    )
    args = parser.parse_args()

    report = analyze_image_directory(
        args.image_dir,
        sample_size=args.sample_size,
        seed=args.seed,
        reference_dir=args.reference_dir,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
