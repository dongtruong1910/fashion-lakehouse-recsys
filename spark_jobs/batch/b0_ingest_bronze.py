"""Job B0: Ingest raw H&M CSVs into Delta Bronze Layer with explicit schema and 10-char article_id padding.

Golden Rule #2 (AGENTS.md):
Never use `inferSchema=True` on H&M CSVs because `article_id` ('0108775015') will lose its leading zero.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from spark_jobs.spark_session import build_spark_session
from src.utils.config import get_paths_config


def resolve_bronze_output_path(
    paths: dict[str, Any],
    table_key: str = "transactions",
    smoke_test: bool = False,
    limit_rows: int | None = None,
    output_override: str | None = None,
) -> str:
    """Resolve Bronze output directory and prevent smoke runs from overwriting production Bronze tables."""
    prod_path = str(paths["lakehouse"]["bronze"][table_key])
    is_partial = smoke_test or (limit_rows is not None)

    if output_override:
        target = str(output_override)
    elif is_partial:
        smoke_base = str(paths["lakehouse"].get("smoke_base_dir", "data/lakehouse_smoke"))
        target = f"{smoke_base}/bronze/{table_key}"
    else:
        target = prod_path

    if is_partial and Path(target).resolve() == Path(prod_path).resolve():
        raise ValueError(
            f"Safety violation (A03): Refusing to overwrite production Bronze path '{prod_path}' "
            "during a smoke/limited run. Use smoke_base_dir or an explicit isolated output path."
        )
    return target


def ingest_transactions_to_bronze(
    limit_rows: int | None = None,
    smoke_test: bool = False,
    output_override: str | None = None,
) -> str:
    """Read raw transactions_train.csv with explicit StringType for article_id and write to Delta Bronze."""
    from pyspark.sql import functions as F
    from pyspark.sql.types import FloatType, IntegerType, StringType, StructField, StructType

    paths = get_paths_config()
    target_path = resolve_bronze_output_path(
        paths=paths,
        table_key="transactions",
        smoke_test=smoke_test,
        limit_rows=limit_rows,
        output_override=output_override,
    )
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

    trimmed_id = F.trim(F.col("article_id"))
    df_valid = df.filter(
        F.col("article_id").isNotNull()
        & trimmed_id.rlike("^[0-9]{1,10}$")
        & (trimmed_id.cast("bigint") > 0)
        & F.col("customer_id").isNotNull()
        & (F.length(F.trim(F.col("customer_id"))) == 64)
    )

    df_clean = df_valid.withColumn("article_id", F.lpad(trimmed_id, 10, "0")).withColumn(
        "t_dat", F.to_date(F.col("t_dat"), "yyyy-MM-dd")
    )

    df_clean.write.format("delta").mode("overwrite").save(target_path)
    return target_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest H&M raw CSVs into Delta Bronze.")
    parser.add_argument("--smoke-test", action="store_true", help="Run on 5,000 rows into isolated smoke lakehouse.")
    parser.add_argument("--output", type=str, default=None, help="Optional explicit output path.")
    args = parser.parse_args()
    ingest_transactions_to_bronze(
        limit_rows=5000 if args.smoke_test else None,
        smoke_test=args.smoke_test,
        output_override=args.output,
    )
