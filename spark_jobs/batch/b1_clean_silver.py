"""Job B1: Clean Bronze tables into Delta Silver Layer (`customer_idx` int32 mapping & `week_num` partitioning).

Golden Rule #3 (AGENTS.md):
Map 64-character hex `customer_id` to `customer_idx` (int32) in Silver to save GBs of RAM during joins,
ALS, LightGBM, and Two-Tower training.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from spark_jobs.spark_session import build_spark_session
from src.utils.config import get_paths_config
from src.utils.id_utils import HM_WEEK_ANCHOR_DATE


def resolve_silver_io_paths(paths: dict[str, Any], smoke_test: bool = False) -> dict[str, str]:
    """Return isolated Bronze input and Silver output paths for smoke vs full runs."""
    if not smoke_test:
        return {
            "bronze_tx": str(paths["lakehouse"]["bronze"]["transactions"]),
            "silver_cust_map": str(paths["lakehouse"]["silver"]["customer_mapping"]),
            "silver_tx": str(paths["lakehouse"]["silver"]["transactions"]),
            "mapping_version": "v1_full",
        }

    smoke_base = str(paths["lakehouse"].get("smoke_base_dir", "data/lakehouse_smoke"))
    smoke_tx = f"{smoke_base}/silver/transactions"
    prod_tx = str(paths["lakehouse"]["silver"]["transactions"])
    if Path(smoke_tx).resolve() == Path(prod_tx).resolve():
        raise ValueError("Safety violation (A03): smoke Silver path cannot equal production Silver path.")

    return {
        "bronze_tx": f"{smoke_base}/bronze/transactions",
        "silver_cust_map": f"{smoke_base}/silver/customer_mapping",
        "silver_tx": smoke_tx,
        "mapping_version": "v1_smoke",
    }


def build_silver_tables(smoke_test: bool = False) -> dict[str, str]:
    """Transform Bronze tables into cleaned, indexed, week-partitioned Silver Delta tables."""
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    paths = get_paths_config()
    io_paths = resolve_silver_io_paths(paths, smoke_test=smoke_test)
    spark = build_spark_session("B1_Clean_Silver")

    tx_bronze = spark.read.format("delta").load(io_paths["bronze_tx"])

    # Map distinct customer_id -> dense int32 customer_idx (0 .. N-1) with explicit mapping_version
    distinct_cust = tx_bronze.select("customer_id").distinct()
    w = Window.orderBy("customer_id")
    cust_map = (
        distinct_cust.withColumn("customer_idx", (F.row_number().over(w) - 1).cast("int"))
        .withColumn("mapping_version", F.lit(io_paths["mapping_version"]))
    )
    cust_map.write.format("delta").mode("overwrite").save(io_paths["silver_cust_map"])

    # Compute canonical week_num anchored at 2018-09-19 so that:
    # - Dev Week (2020-09-09 .. 2020-09-15) is week_num = 103
    # - Final Test Week (2020-09-16 .. 2020-09-22) is week_num = 104
    anchor_date = F.lit(HM_WEEK_ANCHOR_DATE.isoformat()).cast("date")
    tx_silver = (
        tx_bronze.join(cust_map.select("customer_id", "customer_idx"), on="customer_id", how="inner")
        .withColumn("week_num", F.floor(F.datediff(F.col("t_dat"), anchor_date) / 7).cast("smallint"))
        .select(
            "t_dat",
            "week_num",
            "customer_idx",
            "article_id",
            F.col("price").cast("float"),
            F.col("sales_channel_id").cast("byte"),
        )
    )

    tx_silver.write.format("delta").partitionBy("week_num").mode("overwrite").save(
        io_paths["silver_tx"]
    )
    return io_paths


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clean Bronze tables into Silver Delta Lake.")
    parser.add_argument("--smoke-test", action="store_true", help="Run on isolated smoke lakehouse.")
    args = parser.parse_args()
    build_silver_tables(smoke_test=args.smoke_test)
