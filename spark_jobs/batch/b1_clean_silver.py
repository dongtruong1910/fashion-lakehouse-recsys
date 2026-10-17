"""Job B1: Clean Bronze tables into Delta Silver Layer (`customer_idx` int32 mapping & `week_num` partitioning).

Golden Rule #3 (AGENTS.md):
Map 64-character hex `customer_id` to `customer_idx` (int32) in Silver to save GBs of RAM during joins,
ALS, LightGBM, and Two-Tower training.
"""

from __future__ import annotations

from spark_jobs.spark_session import build_spark_session
from src.utils.config import get_paths_config


def build_silver_tables() -> None:
    """Transform Bronze tables into cleaned, indexed, week-partitioned Silver Delta tables."""
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    paths = get_paths_config()
    spark = build_spark_session("B1_Clean_Silver")

    tx_bronze = spark.read.format("delta").load(paths["lakehouse"]["bronze"]["transactions"])

    # Map distinct customer_id -> dense int32 customer_idx (0 .. N-1)
    distinct_cust = tx_bronze.select("customer_id").distinct()
    w = Window.orderBy("customer_id")
    cust_map = distinct_cust.withColumn("customer_idx", (F.row_number().over(w) - 1).cast("int"))
    cust_map.write.format("delta").mode("overwrite").save(
        paths["lakehouse"]["silver"]["customer_mapping"]
    )

    # Compute week_num where 2020-09-16 .. 2020-09-22 is week_num = 104
    min_date = F.lit("2018-09-20").cast("date")
    tx_silver = (
        tx_bronze.join(cust_map, on="customer_id", how="inner")
        .withColumn("week_num", F.floor(F.datediff(F.col("t_dat"), min_date) / 7).cast("smallint"))
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
        paths["lakehouse"]["silver"]["transactions"]
    )


if __name__ == "__main__":
    build_silver_tables()
