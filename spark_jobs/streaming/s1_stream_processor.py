"""Job S1-S4: Spark Structured Streaming processor with 10m Watermark, 15m/1m Sliding Window, and Redis Sink."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from src.utils.id_utils import normalize_article_id, validate_customer_id


def get_kafka_event_spark_schema() -> Any:
    """Return PySpark StructType matching `FashionEvent` in `src/contracts/schemas.py`."""
    from pyspark.sql.types import FloatType, IntegerType, StringType, StructField, StructType

    return StructType(
        [
            StructField("event_id", StringType(), False),
            StructField("event_time", StringType(), False),
            StructField("ingest_time", StringType(), False),
            StructField("customer_id", StringType(), False),
            StructField("article_id", StringType(), False),
            StructField("event_type", StringType(), False),
            StructField("source", StringType(), False),
            StructField("price", FloatType(), True),
            StructField("sales_channel_id", IntegerType(), True),
            StructField("original_t_dat", StringType(), True),
        ]
    )


def record_session_event_idempotent(
    redis_client: Any,
    event_id: str,
    customer_id: str,
    article_id: str | int,
    max_recent_items: int = 50,
    session_ttl_seconds: int = 7 * 86400,
    dedup_ttl_seconds: int = 86400,
) -> bool:
    """Atomically deduplicate `event_id` before pushing `article_id` to `user:{customer_id}:recent` (Finding A09).

    Ensures that even if both the FastAPI `/api/v1/events` fast-path and Spark `foreachBatch` retry
    process the same `event_id`, the session list is updated at most once.

    Returns:
        True if the event was newly applied, False if it was already processed.
    """
    cust = validate_customer_id(customer_id, allow_demo_id=True)
    art = normalize_article_id(article_id)
    dedup_key = f"event:seen:{event_id}"
    session_key = f"user:{cust}:recent"

    is_new = redis_client.set(dedup_key, "1", nx=True, ex=dedup_ttl_seconds)
    if not is_new:
        return False

    pipe = redis_client.pipeline(transaction=True)
    pipe.lpush(session_key, art)
    pipe.ltrim(session_key, 0, max_recent_items - 1)
    pipe.expire(session_key, session_ttl_seconds)
    pipe.execute()
    return True


def publish_trending_window_snapshot(
    redis_client: Any,
    window_rows: Iterable[dict[str, Any]],
    key_prefix: str = "trend:15m",
    ttl_seconds: int = 1800,
) -> dict[str, Any]:
    """Publish only the latest sliding-window snapshot to Redis using idempotent replacement (Finding A09).

    Each row in `window_rows` must provide `window_end` (ISO string or comparable), `article_id`,
    `score` (float), and optional `detector_class`.
    """
    rows = list(window_rows)
    if not rows:
        return {"published_window_end": None, "num_items": 0}

    latest_window_end = max(str(r["window_end"]) for r in rows)
    latest_rows = [r for r in rows if str(r["window_end"]) == latest_window_end]

    global_scores: dict[str, float] = {}
    by_class: dict[str, dict[str, float]] = {}
    for r in latest_rows:
        aid = normalize_article_id(r["article_id"])
        sc = float(r["score"])
        global_scores[aid] = sc
        det_cls = str(r.get("detector_class") or "").strip()
        if det_cls:
            by_class.setdefault(det_cls, {})[aid] = sc

    pipe = redis_client.pipeline(transaction=True)
    if global_scores:
        pipe.delete(key_prefix)
        pipe.zadd(key_prefix, global_scores)
        pipe.expire(key_prefix, ttl_seconds)

    for det_cls, cls_scores in by_class.items():
        cls_key = f"{key_prefix}:{det_cls}"
        pipe.delete(cls_key)
        pipe.zadd(cls_key, cls_scores)
        pipe.expire(cls_key, ttl_seconds)

    pipe.set(f"{key_prefix}:version", latest_window_end, ex=ttl_seconds)
    pipe.execute()
    return {"published_window_end": latest_window_end, "num_items": len(global_scores)}
