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


if __name__ == "__main__":
    unittest.main()
