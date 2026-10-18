"""Unit tests verifying Golden Rules: 10-char article_id padding, Data Contracts, MAP@12, nDCG@10, and GPU Visual Affinity.

Compatible with both `pytest` and standard library `python -m unittest`.
"""

from __future__ import annotations

import unittest

import numpy as np
from PIL import Image

from scripts.resize_hm_aspect_pad import resize_with_white_padding
from src.contracts.schemas import FashionEvent, QdrantProductPayload
from src.cv.embedder import build_hm_article_caption, compose_image_text_vector
from src.metrics.cv_metrics import cat_consistency_at_k, cohens_kappa_score, ndcg_at_k
from src.metrics.recsys_metrics import ap_at_k, candidate_recall_at_k, map_at_k, recall_at_k
from src.recsys.baselines import merge_candidate_sources
from src.recsys.features_gpu import compute_visual_affinity_batch_numpy_or_torch
from src.streaming.event_simulator import build_fashion_event
from src.utils.config import (
    get_class_mapping_config,
    get_model_config,
    get_paths_config,
    get_spark_config,
)
from src.utils.id_utils import (
    article_id_to_qdrant_point_id,
    article_id_to_rel_image_path,
    extract_product_code,
    normalize_article_id,
    qdrant_point_id_to_article_id,
)


class TestCoreContractsAndMetrics(unittest.TestCase):
    def test_normalize_article_id_preserves_leading_zero(self) -> None:
        self.assertEqual(normalize_article_id(108775015), "0108775015")
        self.assertEqual(normalize_article_id("108775015"), "0108775015")
        self.assertEqual(normalize_article_id("0108775015"), "0108775015")
        self.assertEqual(normalize_article_id("108775015.0"), "0108775015")
        self.assertEqual(extract_product_code(108775015), "0108775")
        self.assertEqual(article_id_to_rel_image_path(108775015), "010/0108775015.jpg")

        pt_id = article_id_to_qdrant_point_id("0108775015")
        self.assertEqual(pt_id, 108775015)
        self.assertEqual(qdrant_point_id_to_article_id(pt_id), "0108775015")

        with self.assertRaises(ValueError):
            normalize_article_id("abc123")

    def test_map_at_12_exact_kaggle_behavior(self) -> None:
        # Single customer: bought 2 items ('A', 'B'), predicted ['A', 'X', 'B', 'A']
        # Hit 1 at rank 1 (P@1 = 1.0), Hit 2 at rank 3 (P@3 = 2/3), duplicate 'A' at rank 4 ignored.
        # AP@12 = (1.0 + 2/3) / min(2, 12) = 5/6
        ap = ap_at_k(["A", "B"], ["A", "X", "B", "A"], k=12)
        self.assertAlmostEqual(ap, 5.0 / 6.0, places=6)

        # Customers with empty ground-truth purchases are excluded from MAP@12 denominator
        gt = {
            "u1": ["A", "B"],
            "u2": ["C"],
            "u3_inactive": [],
        }
        preds = {
            "u1": ["A", "X", "B"],
            "u2": ["Y", "C"],
            "u3_inactive": ["A", "B"],
        }
        # u1 AP = 5/6, u2 AP = 0.5 -> MAP = (5/6 + 1/2) / 2 = 2/3
        self.assertAlmostEqual(map_at_k(gt, preds, k=12), 2.0 / 3.0, places=6)
        self.assertAlmostEqual(recall_at_k(["A", "B"], ["A", "X"], k=12), 0.5, places=6)
        self.assertAlmostEqual(candidate_recall_at_k(gt, preds, k=100), 1.0, places=6)

    def test_cv_metrics_ndcg_cat_consistency_and_kappa(self) -> None:
        self.assertAlmostEqual(ndcg_at_k([3, 2, 1, 0], k=10), 1.0, places=6)
        imperfect = ndcg_at_k([0, 2, 3, 1], k=10)
        self.assertTrue(0.0 < imperfect < 1.0)

        consistency = cat_consistency_at_k(
            ["Trousers", "Vest top", "Trousers", "Boots"],
            allowed_product_types={"Trousers", "Outdoor trousers"},
            k=4,
        )
        self.assertAlmostEqual(consistency, 0.5, places=6)

        kappa = cohens_kappa_score([3, 2, 1, 0, 3, 2], [3, 2, 1, 0, 3, 2])
        self.assertAlmostEqual(kappa, 1.0, places=6)

    def test_gpu_visual_affinity_and_candidate_merging(self) -> None:
        item_embs = np.array(
            [
                [1.0, 0.0],
                [1.0, 0.0],
                [0.0, 1.0],
                [-1.0, 0.0],
            ],
            dtype=np.float32,
        )
        user_recent = np.array([[0, 1]], dtype=np.int32)
        user_mask = np.array([[1.0, 1.0]], dtype=np.float32)
        cand_users = np.array([0, 0, 0], dtype=np.int32)
        cand_items = np.array([1, 2, 3], dtype=np.int32)

        scores = compute_visual_affinity_batch_numpy_or_torch(
            item_embeddings=item_embs,
            user_recent_item_indices=user_recent,
            user_recent_mask=user_mask,
            candidate_user_rows=cand_users,
            candidate_item_indices=cand_items,
            device="cpu",
        )
        np.testing.assert_allclose(
            scores, np.array([1.0, 0.0, -1.0], dtype=np.float32), atol=1e-5
        )

        merged = merge_candidate_sources(
            repurchase_items=["0108775015", "0108775044"],
            cooccurrence_items=["0108775044", "0706016001"],
            age_popular_items=["0706016001"],
        )
        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[1]["article_id"], "0108775044")
        self.assertEqual(merged[1]["src_count"], 2)

    def test_configs_and_schemas_contract(self) -> None:
        self.assertIn("lakehouse", get_paths_config())
        self.assertEqual(len(get_class_mapping_config()["detector_classes"]), 12)
        self.assertIn("spark_conf", get_spark_config())
        self.assertIn("recsys", get_model_config())

        ev = build_fashion_event(customer_id="cust_demo", article_id=108775015, source="ui")
        self.assertIsInstance(ev, FashionEvent)
        self.assertEqual(ev.article_id, "0108775015")

        payload = QdrantProductPayload(
            article_id=108775015,
            product_code=108775,
            prod_name="Strap top",
            detector_class="top",
            product_type_name="Vest top",
            product_group_name="Garment Upper body",
            colour_group_name="Black",
            graphical_appearance_name="Solid",
            index_group_name="Ladieswear",
            price=0.0169,
            image_rel_path="010/0108775015.jpg",
        )
        self.assertEqual(payload.article_id, "0108775015")
        self.assertEqual(payload.product_code, "0108775")

        caption = build_hm_article_caption(payload.model_dump())
        self.assertIn("Black Solid Vest top", caption)

        v_comp = compose_image_text_vector(
            np.array([1.0, 0.0]), np.array([0.0, 1.0]), alpha=0.5
        )
        self.assertAlmostEqual(float(np.linalg.norm(v_comp)), 1.0, places=5)

        portrait_img = Image.new("RGB", (100, 200), color=(20, 40, 60))
        padded_img = resize_with_white_padding(portrait_img, target_size=(256, 256))
        self.assertEqual(padded_img.size, (256, 256))
        self.assertEqual(padded_img.getpixel((5, 128)), (255, 255, 255))

    def test_two_tower_all_ablation_modes(self) -> None:
        import torch

        from src.recsys.two_tower import ItemTower, UserTower

        num_items = 20
        vis_table = torch.randn(num_items + 1, 768)
        item_idx = torch.tensor([[1, 2, 0], [3, 4, 5]], dtype=torch.long)
        ptype_idx = torch.tensor([[1, 2, 0], [2, 3, 1]], dtype=torch.long)
        colour_idx = torch.tensor([[1, 1, 0], [2, 2, 3]], dtype=torch.long)
        pad_mask = item_idx == 0
        age_idx = torch.tensor([1, 2], dtype=torch.long)

        for mode in ("id_only", "id_plus_meta", "id_meta_visual"):
            itower = ItemTower(
                num_items=num_items,
                visual_embeddings=vis_table if mode == "id_meta_visual" else None,
                embed_dim=64,
                mode=mode,  # type: ignore[arg-type]
            )
            utower = UserTower(embed_dim=64)
            hist_vecs = itower(item_idx, ptype_idx, colour_idx)
            user_vecs = utower(hist_vecs, pad_mask, age_idx)
            self.assertEqual(tuple(user_vecs.shape), (2, 64))
            norms = torch.norm(user_vecs, p=2, dim=-1)
            self.assertTrue(torch.allclose(norms, torch.ones_like(norms), atol=1e-5))

    def test_a01_week_calendar_and_temporal_leakage_guard(self) -> None:
        from src.utils.id_utils import (
            date_to_hm_week_num,
            hm_week_num_to_date_range,
            validate_no_temporal_leakage,
        )

        # First H&M date 2018-09-20 is in week 0
        self.assertEqual(date_to_hm_week_num("2018-09-20"), 0)
        self.assertEqual(date_to_hm_week_num("2020-09-08"), 102)

        # Dev Week 103: all 7 days 2020-09-09 .. 2020-09-15 must map to 103
        for day in range(9, 16):
            self.assertEqual(date_to_hm_week_num(f"2020-09-{day:02d}"), 103)

        # Final Test Week 104: all 7 days 2020-09-16 .. 2020-09-22 must map to 104 (fixes A01!)
        for day in range(16, 23):
            self.assertEqual(date_to_hm_week_num(f"2020-09-{day:02d}"), 104)

        w104_start, w104_end = hm_week_num_to_date_range(104)
        self.assertEqual(w104_start.isoformat(), "2020-09-16")
        self.assertEqual(w104_end.isoformat(), "2020-09-22")

        # Feature cutoff strictly before target week start passes; on/after raises ValueError
        validate_no_temporal_leakage("2020-09-15", target_week_num=104)
        with self.assertRaises(ValueError):
            validate_no_temporal_leakage("2020-09-16", target_week_num=104)

    def test_a02_lgbm_multi_week_query_grouping(self) -> None:
        import pandas as pd

        from src.recsys.lgbm_ranker import prepare_lgbm_query_frame

        # Same customer_idx=7 across two target weeks (101 and 102), 2 candidates each -> groups must be [2, 2], NOT [4]
        df = pd.DataFrame(
            {
                "target_week": [101, 102, 101, 102],
                "customer_idx": [7, 7, 7, 7],
                "article_id": ["0108775015", "0108775015", "0108775044", "0108775044"],
                "label": [1, 0, 0, 1],
            }
        )
        sorted_df, groups = prepare_lgbm_query_frame(df)
        self.assertEqual(groups.tolist(), [2, 2])
        self.assertEqual(int(groups.sum()), len(sorted_df))

        # Duplicate (target_week, customer_idx, article_id) must raise ValueError
        dup_df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
        with self.assertRaises(ValueError):
            prepare_lgbm_query_frame(dup_df)

    def test_a03_smoke_path_isolation(self) -> None:
        from spark_jobs.batch.b0_ingest_bronze import resolve_bronze_output_path
        from spark_jobs.batch.b1_clean_silver import resolve_silver_io_paths

        paths = get_paths_config()
        prod_tx = paths["lakehouse"]["bronze"]["transactions"]
        smoke_tx = resolve_bronze_output_path(paths, smoke_test=True)
        self.assertNotEqual(smoke_tx, prod_tx)
        self.assertIn("lakehouse_smoke", smoke_tx)

        # Attempting to force smoke run onto production path must raise ValueError
        with self.assertRaises(ValueError):
            resolve_bronze_output_path(paths, smoke_test=True, output_override=prod_tx)

        silver_smoke = resolve_silver_io_paths(paths, smoke_test=True)
        silver_full = resolve_silver_io_paths(paths, smoke_test=False)
        self.assertNotEqual(silver_smoke["silver_tx"], silver_full["silver_tx"])
        self.assertEqual(silver_smoke["mapping_version"], "v1_smoke")
        self.assertEqual(silver_full["mapping_version"], "v1_full")

    def test_a04_detector_ontology_guard(self) -> None:
        from src.cv.detector import resolve_detector_class_from_model_names

        fashion12 = {int(k): v for k, v in get_class_mapping_config()["detector_classes"].items()}
        # COCO checkpoint where 0='person' must be rejected, never mapped to 'top'
        coco_names = {0: "person", 26: "handbag"}
        with self.assertRaises(RuntimeError):
            resolve_detector_class_from_model_names(0, coco_names, fashion12)

        # Valid fashion12 checkpoint maps cleanly
        self.assertEqual(resolve_detector_class_from_model_names(0, fashion12, fashion12), "top")
        self.assertEqual(resolve_detector_class_from_model_names(6, fashion12, fashion12), "shoe")

    def test_a05_and_a19_two_tower_empty_history_and_order_sensitivity(self) -> None:
        import torch

        from src.recsys.two_tower import ItemTower, UserTower

        torch.manual_seed(42)
        itower = ItemTower(
            num_items=20,
            visual_embeddings=torch.randn(21, 768),
            embed_dim=64,
            mode="id_meta_visual",
        )
        utower = UserTower(embed_dim=64)
        itower.eval()
        utower.eval()

        # Row 0: completely empty history (all padded=True). Row 1: valid history [1, 2, 3].
        item_idx = torch.tensor([[0, 0, 0], [1, 2, 3]], dtype=torch.long)
        ptype_idx = torch.tensor([[0, 0, 0], [1, 2, 3]], dtype=torch.long)
        colour_idx = torch.tensor([[0, 0, 0], [1, 2, 3]], dtype=torch.long)
        pad_mask = item_idx == 0
        age_idx = torch.tensor([1, 2], dtype=torch.long)

        hist_vecs = itower(item_idx, ptype_idx, colour_idx)
        user_vecs = utower(hist_vecs, pad_mask, age_idx)

        # Must be 100% finite (0 NaNs) and unit-normalized even for empty history!
        self.assertTrue(bool(torch.isfinite(user_vecs).all()))
        norms = torch.norm(user_vecs, p=2, dim=-1)
        self.assertTrue(torch.allclose(norms, torch.ones_like(norms), atol=1e-5))

        # Order/recency sensitivity check (Finding A19): [1, 2, 3] vs reversed [3, 2, 1] must differ!
        rev_idx = torch.tensor([[3, 2, 1]], dtype=torch.long)
        fwd_idx = torch.tensor([[1, 2, 3]], dtype=torch.long)
        v_fwd = utower(
            itower(fwd_idx, ptype_idx[1:], colour_idx[1:]),
            fwd_idx == 0,
            age_idx[1:],
        )
        v_rev = utower(
            itower(rev_idx, ptype_idx[1:], colour_idx[1:]),
            rev_idx == 0,
            age_idx[1:],
        )
        max_diff = float(torch.max(torch.abs(v_fwd - v_rev)).item())
        self.assertGreater(max_diff, 1e-3)

    def test_a06_and_a08_strict_schema_validation_and_replay_clock(self) -> None:
        # Invalid UUID, NaN price, invalid event_type, or arbitrary customer_id='x' must raise ValueError
        with self.assertRaises(ValueError):
            FashionEvent(
                event_id="not-a-uuid",
                event_time="2026-10-17T08:30:00Z",
                ingest_time="2026-10-17T08:30:00Z",
                customer_id="cust_demo",
                article_id="0108775015",
            )
        with self.assertRaises(ValueError):
            FashionEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                event_time="2026-10-17T08:30:00Z",
                ingest_time="2026-10-17T08:30:00Z",
                customer_id="x",
                article_id="0108775015",
            )
        with self.assertRaises(ValueError):
            FashionEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                event_time="2026-10-17T08:30:00Z",
                ingest_time="2026-10-17T08:30:00Z",
                customer_id="cust_demo",
                article_id="0108775015",
                price=float("nan"),
            )

        # QdrantProductPayload with mismatched product_code prefix must raise ValueError
        with self.assertRaises(ValueError):
            QdrantProductPayload(
                article_id="0108775015",
                product_code="9999999",
                prod_name="Strap top",
                detector_class="top",
                product_type_name="Vest top",
                product_group_name="Garment Upper body",
                colour_group_name="Black",
                graphical_appearance_name="Solid",
                index_group_name="Ladieswear",
            )

        # Replay event uses active UTC clock for event_time and preserves original_t_dat (Finding A08)
        hex64 = "000058a12d5b43e67d225668fa1f8d618c13dc232df0cad8ffe7ad4a1091e318"
        ev_replay = build_fashion_event(
            customer_id=hex64, article_id=108775015, date_str="2020-09-18", source="replay"
        )
        self.assertEqual(ev_replay.original_t_dat, "2020-09-18")
        self.assertEqual(ev_replay.event_time, ev_replay.ingest_time)

    def test_a09_a16_a17_a18_and_kappa_edge_cases(self) -> None:
        import math

        from spark_jobs.streaming.s1_stream_processor import record_session_event_idempotent
        from src.cv.embedder import get_text_tokenizer_kwargs
        from src.cv.qdrant_indexer import validate_existing_collection_params
        from src.metrics.cv_metrics import cohens_kappa_summary, i2i_precision_at_k

        # A18: One-shot iterator ground truth in candidate_recall_at_k and map_at_k must equal list ground truth
        self.assertAlmostEqual(
            candidate_recall_at_k({"u": iter(["0108775015"])}, {"u": ["0108775015"]}, k=10),
            1.0,
            places=6,
        )
        self.assertAlmostEqual(
            map_at_k({"u": iter(["0108775015"])}, {"u": ["0108775015"]}, k=12),
            1.0,
            places=6,
        )

        # Section 5.1: Degenerate zero-variance Cohen's Kappa returns NaN & undefined_zero_variance status
        self.assertTrue(math.isnan(cohens_kappa_score([3, 3, 3], [3, 3, 3])))
        summary = cohens_kappa_summary([3, 3, 3], [3, 3, 3])
        self.assertEqual(summary["status"], "undefined_zero_variance")
        self.assertAlmostEqual(float(summary["observed_agreement"]), 1.0, places=6)

        # A11: I2I Precision@K excludes the query article itself
        p_i2i = i2i_precision_at_k(
            query_article_id="0108775015",
            retrieved_article_ids=["0108775015", "0108775044", "0706016001"],
            relevant_article_ids={"0108775015", "0108775044"},
            k=2,
        )
        self.assertAlmostEqual(p_i2i, 0.5, places=6)

        # A17: SigLIP uses padding='max_length', max_length=64
        siglip_kw = get_text_tokenizer_kwargs("google/siglip2-base-patch16-224")
        self.assertEqual(siglip_kw["padding"], "max_length")
        self.assertEqual(siglip_kw["max_length"], 64)

        # A16: Qdrant dimension mismatch raises ValueError
        with self.assertRaises(ValueError):
            validate_existing_collection_params(
                {"visual_emb": {"size": 512}, "two_tower_emb": {"size": 64}},
                visual_dim=768,
                two_tower_dim=64,
            )

        # A09: Idempotent Redis session helper deduplicates duplicate event_id
        class _FakePipeline:
            def __init__(self, store: dict) -> None:
                self.store = store
                self.ops: list = []

            def lpush(self, k: str, v: str) -> None:
                self.ops.append(("lpush", k, v))

            def ltrim(self, k: str, start: int, end: int) -> None:
                self.ops.append(("ltrim", k, start, end))

            def expire(self, k: str, ttl: int) -> None:
                self.ops.append(("expire", k, ttl))

            def execute(self) -> None:
                for op in self.ops:
                    if op[0] == "lpush":
                        self.store.setdefault(op[1], []).insert(0, op[2])
                    elif op[0] == "ltrim":
                        self.store[op[1]] = self.store.get(op[1], [])[op[2] : op[3] + 1]

        class _FakeRedis:
            def __init__(self) -> None:
                self.seen: set[str] = set()
                self.lists: dict[str, list[str]] = {}

            def set(self, key: str, val: str, nx: bool = False, ex: int = 0) -> bool:
                if nx and key in self.seen:
                    return False
                self.seen.add(key)
                return True

            def pipeline(self, transaction: bool = True) -> _FakePipeline:
                return _FakePipeline(self.lists)

        fake_r = _FakeRedis()
        first = record_session_event_idempotent(
            fake_r,
            event_id="550e8400-e29b-41d4-a716-446655440000",
            customer_id="cust_demo",
            article_id=108775015,
        )
        second = record_session_event_idempotent(
            fake_r,
            event_id="550e8400-e29b-41d4-a716-446655440000",
            customer_id="cust_demo",
            article_id=108775015,
        )
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(fake_r.lists["user:cust_demo:recent"], ["0108775015"])


if __name__ == "__main__":
    unittest.main()
