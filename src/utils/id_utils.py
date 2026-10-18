"""Strict ID normalization utilities for H&M article_id, product_code, and Qdrant point IDs.

Golden Rule #2 (AGENTS.md):
H&M `article_id` MUST always be a 10-character zero-padded string (e.g., '0108775015').
Never allow integer conversion to strip the leading zero.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import re

# Anchor date (Wednesday 2018-09-19) so that every 7-day H&M evaluation week aligns exactly with:
# - Week 0   : 2018-09-19 .. 2018-09-25 (contains first H&M transaction date 2018-09-20)
# - Week 102 : 2020-09-02 .. 2020-09-08
# - Week 103 : 2020-09-09 .. 2020-09-15 (Dev / Model Selection Week — exact 7 days)
# - Week 104 : 2020-09-16 .. 2020-09-22 (Final Test Holdout Week — exact 7 days)
HM_WEEK_ANCHOR_DATE: date = date(2018, 9, 19)
_HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_DEMO_CUST_RE = re.compile(r"^(?:cust_demo|demo_[a-zA-Z0-9_-]{1,58}|session_[a-zA-Z0-9_-]{1,56})$")


def normalize_article_id(raw_id: str | int) -> str:
    """Normalize an H&M article_id into a strict 10-character zero-padded digit string.

    Args:
        raw_id: Raw article identifier (int or string, e.g. 108775015 or "0108775015").

    Returns:
        10-character zero-padded string (e.g., "0108775015").

    Raises:
        ValueError: If raw_id is bool, empty, non-numeric, zero, or exceeds 10 digits.
    """
    if isinstance(raw_id, bool) or raw_id is None:
        raise ValueError(f"Invalid article_id '{raw_id}': must be a digit string or integer.")
    cleaned = str(raw_id).strip()
    if cleaned.endswith(".0"):
        cleaned = cleaned[:-2]
    if not cleaned or not cleaned.isdigit():
        raise ValueError(f"Invalid article_id '{raw_id}': must contain only ASCII digits.")
    if len(cleaned) > 10:
        raise ValueError(f"Invalid article_id '{raw_id}': length {len(cleaned)} exceeds 10 digits.")
    if int(cleaned) <= 0:
        raise ValueError(f"Invalid article_id '{raw_id}': must represent a positive identifier.")
    return cleaned.zfill(10)


def normalize_product_code(raw_code: str | int) -> str:
    """Normalize an H&M product_code into a strict 7-character zero-padded digit string."""
    if isinstance(raw_code, bool) or raw_code is None:
        raise ValueError(f"Invalid product_code '{raw_code}': must be a digit string or integer.")
    cleaned = str(raw_code).strip()
    if cleaned.endswith(".0"):
        cleaned = cleaned[:-2]
    if not cleaned or not cleaned.isdigit():
        raise ValueError(f"Invalid product_code '{raw_code}': must contain only ASCII digits.")
    if len(cleaned) > 7:
        raise ValueError(
            f"Invalid product_code '{raw_code}': length {len(cleaned)} exceeds 7 digits."
        )
    if int(cleaned) <= 0:
        raise ValueError(f"Invalid product_code '{raw_code}': must represent a positive code.")
    return cleaned.zfill(7)


def extract_product_code(article_id: str | int) -> str:
    """Extract the 7-character product_code prefix from an article_id.

    All color variants of the same design share the same 7-digit product_code.
    """
    norm_id = normalize_article_id(article_id)
    return norm_id[:7]


def validate_customer_id(customer_id: str, allow_demo_id: bool = True) -> str:
    """Validate an H&M 64-char hex customer_id (or explicit demo_/session_ ID when allowed)."""
    if not isinstance(customer_id, str):
        raise ValueError("customer_id must be a string.")
    cleaned = customer_id.strip()
    if _HEX64_RE.match(cleaned):
        return cleaned.lower()
    if allow_demo_id and _DEMO_CUST_RE.match(cleaned):
        return cleaned
    raise ValueError(
        f"Invalid customer_id '{customer_id}': must be a 64-char hex string or explicit demo_/session_ ID."
    )


def _coerce_to_date(d: str | date | datetime) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        return date.fromisoformat(d.strip()[:10])
    raise TypeError(f"Unsupported date value: {d!r}")


def date_to_hm_week_num(d: str | date | datetime) -> int:
    """Map a calendar date (`YYYY-MM-DD`) to its canonical H&M `week_num`.

    Guaranteed alignment:
    - `2020-09-09` .. `2020-09-15` -> `103` (Dev Week)
    - `2020-09-16` .. `2020-09-22` -> `104` (Final Test Week)
    """
    dt = _coerce_to_date(d)
    delta_days = (dt - HM_WEEK_ANCHOR_DATE).days
    if delta_days < 0:
        raise ValueError(f"Date {dt.isoformat()} precedes H&M anchor {HM_WEEK_ANCHOR_DATE.isoformat()}.")
    return delta_days // 7


def hm_week_num_to_date_range(week_num: int) -> tuple[date, date]:
    """Return the inclusive `(start_date, end_date)` for a canonical `week_num`."""
    if week_num < 0:
        raise ValueError(f"week_num must be non-negative, got {week_num}.")
    start = HM_WEEK_ANCHOR_DATE + timedelta(days=int(week_num) * 7)
    end = start + timedelta(days=6)
    return start, end


def validate_no_temporal_leakage(
    max_feature_date: str | date | datetime, target_week_num: int
) -> None:
    """Raise ValueError if `max_feature_date` is on or after the start date of `target_week_num`."""
    feat_dt = _coerce_to_date(max_feature_date)
    week_start, _ = hm_week_num_to_date_range(target_week_num)
    if feat_dt >= week_start:
        raise ValueError(
            f"Temporal leakage detected: max_feature_date={feat_dt.isoformat()} "
            f">= target_week {target_week_num} start_date={week_start.isoformat()}."
        )


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
