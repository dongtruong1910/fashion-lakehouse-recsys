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
    ) -> None:
        super().__init__()
        self.mode = mode
        self.item_id_emb = nn.Embedding(num_items + 1, embed_dim, padding_idx=0)

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
    ) -> torch.Tensor:
        parts = [self.item_id_emb(item_idx)]
        if self.mode in ("id_plus_meta", "id_meta_visual"):
            if ptype_idx is None or colour_idx is None:
                raise ValueError("ptype_idx and colour_idx are required for metadata modes.")
            parts.append(self.ptype_emb(ptype_idx))
            parts.append(self.colour_emb(colour_idx))

        if self.mode == "id_meta_visual":
            vis_feat = self.visual_proj(self.visual_table(item_idx))
            parts.append(vis_feat)

        x = torch.cat(parts, dim=-1)
        out = self.mlp(x)
        return F.normalize(out, p=2, dim=-1)


class UserTower(nn.Module):
    """Encodes a user's recent N=15 item sequence + age bucket into a 64-d L2-normalized vector."""

    def __init__(self, embed_dim: int = 64, num_age_buckets: int = 5, num_heads: int = 2) -> None:
        super().__init__()
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
    ) -> torch.Tensor:
        """Compute L2-normalized user representation.

        Args:
            history_item_vecs: Tensor of shape (B, N, D) from ItemTower.
            history_padding_mask: Bool tensor of shape (B, N), True where padded (0).
            age_bucket_idx: Long tensor of shape (B,).
        """
        attn_out, _ = self.attn(
            history_item_vecs,
            history_item_vecs,
            history_item_vecs,
            key_padding_mask=history_padding_mask,
        )
        valid_mask = (~history_padding_mask).unsqueeze(-1).to(attn_out.dtype)
        denom = valid_mask.sum(dim=1).clamp(min=1.0)
        pooled = (attn_out * valid_mask).sum(dim=1) / denom

        x = torch.cat([pooled, self.age_emb(age_bucket_idx)], dim=-1)
        out = self.mlp(x)
        return F.normalize(out, p=2, dim=-1)
