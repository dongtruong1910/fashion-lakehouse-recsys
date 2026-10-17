"""L0 & L1 Heuristic Recommendation Baselines and Candidate Merging Logic."""

from __future__ import annotations

from collections.abc import Sequence


def merge_candidate_sources(
    repurchase_items: Sequence[str],
    cooccurrence_items: Sequence[str],
    age_popular_items: Sequence[str],
    als_items: Sequence[str] = (),
    twotower_items: Sequence[str] = (),
    max_candidates: int = 100,
) -> list[dict[str, int | str]]:
    """Merge multi-source candidate lists for a user while tracking per-source ranks and source count.

    Preserves priority order and deduplicates `article_id` across all 5 candidate generators.
    """
    source_maps = {
        "src_repurchase_rank": {item: r for r, item in enumerate(repurchase_items, start=1)},
        "src_cooc_rank": {item: r for r, item in enumerate(cooccurrence_items, start=1)},
        "src_age_pop_rank": {item: r for r, item in enumerate(age_popular_items, start=1)},
        "src_als_rank": {item: r for r, item in enumerate(als_items, start=1)},
        "src_twotower_rank": {item: r for r, item in enumerate(twotower_items, start=1)},
    }

    ordered_unique: list[str] = []
    seen: set[str] = set()
    for seq in (
        repurchase_items,
        cooccurrence_items,
        twotower_items,
        als_items,
        age_popular_items,
    ):
        for item in seq:
            if item not in seen:
                seen.add(item)
                ordered_unique.append(item)
                if len(ordered_unique) >= max_candidates:
                    break
        if len(ordered_unique) >= max_candidates:
            break

    rows: list[dict[str, int | str]] = []
    for item in ordered_unique:
        src_count = 0
        row: dict[str, int | str] = {"article_id": item}
        for col_name, rank_map in source_maps.items():
            if item in rank_map:
                row[col_name] = rank_map[item]
                src_count += 1
            else:
                row[col_name] = 999
        row["src_count"] = src_count
        rows.append(row)
    return rows
