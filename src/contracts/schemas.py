"""Strict Data Contract Schemas enforcing `docs/DATA_CONTRACTS.md` across all modules.

Uses standard-library `@dataclass` with `__post_init__` validation and `.model_dump()` compatibility
so that contracts work both in bare Python / PySpark workers and directly as FastAPI request/response models.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
import math
from typing import Any, Literal
import uuid

from src.utils.id_utils import (
    extract_product_code,
    normalize_article_id,
    normalize_product_code,
    validate_customer_id,
)

DetectorClass = Literal[
    "top",
    "outerwear",
    "pants",
    "shorts",
    "skirt",
    "dress",
    "shoe",
    "bag",
    "hat",
    "eyewear",
    "scarf_tie",
    "belt",
    "other",
]

VALID_DETECTOR_CLASSES: frozenset[str] = frozenset(
    {
        "top",
        "outerwear",
        "pants",
        "shorts",
        "skirt",
        "dress",
        "shoe",
        "bag",
        "hat",
        "eyewear",
        "scarf_tie",
        "belt",
        "other",
    }
)
VALID_EVENT_TYPES: frozenset[str] = frozenset({"view", "click", "add_to_cart", "purchase"})
VALID_EVENT_SOURCES: frozenset[str] = frozenset({"replay", "ui"})
VALID_SALES_CHANNELS: frozenset[int] = frozenset({1, 2})

EventType = Literal["view", "click", "add_to_cart", "purchase"]
EventSource = Literal["replay", "ui"]


def _validate_iso_timestamp_tz(ts: str, field_name: str) -> str:
    if not isinstance(ts, str) or not ts.strip():
        raise ValueError(f"{field_name} must be a non-empty ISO-8601 timestamp string.")
    cleaned = ts.strip()
    iso_candidate = cleaned[:-1] + "+00:00" if cleaned.endswith("Z") else cleaned
    try:
        parsed = datetime.fromisoformat(iso_candidate)
    except ValueError as exc:
        raise ValueError(f"Invalid {field_name} '{ts}': must be valid ISO-8601 datetime.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"Invalid {field_name} '{ts}': timestamp must include timezone ('Z' or offset).")
    return cleaned


def _validate_finite_non_negative(val: float, field_name: str) -> float:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ValueError(f"{field_name} must be a finite number.")
    fval = float(val)
    if not math.isfinite(fval) or fval < 0.0:
        raise ValueError(f"{field_name} must be finite and non-negative, got {val!r}.")
    return fval


@dataclass
class FashionEvent:
    """Kafka message schema for `fashion-events` topic (Section 5 of DATA_CONTRACTS.md)."""

    event_id: str
    event_time: str
    ingest_time: str
    customer_id: str
    article_id: str
    event_type: EventType = "purchase"
    source: EventSource = "replay"
    price: float = 0.0
    sales_channel_id: Literal[1, 2] = 2
    original_t_dat: str | None = None

    def __post_init__(self) -> None:
        try:
            self.event_id = str(uuid.UUID(str(self.event_id).strip()))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"Invalid event_id '{self.event_id}': must be a valid UUID.") from exc

        self.event_time = _validate_iso_timestamp_tz(self.event_time, "event_time")
        self.ingest_time = _validate_iso_timestamp_tz(self.ingest_time, "ingest_time")
        self.customer_id = validate_customer_id(self.customer_id, allow_demo_id=True)
        self.article_id = normalize_article_id(self.article_id)

        if self.event_type not in VALID_EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type '{self.event_type}': must be one of {sorted(VALID_EVENT_TYPES)}."
            )
        if self.source not in VALID_EVENT_SOURCES:
            raise ValueError(
                f"Invalid source '{self.source}': must be one of {sorted(VALID_EVENT_SOURCES)}."
            )
        self.price = _validate_finite_non_negative(self.price, "price")

        if isinstance(self.sales_channel_id, bool) or self.sales_channel_id not in VALID_SALES_CHANNELS:
            raise ValueError(
                f"Invalid sales_channel_id '{self.sales_channel_id}': must be 1 (Store) or 2 (Online)."
            )

        if self.original_t_dat is not None:
            try:
                date.fromisoformat(str(self.original_t_dat).strip())
                self.original_t_dat = str(self.original_t_dat).strip()
            except ValueError as exc:
                raise ValueError(
                    f"Invalid original_t_dat '{self.original_t_dat}': must be YYYY-MM-DD."
                ) from exc

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QdrantProductPayload:
    """Payload schema stored with each product vector in Qdrant `hm_products` collection."""

    article_id: str
    product_code: str
    prod_name: str
    detector_class: DetectorClass
    product_type_name: str
    product_group_name: str
    colour_group_name: str
    graphical_appearance_name: str
    index_group_name: str
    price: float = 0.0
    image_rel_path: str = ""
    encoder_model_id: str = "google/siglip2-base-patch16-224"

    def __post_init__(self) -> None:
        self.article_id = normalize_article_id(self.article_id)
        expected_prefix = extract_product_code(self.article_id)
        if self.product_code is None or str(self.product_code).strip() == "":
            self.product_code = expected_prefix
        else:
            norm_code = normalize_product_code(self.product_code)
            if norm_code != expected_prefix:
                raise ValueError(
                    f"product_code '{norm_code}' does not match 7-digit prefix '{expected_prefix}' "
                    f"of article_id '{self.article_id}'."
                )
            self.product_code = norm_code

        if self.detector_class not in VALID_DETECTOR_CLASSES:
            raise ValueError(
                f"Invalid detector_class '{self.detector_class}': must be one of {sorted(VALID_DETECTOR_CLASSES)}."
            )
        self.price = _validate_finite_non_negative(self.price, "price")

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BoundingBoxDetection:
    """Detected garment bounding box from YOLO11 detector."""

    box_id: int
    detector_class: DetectorClass
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        if self.detector_class not in VALID_DETECTOR_CLASSES:
            raise ValueError(
                f"Invalid detector_class '{self.detector_class}': must be one of {sorted(VALID_DETECTOR_CLASSES)}."
            )
        self.confidence = _validate_finite_non_negative(self.confidence, "confidence")
        if self.confidence > 1.0:
            raise ValueError(f"confidence must be <= 1.0, got {self.confidence}.")
        if len(self.bbox_xyxy) != 4 or not all(math.isfinite(float(v)) for v in self.bbox_xyxy):
            raise ValueError(f"bbox_xyxy must contain 4 finite coordinates, got {self.bbox_xyxy!r}.")

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoredProductItem:
    """A single recommended or retrieved product returned by FastAPI."""

    article_id: str
    prod_name: str
    product_type_name: str
    colour_group_name: str
    detector_class: str
    price: float
    image_rel_path: str
    final_score: float
    visual_similarity: float | None = None
    personalization_score: float | None = None
    candidate_sources: list[str] = field(default_factory=list)
    explanation: str = ""

    def __post_init__(self) -> None:
        self.article_id = normalize_article_id(self.article_id)
        if self.detector_class not in VALID_DETECTOR_CLASSES:
            raise ValueError(
                f"Invalid detector_class '{self.detector_class}': must be one of {sorted(VALID_DETECTOR_CLASSES)}."
            )
        self.price = _validate_finite_non_negative(self.price, "price")
        if not math.isfinite(float(self.final_score)):
            raise ValueError("final_score must be finite.")

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VisualSearchResponse:
    """Response schema for `POST /api/v1/visual-search`."""

    customer_id: str | None = None
    selected_box_id: int | None = None
    detections: list[BoundingBoxDetection] = field(default_factory=list)
    results: list[ScoredProductItem] = field(default_factory=list)
    latency_ms: float = 0.0

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecommendationResponse:
    """Response schema for `GET /api/v1/recommend/{customer_id}`."""

    customer_id: str
    recent_session_items: list[str] = field(default_factory=list)
    recommendations: list[ScoredProductItem] = field(default_factory=list)
    latency_ms: float = 0.0

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)
