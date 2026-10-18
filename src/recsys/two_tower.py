"""L4 Deep Learning RecSys: Two-Tower Neural Retrieval Model with Frozen Visual Embeddings.

Solves Technical Bottleneck #2 in `docs/ke_hoach_ban_dau/nhan_xet_va_chinh_sua_plan_v2.md`:
- Uses sequence length `N = 15` (instead of 30) and a lightweight 1-layer Attention Pooling
  instead of a heavy multi-layer Transformer so training with batch_size=512 fits easily
  inside < 3.0 GB VRAM on the laptop RTX 4060 (8GB VRAM).
- Supports all 3 mandatory Ablation variants:
  1. `id_only`: Item represented only by learned `article_idx` embedding.
  2. `id_plus_meta`: Item represented by `article_idx` + `product_type` + `colour` embeddings.
  3. `id_meta_visual`: Item represented by ID + metadata + projected CLIP/SigLIP visual vector (solves Cold-Start Items!).
"""

from __future__ import annotations

from typing import Literal

import torch
import torch.nn as nn
import torch.nn.functional as F

AblationMode = Literal["id_only", "id_plus_meta", "id_meta_visual"]


class ItemTower(nn.Module):
    """Encodes an article into a 64-d L2-normalized vector using ID, metadata, and visual features."""

    def __init__(
        self,
        num_items: int,
        num_product_types: int = 140,
        num_colours: int = 60,
        visual_embeddings: torch.Tensor | None = None,
        embed_dim: int = 64,
        mode: AblationMode = "id_meta_visual",
        id_dropout_prob: float = 0.15,
    ) -> None:
        super().__init__()
        self.mode = mode
        self.id_dropout_prob = id_dropout_prob
        self.item_id_emb = nn.Embedding(num_items + 1, embed_dim, padding_idx=0)
        self.oov_item_emb = nn.Parameter(torch.randn(1, embed_dim) * 0.02)

        in_dim = embed_dim
        if mode in ("id_plus_meta", "id_meta_visual"):
            self.ptype_emb = nn.Embedding(num_product_types + 1, 16, padding_idx=0)
            self.colour_emb = nn.Embedding(num_colours + 1, 16, padding_idx=0)
            in_dim += 32

        if mode == "id_meta_visual":
            if visual_embeddings is None:
                raise ValueError("`visual_embeddings` tensor is required for mode='id_meta_visual'")
            self.visual_table = nn.Embedding.from_pretrained(
                visual_embeddings, freeze=True, padding_idx=0
            )
            vis_dim = visual_embeddings.shape[1]
            self.visual_proj = nn.Linear(vis_dim, embed_dim)
            in_dim += embed_dim

        self.mlp = nn.Sequential(
            nn.Linear(in_dim, embed_dim * 2),
            nn.GELU(),
            nn.Linear(embed_dim * 2, embed_dim),
        )

    def forward(
        self,
        item_idx: torch.Tensor,
        ptype_idx: torch.Tensor | None = None,
        colour_idx: torch.Tensor | None = None,
        visual_vec_override: torch.Tensor | None = None,
        is_cold_start_item: torch.Tensor | None = None,
    ) -> torch.Tensor:
        id_vec = self.item_id_emb(item_idx)
        # During training in content-aware modes, randomly drop item ID or use OOV token for cold-start items
        if self.mode in ("id_plus_meta", "id_meta_visual"):
            if is_cold_start_item is not None:
                cold_mask = is_cold_start_item.unsqueeze(-1).to(torch.bool)
                id_vec = torch.where(cold_mask, self.oov_item_emb.expand_as(id_vec), id_vec)
            elif self.training and self.id_dropout_prob > 0.0:
                drop_mask = (
                    torch.rand(item_idx.shape, device=item_idx.device) < self.id_dropout_prob
                ) & (item_idx > 0)
                id_vec = torch.where(
                    drop_mask.unsqueeze(-1), self.oov_item_emb.expand_as(id_vec), id_vec
                )

        parts = [id_vec]
        if self.mode in ("id_plus_meta", "id_meta_visual"):
            if ptype_idx is None or colour_idx is None:
                raise ValueError("ptype_idx and colour_idx are required for metadata modes.")
            parts.append(self.ptype_emb(ptype_idx))
            parts.append(self.colour_emb(colour_idx))

        if self.mode == "id_meta_visual":
            raw_vis = (
                visual_vec_override
                if visual_vec_override is not None
                else self.visual_table(item_idx)
            )
            vis_feat = self.visual_proj(raw_vis)
            parts.append(vis_feat)

        x = torch.cat(parts, dim=-1)
        out = self.mlp(x)
        # Zero out strictly padded sequence slots (where item_idx == 0 and no override is provided)
        if visual_vec_override is None:
            non_pad = (item_idx != 0)
            if is_cold_start_item is not None:
                non_pad = non_pad | is_cold_start_item.to(torch.bool)
            out = F.normalize(out, p=2, dim=-1, eps=1e-12) * non_pad.unsqueeze(-1).to(out.dtype)
            return out
        return F.normalize(out, p=2, dim=-1, eps=1e-12)


class UserTower(nn.Module):
    """Encodes a user's recent N=15 item sequence + recency + age bucket into a 64-d L2-normalized vector."""

    def __init__(
        self,
        embed_dim: int = 64,
        num_age_buckets: int = 5,
        num_heads: int = 2,
        max_seq_len: int = 15,
        decay_lambda: float = 0.15,
    ) -> None:
        super().__init__()
        self.max_seq_len = max_seq_len
        self.decay_lambda = decay_lambda
        self.pos_emb = nn.Embedding(max_seq_len, embed_dim)
        self.empty_history_emb = nn.Parameter(torch.randn(1, embed_dim) * 0.02)
        self.attn = nn.MultiheadAttention(
            embed_dim=embed_dim, num_heads=num_heads, dropout=0.1, batch_first=True
        )
        self.age_emb = nn.Embedding(num_age_buckets + 1, 16, padding_idx=0)
        self.mlp = nn.Sequential(
            nn.Linear(embed_dim + 16, embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, embed_dim),
        )

    def forward(
        self,
        history_item_vecs: torch.Tensor,
        history_padding_mask: torch.Tensor,
        age_bucket_idx: torch.Tensor,
        history_decay_days: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Compute L2-normalized user representation with position/time-decay and safe empty-history fallback.

        Args:
            history_item_vecs: Tensor of shape (B, N, D) from ItemTower (index 0 = most recent item).
            history_padding_mask: Bool tensor of shape (B, N), True where padded (0).
            age_bucket_idx: Long tensor of shape (B,).
            history_decay_days: Optional float tensor of shape (B, N) with days elapsed since purchase.
        """
        bsz, seq_len, _ = history_item_vecs.shape
        pos_ids = torch.arange(seq_len, device=history_item_vecs.device).clamp(
            max=self.max_seq_len - 1
        )
        seq_input = history_item_vecs + self.pos_emb(pos_ids).unsqueeze(0)

        # Prevent NaN in MultiheadAttention when an entire row of history_padding_mask is True (Finding A05)
        all_empty = history_padding_mask.all(dim=1)  # (B,)
        safe_key_mask = history_padding_mask.clone()
        if bool(all_empty.any()):
            safe_key_mask[all_empty, 0] = False

        attn_out, _ = self.attn(
            seq_input,
            seq_input,
            seq_input,
            key_padding_mask=safe_key_mask,
        )

        # Recency time-decay weights: either explicit elapsed days or rank-based exponential decay
        if history_decay_days is not None:
            recency_w = torch.exp(-self.decay_lambda * history_decay_days.clamp(min=0.0))
        else:
            rank_steps = pos_ids.to(attn_out.dtype).unsqueeze(0).expand(bsz, seq_len)
            recency_w = torch.exp(-self.decay_lambda * rank_steps)

        valid_weights = (recency_w * (~history_padding_mask).to(attn_out.dtype)).unsqueeze(-1)
        denom = valid_weights.sum(dim=1).clamp(min=1e-12)
        pooled = (attn_out * valid_weights).sum(dim=1) / denom

        # Replace empty-history rows with learned cold-start user embedding
        if bool(all_empty.any()):
            pooled = torch.where(
                all_empty.unsqueeze(-1),
                self.empty_history_emb.to(pooled.dtype).expand_as(pooled),
                pooled,
            )

        x = torch.cat([pooled, self.age_emb(age_bucket_idx)], dim=-1)
        out = self.mlp(x)
        return F.normalize(out, p=2, dim=-1, eps=1e-12)
