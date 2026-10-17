"""Kafka Event Simulator replaying validation-week transactions with uniform random intra-day timestamps.

Note (Section 7.3 of Plan v2/v3):
Since H&M `t_dat` only records the date (`YYYY-MM-DD`), intra-day timestamps (`HH:MM:SS`) are
sampled uniformly during replay and explicitly tagged with `source='replay'`.
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timezone

from src.contracts.schemas import EventSource, EventType, FashionEvent
from src.utils.id_utils import normalize_article_id


def build_fashion_event(
    customer_id: str,
    article_id: str | int,
    date_str: str = "2020-09-18",
    price: float = 0.025,
    sales_channel_id: int = 2,
    event_type: EventType = "purchase",
    source: EventSource = "replay",
) -> FashionEvent:
    """Create a validated FashionEvent instance with synthetic intra-day time for replay or real time for UI."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if source == "replay":
        hh = random.randint(0, 23)
        mm = random.randint(0, 59)
        ss = random.randint(0, 59)
        ev_time = f"{date_str}T{hh:02d}:{mm:02d}:{ss:02d}Z"
    else:
        ev_time = now_iso

    return FashionEvent(
        event_id=str(uuid.uuid4()),
        event_time=ev_time,
        ingest_time=now_iso,
        customer_id=customer_id,
        article_id=normalize_article_id(article_id),
        event_type=event_type,
        source=source,
        price=price,
        sales_channel_id=1 if sales_channel_id == 1 else 2,
    )


def serialize_event_json(event: FashionEvent) -> bytes:
    """Serialize a FashionEvent to UTF-8 JSON bytes for Kafka producer."""
    return json.dumps(event.model_dump(), ensure_ascii=False).encode("utf-8")
