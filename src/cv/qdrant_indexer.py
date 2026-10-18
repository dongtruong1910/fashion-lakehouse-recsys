"""Stage 3 CV: Qdrant Vector Database Collection Manager & Filtered ANN Search (`hm_products`)."""

from __future__ import annotations

import os
from typing import Any

from src.contracts.schemas import QdrantProductPayload
from src.utils.id_utils import article_id_to_qdrant_point_id


def validate_existing_collection_params(
    vectors_cfg: dict[str, Any],
    visual_dim: int = 768,
    two_tower_dim: int = 64,
) -> None:
    """Verify that an existing Qdrant collection's named vectors match expected dimensions and metrics (A16)."""
    if "visual_emb" not in vectors_cfg or "two_tower_emb" not in vectors_cfg:
        raise ValueError(
            f"Existing Qdrant collection is missing required named vectors ('visual_emb', 'two_tower_emb'): "
            f"found {list(vectors_cfg.keys())}."
        )
    vis_param = vectors_cfg["visual_emb"]
    tt_param = vectors_cfg["two_tower_emb"]

    vis_size = int(getattr(vis_param, "size", vis_param.get("size") if isinstance(vis_param, dict) else -1))
    tt_size = int(getattr(tt_param, "size", tt_param.get("size") if isinstance(tt_param, dict) else -1))
    if vis_size != int(visual_dim):
        raise ValueError(
            f"Qdrant collection dimension mismatch (Finding A16): existing visual_emb.size={vis_size} "
            f"!= requested visual_dim={visual_dim}. Recreate or version the collection for the new encoder."
        )
    if tt_size != int(two_tower_dim):
        raise ValueError(
            f"Qdrant collection dimension mismatch (Finding A16): existing two_tower_emb.size={tt_size} "
            f"!= requested two_tower_dim={two_tower_dim}."
        )


class QdrantCatalogStore:
    """Manages the `hm_products` Qdrant collection with dual named vectors (`visual_emb`, `two_tower_emb`)."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        collection_name: str | None = None,
    ) -> None:
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = int(port or os.getenv("QDRANT_PORT", "6333"))
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION", "hm_products")
        self._client: Any = None

    @property
    def client(self) -> Any:
        if self._client is None:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(host=self.host, port=self.port)
        return self._client

    def ensure_collection(
        self,
        visual_dim: int = 768,
        two_tower_dim: int = 64,
        enable_int8_quantization: bool = True,
    ) -> None:
        """Create `hm_products` collection with named vectors and payload indexes, or verify existing compatibility."""
        from qdrant_client.http import models as qmodels

        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection_name in existing:
            info = self.client.get_collection(self.collection_name)
            vec_cfg = info.config.params.vectors
            if isinstance(vec_cfg, dict):
                validate_existing_collection_params(
                    vec_cfg, visual_dim=visual_dim, two_tower_dim=two_tower_dim
                )
            else:
                raise ValueError(
                    f"Existing Qdrant collection '{self.collection_name}' does not use Named Vectors."
                )
            return

        quant_cfg = (
            qmodels.ScalarQuantization(
                scalar=qmodels.ScalarQuantizationConfig(
                    type=qmodels.ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True,
                )
            )
            if enable_int8_quantization
            else None
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                "visual_emb": qmodels.VectorParams(
                    size=visual_dim, distance=qmodels.Distance.COSINE
                ),
                "two_tower_emb": qmodels.VectorParams(
                    size=two_tower_dim, distance=qmodels.Distance.DOT
                ),
            },
            quantization_config=quant_cfg,
        )

        for field in (
            "detector_class",
            "product_type_name",
            "colour_group_name",
            "index_group_name",
            "encoder_model_id",
        ):
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field,
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )

    @staticmethod
    def build_point_struct(
        payload: QdrantProductPayload,
        visual_vec: list[float],
        two_tower_vec: list[float] | None = None,
    ) -> Any:
        """Build a Qdrant PointStruct enforcing the integer point ID and schema contract."""
        from qdrant_client.http import models as qmodels

        vectors: dict[str, list[float]] = {"visual_emb": visual_vec}
        if two_tower_vec is not None:
            vectors["two_tower_emb"] = two_tower_vec

        return qmodels.PointStruct(
            id=article_id_to_qdrant_point_id(payload.article_id),
            vector=vectors,
            payload=payload.model_dump(),
        )
