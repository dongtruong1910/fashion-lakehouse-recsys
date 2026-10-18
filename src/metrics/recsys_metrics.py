"""Official Kaggle H&M Recommendation Metrics: AP@K, MAP@12, Recall@K, and Candidate Recall@K.

Formula for H&M MAP@12:
$$\\text{MAP}@12 = \\frac{1}{|U|} \\sum_{u=1}^{|U|} \\frac{1}{\\min(m_u, 12)} \\sum_{k=1}^{\\min(n_u, 12)} P(k) \\cdot \\text{rel}(k)$$
where $m_u > 0$ is the number of ground-truth items purchased by customer $u$ in the validation week,
$n_u$ is the number of predicted items, and duplicate predictions are only counted once at their first rank.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence


def ap_at_k(actual: Sequence[str] | set[str], predicted: Sequence[str], k: int = 12) -> float:
    """Compute Average Precision at K (AP@K) for a single customer according to Kaggle H&M rules.

    Args:
        actual: Ground-truth article_ids purchased by the customer in the target week.
        predicted: Ordered list of predicted article_ids (highest rank first).
        k: Cutoff rank (default 12 for H&M competition).

    Returns:
        AP@K score in [0.0, 1.0]. Returns 0.0 if `actual` is empty.
    """
    actual_set = set(actual)
    if not actual_set:
        return 0.0

    preds_k = list(predicted)[:k]
    score = 0.0
    num_hits = 0.0
    seen: set[str] = set()

    for idx, item in enumerate(preds_k, start=1):
        if item in actual_set and item not in seen:
            seen.add(item)
            num_hits += 1.0
            score += num_hits / idx

    return score / min(len(actual_set), k)


def map_at_k(
    ground_truth: Mapping[str | int, Iterable[str]],
    predictions: Mapping[str | int, Sequence[str]],
    k: int = 12,
) -> float:
    """Compute Mean Average Precision at K (MAP@K) across all customers with purchases in ground_truth.

    Note: Per Kaggle H&M rules, only customers who made at least 1 purchase in the validation
    period are included in the denominator $|U|$.
    """
    gt_sets: dict[str | int, set[str]] = {u: set(items) for u, items in ground_truth.items()}
    valid_users = [u for u, item_set in gt_sets.items() if len(item_set) > 0]
    if not valid_users:
        return 0.0

    total_ap = 0.0
    for u in valid_users:
        user_preds = predictions.get(u, [])
        total_ap += ap_at_k(gt_sets[u], user_preds, k=k)

    return total_ap / len(valid_users)


def recall_at_k(actual: Iterable[str], predicted: Sequence[str], k: int = 12) -> float:
    """Compute Recall@K for a single customer."""
    actual_set = set(actual)
    if not actual_set:
        return 0.0
    preds_k = set(list(predicted)[:k])
    return len(actual_set & preds_k) / len(actual_set)


def candidate_recall_at_k(
    ground_truth: Mapping[str | int, Iterable[str]],
    candidates: Mapping[str | int, Sequence[str]],
    k: int = 100,
) -> float:
    """Compute mean Candidate Recall@K — the upper bound ceiling for the second-stage ranker.

    Materializes each customer's ground-truth iterable once so one-shot iterators are never exhausted (Finding A18).
    """
    gt_sets: dict[str | int, set[str]] = {u: set(items) for u, items in ground_truth.items()}
    valid_users = [u for u, item_set in gt_sets.items() if len(item_set) > 0]
    if not valid_users:
        return 0.0

    recalls = [recall_at_k(gt_sets[u], candidates.get(u, []), k=k) for u in valid_users]
    return sum(recalls) / len(recalls)
