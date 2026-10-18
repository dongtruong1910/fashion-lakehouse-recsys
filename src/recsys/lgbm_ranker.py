"""L3 Hybrid Ranker: Unified LightGBM LambdaRank model for both Offline Evaluation and Online Serving."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.utils.config import get_model_config

FEATURE_COLUMNS: list[str] = [
    "src_repurchase_rank",
    "src_cooc_rank",
    "src_age_pop_rank",
    "src_als_rank",
    "src_twotower_rank",
    "src_count",
    "als_score",
    "tt_score",
    "visual_affinity_score",
    "user_item_purchase_cnt",
    "days_since_last_buy_item",
    "user_ptype_affinity",
    "user_colour_affinity",
    "price_diff_user_avg",
    "item_sales_1w",
    "item_sales_4w",
    "item_trend_ratio",
    "user_age",
    "user_total_tx_4w",
    "user_online_ratio",
    "product_type_no",
    "colour_group_code",
    "index_group_no",
    "garment_group_no",
]

CATEGORICAL_FEATURES: list[str] = [
    "product_type_no",
    "colour_group_code",
    "index_group_no",
    "garment_group_no",
]


def prepare_lgbm_query_frame(
    df: pd.DataFrame,
    drop_all_zero_groups: bool = False,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Sort candidate DataFrame by `(target_week, customer_idx, article_id)` and compute LambdaRank group sizes.

    Fixes Finding A02:
    - A customer appearing in multiple target weeks (e.g. week 101 and week 102) represents two distinct
      ranking queries with different historical cutoffs and labels, and MUST NOT be merged into one group.
    - Enforces uniqueness of `(target_week, customer_idx, article_id)`.
    - Optionally drops all-zero label groups ONLY during training (`drop_all_zero_groups=True`), never during evaluation.
    """
    required_cols = {"customer_idx"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"DataFrame missing required columns: {required_cols - set(df.columns)}")

    work_df = df.copy()
    if "target_week" not in work_df.columns:
        work_df["target_week"] = 0

    sort_cols = ["target_week", "customer_idx"]
    if "article_id" in work_df.columns:
        dup_mask = work_df.duplicated(subset=["target_week", "customer_idx", "article_id"])
        if bool(dup_mask.any()):
            raise ValueError(
                "Duplicate candidate rows detected for the same (target_week, customer_idx, article_id)."
            )
        sort_cols.append("article_id")

    sorted_df = work_df.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)

    if drop_all_zero_groups and "label" in sorted_df.columns:
        pos_sums = sorted_df.groupby(["target_week", "customer_idx"], sort=False)["label"].transform("sum")
        sorted_df = sorted_df.loc[pos_sums > 0].reset_index(drop=True)

    if len(sorted_df) == 0:
        return sorted_df, np.zeros(0, dtype=np.int32)

    groups = (
        sorted_df.groupby(["target_week", "customer_idx"], sort=False)
        .size()
        .to_numpy(dtype=np.int32)
    )
    if int(groups.sum()) != len(sorted_df):
        raise RuntimeError(
            f"Group size sum ({int(groups.sum())}) != number of candidate rows ({len(sorted_df)})."
        )
    return sorted_df, groups


class UnifiedLGBMRanker:
    """Single LightGBM LambdaRank model used identically in offline evaluation and FastAPI online serving."""

    def __init__(self, model_path: str | Path | None = None) -> None:
        self.cfg: dict[str, Any] = get_model_config()["recsys"]["lightgbm"]
        self.model_path = Path(model_path) if model_path else None
        self.booster: Any = None

    def train(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        feature_cols: list[str] | None = None,
        drop_all_zero_train_groups: bool = False,
    ) -> Any:
        """Train LightGBM LambdaRank grouped by `(target_week, customer_idx)` (Active Users only)."""
        import lightgbm as lgb

        feats = feature_cols or FEATURE_COLUMNS
        cat_cols = [c for c in CATEGORICAL_FEATURES if c in feats]

        train_sorted, train_groups = prepare_lgbm_query_frame(
            train_df, drop_all_zero_groups=drop_all_zero_train_groups
        )
        val_sorted, val_groups = prepare_lgbm_query_frame(val_df, drop_all_zero_groups=False)

        dtrain = lgb.Dataset(
            train_sorted[feats],
            label=train_sorted["label"].to_numpy(),
            group=train_groups,
            categorical_feature=cat_cols,
        )
        dval = lgb.Dataset(
            val_sorted[feats],
            label=val_sorted["label"].to_numpy(),
            group=val_groups,
            categorical_feature=cat_cols,
            reference=dtrain,
        )

        params = {
            "objective": self.cfg["objective"],
            "metric": self.cfg["metric"],
            "ndcg_eval_at": self.cfg["ndcg_eval_at"],
            "boosting_type": self.cfg["boosting_type"],
            "num_leaves": self.cfg["num_leaves"],
            "learning_rate": self.cfg["learning_rate"],
            "colsample_bytree": self.cfg["colsample_bytree"],
            "subsample": self.cfg["subsample"],
            "random_state": self.cfg["random_state"],
            "n_jobs": self.cfg["n_jobs"],
            "verbose": -1,
        }

        self.booster = lgb.train(
            params=params,
            train_set=dtrain,
            num_boost_round=self.cfg["n_estimators"],
            valid_sets=[dval],
            callbacks=[lgb.early_stopping(self.cfg["early_stopping_rounds"], verbose=False)],
        )
        if self.model_path:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            self.booster.save_model(str(self.model_path))
        return self.booster

    def load(self) -> None:
        """Load saved LightGBM Booster into memory."""
        import lightgbm as lgb

        if not self.model_path or not self.model_path.exists():
            raise FileNotFoundError(f"LightGBM model file not found: {self.model_path}")
        self.booster = lgb.Booster(model_file=str(self.model_path))

    def predict_scores(
        self, candidates_df: pd.DataFrame, feature_cols: list[str] | None = None
    ) -> np.ndarray:
        """Score a candidate DataFrame in < 5ms for online or offline ranking."""
        if self.booster is None:
            self.load()
        feats = feature_cols or FEATURE_COLUMNS
        return np.asarray(self.booster.predict(candidates_df[feats]), dtype=np.float32)
