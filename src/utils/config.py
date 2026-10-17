"""Centralized YAML configuration loader for paths, class mappings, Spark, and models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = PROJECT_ROOT / "configs"


def load_yaml_config(config_name: str | Path) -> dict[str, Any]:
    """Load a YAML configuration file from the `configs/` directory or an explicit path."""
    path = Path(config_name)
    if not path.is_absolute():
        candidate = CONFIGS_DIR / path
        path = candidate if candidate.exists() else PROJECT_ROOT / path
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_paths_config() -> dict[str, Any]:
    """Return contents of `configs/paths.yaml`."""
    return load_yaml_config("paths.yaml")


def get_class_mapping_config() -> dict[str, Any]:
    """Return contents of `configs/class_mapping.yaml`."""
    return load_yaml_config("class_mapping.yaml")


def get_spark_config() -> dict[str, Any]:
    """Return contents of `configs/spark_config.yaml`."""
    return load_yaml_config("spark_config.yaml")


def get_model_config() -> dict[str, Any]:
    """Return contents of `configs/model_config.yaml`."""
    return load_yaml_config("model_config.yaml")
