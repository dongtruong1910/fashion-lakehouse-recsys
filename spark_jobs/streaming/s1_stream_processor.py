"""Job S1-S4: Spark Structured Streaming processor with 10m Watermark, 15m/1m Sliding Window, and Redis Sink."""

from __future__ import annotations

from typing import Any


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
        ]
    )
