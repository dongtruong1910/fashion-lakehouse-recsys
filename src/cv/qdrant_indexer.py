"""Stage 3 CV: Qdrant Vector Database Collection Manager & Filtered ANN Search (`hm_products`)."""

from __future__ import annotations

import os
from typing import Any

from src.contracts.schemas import QdrantProductPayload
from src.utils.id_utils import article_id_to_qdrant_point_id


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
        """Create `hm_products` collection with named vectors and payload indexes if it does not exist."""
        from qdrant_client.http import models as qmodels

        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection_name in existing:
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
