"""Fast GPU-accelerated Visual Affinity Feature Calculator (`visual_affinity_score`).

Solves Technical Bottleneck #1 in `docs/ke_hoach_ban_dau/nhan_xet_va_chinh_sua_plan_v2.md`:
Instead of running a slow PySpark UDF over 7,000,000 (customer_idx, article_id) candidate pairs,
this module loads the 105,542 x D L2-normalized image embedding matrix (~162 MB in FP16) onto the
RTX 4060 GPU and computes $\\cos(\\mathbf{v}_{\\text{item}}, \\overline{\\mathbf{v}}_{\\text{user\\_recent\\_5}})$
in batched tensor operations in < 3 seconds.
"""

from __future__ import annotations

import numpy as np


def compute_visual_affinity_batch_numpy_or_torch(
    item_embeddings: np.ndarray,
    user_recent_item_indices: np.ndarray,
    user_recent_mask: np.ndarray,
    candidate_user_rows: np.ndarray,
    candidate_item_indices: np.ndarray,
    batch_size: int = 262_144,
    device: str = "cuda",
) -> np.ndarray:
    """Compute cosine similarity between each candidate item and the user's mean recent-5 visual vector.

    Args:
        item_embeddings: L2-normalized float32 matrix of shape (num_items, embed_dim).
        user_recent_item_indices: Int32 array of shape (num_active_users, K_recent) holding recent item indices.
        user_recent_mask: Float32 binary mask of shape (num_active_users, K_recent), 1.0 for valid history items.
        candidate_user_rows: Int32 array of shape (num_pairs,) indexing into `user_recent_item_indices`.
        candidate_item_indices: Int32 array of shape (num_pairs,) indexing into `item_embeddings`.
        batch_size: Number of pairs processed per GPU batch.
        device: 'cuda' or 'cpu'.

    Returns:
        Float32 array of shape (num_pairs,) containing `visual_affinity_score` in [-1.0, 1.0].
    """
    try:
        import torch

        use_cuda = device == "cuda" and torch.cuda.is_available()
        dev = torch.device("cuda" if use_cuda else "cpu")

        with torch.inference_mode():
            emb_t = torch.as_tensor(item_embeddings, dtype=torch.float32, device=dev)
            hist_idx_t = torch.as_tensor(user_recent_item_indices, dtype=torch.long, device=dev)
            mask_t = torch.as_tensor(user_recent_mask, dtype=torch.float32, device=dev).unsqueeze(-1)

            # Compute L2-normalized mean visual taste vector per active user: (U, D)
            hist_vecs = emb_t[hist_idx_t] * mask_t  # (U, K, D)
            user_mean_vecs = hist_vecs.sum(dim=1)
            norms = user_mean_vecs.norm(p=2, dim=-1, keepdim=True).clamp(min=1e-12)
            has_hist = (mask_t.sum(dim=1) > 0).to(torch.float32)
            user_mean_vecs = (user_mean_vecs / norms) * has_hist

            n_pairs = len(candidate_user_rows)
            out = np.zeros(n_pairs, dtype=np.float32)

            for start in range(0, n_pairs, batch_size):
                end = min(start + batch_size, n_pairs)
                u_idx = torch.as_tensor(candidate_user_rows[start:end], dtype=torch.long, device=dev)
                i_idx = torch.as_tensor(
                    candidate_item_indices[start:end], dtype=torch.long, device=dev
                )
                scores = (user_mean_vecs[u_idx] * emb_t[i_idx]).sum(dim=-1)
                out[start:end] = scores.cpu().numpy()

            return out
    except ImportError:
        # Pure NumPy fallback if PyTorch is not installed in the current environment
        hist_vecs = item_embeddings[user_recent_item_indices] * user_recent_mask[..., None]
        user_mean = hist_vecs.sum(axis=1)
        norms = np.linalg.norm(user_mean, axis=-1, keepdims=True)
        valid = (user_recent_mask.sum(axis=1, keepdims=True) > 0).astype(np.float32)
        user_mean = (user_mean / np.maximum(norms, 1e-12)) * valid
        return np.sum(
            user_mean[candidate_user_rows] * item_embeddings[candidate_item_indices], axis=-1
        ).astype(np.float32)
