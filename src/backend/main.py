"""FastAPI Serving Engine enforcing `docs/DATA_CONTRACTS.md` (Section 6).

Run locally:
    uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI

from src.contracts.schemas import (
    FashionEvent,
    RecommendationResponse,
    ScoredProductItem,
    VisualSearchResponse,
)
from src.utils.id_utils import normalize_article_id

app = FastAPI(
    title="Fashion Lakehouse Multimodal Search & Recommendation API",
    version="0.3.0",
    description="Unified Serving Layer for Visual Search, Real-Time Hybrid Recommendations, and Outfit Completion.",
)


@app.get("/health")
def health_check() -> dict[str, Any]:
    """Return service health and hardware configuration summary."""
    return {
        "status": "ok",
        "version": "0.3.0",
        "services": {
            "qdrant": "configured",
            "redis": "configured",
            "kafka": "configured",
        },
    }


@app.post("/api/v1/visual-search", response_model=VisualSearchResponse)
def visual_search_endpoint(
    customer_id: str | None = None,
    text_query: str | None = None,
    top_k: int = 12,
) -> VisualSearchResponse:
    """Visual + Multimodal Search with optional Two-Tower personalization (`TASK-SRV-01`)."""
    t0 = time.perf_counter()
    latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return VisualSearchResponse(
        customer_id=customer_id,
        selected_box_id=0,
        detections=[],
        results=[],
        latency_ms=latency_ms,
    )


@app.get("/api/v1/recommend/{customer_id}", response_model=RecommendationResponse)
def recommend_for_customer(customer_id: str, top_k: int = 12) -> RecommendationResponse:
    """Personalized Home Feed blending Batch candidates, Real-time Session Two-Tower, and Trending 15m."""
    t0 = time.perf_counter()
    latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return RecommendationResponse(
        customer_id=customer_id,
        recent_session_items=[],
        recommendations=[],
        latency_ms=latency_ms,
    )


@app.get("/api/v1/outfit/{article_id}", response_model=list[ScoredProductItem])
def recommend_outfit(article_id: str, top_k: int = 6) -> list[ScoredProductItem]:
    """Complete-the-Look cross-category outfit recommendation (`cooc_outfit` + visual style similarity)."""
    _ = normalize_article_id(article_id)
    return []


@app.post("/api/v1/events")
def record_user_event(event: FashionEvent) -> dict[str, Any]:
    """Ingest user interaction event (`view`, `click`, `add_to_cart`, `purchase`) into Redis session & Kafka."""
    return {
        "status": "accepted",
        "event_id": event.event_id,
        "customer_id": event.customer_id,
        "article_id": event.article_id,
        "event_type": event.event_type,
    }
