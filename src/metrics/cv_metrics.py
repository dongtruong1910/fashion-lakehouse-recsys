"""Computer Vision evaluation metrics: Recall@K, Precision@K, CatConsistency@K, nDCG@K, and Cohen's Kappa."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np


def dcg_at_k(relevances: Sequence[float | int], k: int = 10) -> float:
    """Compute Discounted Cumulative Gain at K using graded relevance scores $r_i \\in \\{0, 1, 2, 3\\}$:
    $$\\text{DCG}@K = \\sum_{i=1}^{K} \\frac{2^{r_i} - 1}{\\log_2(i + 1)}$$
    """
    rel_k = list(relevances)[:k]
    score = 0.0
    for idx, rel in enumerate(rel_k, start=1):
        score += (2.0 ** float(rel) - 1.0) / math.log2(idx + 1.0)
    return score


def ndcg_at_k(
    predicted_relevances: Sequence[float | int],
    ideal_relevances: Sequence[float | int] | None = None,
    k: int = 10,
) -> float:
    """Compute Normalized Discounted Cumulative Gain at K (nDCG@K) for graded relevance (0-3).

    Args:
        predicted_relevances: Relevance scores (e.g., [3, 2, 0, 1, ...]) in the order returned by the model.
        ideal_relevances: Optional full pool of relevance scores for the query (for Pooled Evaluation).
            If None, uses sorted `predicted_relevances`.
        k: Cutoff rank (default 10).
    """
    pool = list(ideal_relevances) if ideal_relevances is not None else list(predicted_relevances)
    ideal_sorted = sorted(pool, reverse=True)
    idcg = dcg_at_k(ideal_sorted, k=k)
    if idcg <= 0.0:
        return 0.0
    return dcg_at_k(predicted_relevances, k=k) / idcg


def cat_consistency_at_k(
    retrieved_product_types: Sequence[str],
    allowed_product_types: set[str] | Sequence[str],
    k: int = 10,
) -> float:
    """Compute Category Consistency@K (Proxy Street-to-Shop metric on Fashionpedia crops).

    Measures the fraction of top-K retrieved H&M catalog items whose `product_type_name`
    belongs to the valid H&M product types mapped from the query crop's ground-truth garment class.
    """
    top_k = list(retrieved_product_types)[:k]
    if not top_k:
        return 0.0
    allowed = set(allowed_product_types)
    hits = sum(1 for pt in top_k if pt in allowed)
    return hits / len(top_k)


def cohens_kappa_score(rater_a: Sequence[int], rater_b: Sequence[int]) -> float:
    """Compute Cohen's Kappa inter-annotator agreement for graded relevance ratings."""
    if len(rater_a) != len(rater_b) or len(rater_a) == 0:
        raise ValueError("Rater sequences must be non-empty and have equal length.")
    a = np.asarray(rater_a, dtype=int)
    b = np.asarray(rater_b, dtype=int)
    n = len(a)
    p_o = float(np.mean(a == b))

    labels = np.union1d(a, b)
    p_e = 0.0
    for lbl in labels:
        p_a = float(np.sum(a == lbl)) / n
        p_b = float(np.sum(b == lbl)) / n
        p_e += p_a * p_b

    if abs(1.0 - p_e) < 1e-12:
        return 1.0
    return (p_o - p_e) / (1.0 - p_e)
