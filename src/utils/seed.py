"""Deterministic seed utilities for reproducible experiments."""

from __future__ import annotations

import os
import random

import numpy as np


def seed_everything(seed: int = 42) -> None:
    """Fix random seeds across Python, NumPy, and PyTorch (if installed)."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass
