"""SparkSession factory configured for Delta Lake 3.2, Adaptive Query Execution (AQE), and 16GB WSL2 RAM."""

from __future__ import annotations

from typing import Any

from src.utils.config import get_spark_config


def build_spark_session(app_name: str | None = None, include_kafka: bool = False) -> Any:
    """Create a configured SparkSession with Delta Lake extensions and memory limits."""
    from pyspark.sql import SparkSession

    cfg = get_spark_config()
    builder = (
        SparkSession.builder.appName(app_name or cfg["app_name"])
        .master(cfg["master"])
        .config("spark.driver.memory", cfg["driver_memory"])
        .config("spark.executor.memory", cfg["executor_memory"])
        .config("spark.driver.maxResultSize", cfg["max_result_size"])
    )

    packages = list(cfg.get("jars_packages", []))
    if not include_kafka:
        packages = [p for p in packages if "kafka" not in p]
    if packages:
        builder = builder.config("spark.jars.packages", ",".join(packages))

    for k, v in cfg.get("spark_conf", {}).items():
        builder = builder.config(k, v)

    return builder.getOrCreate()
