"""Job B0: Ingest raw H&M CSVs into Delta Bronze Layer with explicit schema and 10-char article_id padding.

Golden Rule #2 (AGENTS.md):
Never use `inferSchema=True` on H&M CSVs because `article_id` ('0108775015') will lose its leading zero.
"""

from __future__ import annotations

from spark_jobs.spark_session import build_spark_session
from src.utils.config import get_paths_config


def ingest_transactions_to_bronze(limit_rows: int | None = None) -> None:
    """Read raw transactions_train.csv with explicit StringType for article_id and write to Delta Bronze."""
    from pyspark.sql import functions as F
    from pyspark.sql.types import FloatType, IntegerType, StringType, StructField, StructType

    paths = get_paths_config()
    spark = build_spark_session("B0_Ingest_Bronze")

    tx_schema = StructType(
        [
            StructField("t_dat", StringType(), nullable=False),
            StructField("customer_id", StringType(), nullable=False),
            StructField("article_id", StringType(), nullable=False),
            StructField("price", FloatType(), nullable=True),
            StructField("sales_channel_id", IntegerType(), nullable=True),
        ]
    )

    df = spark.read.csv(paths["raw"]["transactions_csv"], header=True, schema=tx_schema)
    if limit_rows is not None:
        df = df.limit(limit_rows)

    df_clean = df.withColumn("article_id", F.lpad(F.trim(F.col("article_id")), 10, "0")).withColumn(
        "t_dat", F.to_date(F.col("t_dat"), "yyyy-MM-dd")
    )

    df_clean.write.format("delta").mode("overwrite").save(paths["lakehouse"]["bronze"]["transactions"])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest H&M raw CSVs into Delta Bronze.")
    parser.add_argument("--smoke-test", action="store_true", help="Run on 5,000 rows only.")
    args = parser.parse_args()
    ingest_transactions_to_bronze(limit_rows=5000 if args.smoke_test else None)
