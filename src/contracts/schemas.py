"""Strict Data Contract Schemas enforcing `docs/DATA_CONTRACTS.md` across all modules.

Uses standard-library `@dataclass` with `__post_init__` validation and `.model_dump()` compatibility
so that contracts work both in bare Python / PySpark workers and directly as FastAPI request/response models.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from src.utils.id_utils import extract_product_code, normalize_article_id

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

EventType = Literal["view", "click", "add_to_cart", "purchase"]
EventSource = Literal["replay", "ui"]


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

    def __post_init__(self) -> None:
        self.article_id = normalize_article_id(self.article_id)
        if not self.customer_id or not str(self.customer_id).strip():
            raise ValueError("customer_id must not be empty.")
        if self.price < 0.0:
            raise ValueError("price must be non-negative.")

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

    def __post_init__(self) -> None:
        self.article_id = normalize_article_id(self.article_id)
        s = str(self.product_code).strip()
        self.product_code = s.zfill(7) if len(s) <= 7 else extract_product_code(self.article_id)

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BoundingBoxDetection:
    """Detected garment bounding box from YOLO11 detector."""

    box_id: int
    detector_class: DetectorClass
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]

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
