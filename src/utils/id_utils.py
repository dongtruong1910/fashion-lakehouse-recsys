"""Strict ID normalization utilities for H&M article_id, product_code, and Qdrant point IDs.

Golden Rule #2 (AGENTS.md):
H&M `article_id` MUST always be a 10-character zero-padded string (e.g., '0108775015').
Never allow integer conversion to strip the leading zero.
"""

from __future__ import annotations

from pathlib import Path


def normalize_article_id(raw_id: str | int) -> str:
    """Normalize an H&M article_id into a strict 10-character zero-padded digit string.

    Args:
        raw_id: Raw article identifier (int or string, e.g. 108775015 or "0108775015").

    Returns:
        10-character zero-padded string (e.g., "0108775015").

    Raises:
        ValueError: If raw_id is empty, non-numeric, or exceeds 10 digits.
    """
    cleaned = str(raw_id).strip()
    if cleaned.endswith(".0"):
        cleaned = cleaned[:-2]
    if not cleaned or not cleaned.isdigit():
        raise ValueError(f"Invalid article_id '{raw_id}': must contain only digits.")
    if len(cleaned) > 10:
        raise ValueError(f"Invalid article_id '{raw_id}': length {len(cleaned)} exceeds 10 digits.")
    return cleaned.zfill(10)


def extract_product_code(article_id: str | int) -> str:
    """Extract the 7-character product_code prefix from an article_id.

    All color variants of the same design share the same 7-digit product_code.
    """
    norm_id = normalize_article_id(article_id)
    return norm_id[:7]


def article_id_to_rel_image_path(article_id: str | int) -> str:
    """Return the relative H&M image path (e.g. '010/0108775015.jpg') for an article_id."""
    norm_id = normalize_article_id(article_id)
    folder = norm_id[:3]
    return f"{folder}/{norm_id}.jpg"


def resolve_article_image_path(images_root: str | Path, article_id: str | int) -> Path:
    """Return the full Path to an article's image file on disk."""
    return Path(images_root) / article_id_to_rel_image_path(article_id)


def article_id_to_qdrant_point_id(article_id: str | int) -> int:
    """Convert a 10-character article_id to a positive integer Point ID for Qdrant."""
    norm_id = normalize_article_id(article_id)
    return int(norm_id)


def qdrant_point_id_to_article_id(point_id: int) -> str:
    """Convert a Qdrant integer Point ID back into a 10-character zero-padded article_id."""
    return normalize_article_id(point_id)
