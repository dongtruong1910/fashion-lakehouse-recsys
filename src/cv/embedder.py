"""Stage 2 CV: Multimodal Image & Text Embedder (CLIP, SigLIP-2, FashionCLIP) with L2 Normalization."""

from __future__ import annotations

import numpy as np
from PIL import Image

from src.utils.config import get_model_config


def build_hm_article_caption(row: dict[str, str]) -> str:
    """Construct concise English product description for H&M articles (Section 5.1.5).

    Kept concise to fit within the 64-token context window of SigLIP/CLIP text encoders.
    """
    colour = str(row.get("colour_group_name", "")).strip()
    appearance = str(row.get("graphical_appearance_name", "")).strip()
    ptype = str(row.get("product_type_name", "")).strip()
    idx_group = str(row.get("index_group_name", "")).strip()
    desc = str(row.get("detail_desc", "")).strip()
    if len(desc) > 140:
        desc = desc[:140].rsplit(" ", 1)[0]
    return f"{colour} {appearance} {ptype}, {idx_group}. {desc}".strip()


def compose_image_text_vector(
    image_vec: np.ndarray,
    text_vec: np.ndarray | None = None,
    alpha: float = 0.75,
) -> np.ndarray:
    """Blend L2-normalized image and text vectors for Composed Image Retrieval:
    $$\\mathbf{v}_{\\text{query}} = \\text{normalize}(\\alpha \\mathbf{v}_{\\text{img}} + (1 - \\alpha) \\mathbf{v}_{\\text{text}})$$
    """
    img_norm = image_vec / (np.linalg.norm(image_vec, axis=-1, keepdims=True) + 1e-12)
    if text_vec is None:
        return img_norm.astype(np.float32)
    txt_norm = text_vec / (np.linalg.norm(text_vec, axis=-1, keepdims=True) + 1e-12)
    blended = alpha * img_norm + (1.0 - alpha) * txt_norm
    blended = blended / (np.linalg.norm(blended, axis=-1, keepdims=True) + 1e-12)
    return blended.astype(np.float32)


def get_text_tokenizer_kwargs(model_id: str, spec: dict[str, object] | None = None) -> dict[str, object]:
    """Return checkpoint-appropriate text tokenization arguments (Finding A17).

    SigLIP / SigLIP-2 models were pretrained with fixed `padding="max_length"` (64 tokens),
    whereas CLIP models use `padding=True` (or longest in batch, up to 77 tokens).
    """
    is_siglip = "siglip" in model_id.lower()
    default_padding = "max_length" if is_siglip else True
    default_max_len = 64 if is_siglip else 77

    if spec:
        cfg_pad = spec.get("text_padding")
        if cfg_pad == "max_length":
            default_padding = "max_length"
        elif cfg_pad == "longest":
            default_padding = True
        if "max_text_length" in spec:
            default_max_len = int(spec["max_text_length"])  # type: ignore[arg-type]

    return {
        "padding": default_padding,
        "truncation": True,
        "max_length": default_max_len,
        "return_tensors": "pt",
    }


class MultimodalEmbedder:
    """Wrapper for extracting L2-normalized image and text embeddings on RTX 4060 (FP16)."""

    def __init__(self, candidate_key: str | None = None, device: str = "cuda") -> None:
        cv_cfg = get_model_config()["cv"]
        self.candidate_key = candidate_key or cv_cfg["active_encoder"]
        self.spec = cv_cfg["zeroshot_candidates"][self.candidate_key]
        self.model_id: str = self.spec["model_id"]
        self.embed_dim: int = int(self.spec["embed_dim"])
        self.device = device
        self._model = None
        self._processor = None

    def load(self) -> None:
        """Load Hugging Face AutoModel & AutoProcessor in eval + FP16 mode."""
        import torch
        from transformers import AutoModel, AutoProcessor

        dtype = torch.float16 if (self.device == "cuda" and torch.cuda.is_available()) else torch.float32
        self._processor = AutoProcessor.from_pretrained(self.model_id)
        self._model = AutoModel.from_pretrained(self.model_id, torch_dtype=dtype).to(self.device)
        self._model.eval()

    def encode_images(self, images: list[Image.Image]) -> np.ndarray:
        """Encode a batch of PIL images into L2-normalized float32 vectors of shape (N, D)."""
        import torch

        if self._model is None:
            self.load()
        with torch.inference_mode():
            inputs = self._processor(images=images, return_tensors="pt").to(self.device)
            feats = self._model.get_image_features(**inputs)
            feats = feats / feats.norm(p=2, dim=-1, keepdim=True).clamp(min=1e-12)
            return feats.detach().cpu().to(torch.float32).numpy()

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        """Encode a batch of text queries into L2-normalized float32 vectors of shape (N, D)."""
        import torch

        if self._model is None:
            self.load()
        tok_kwargs = get_text_tokenizer_kwargs(self.model_id, self.spec)
        with torch.inference_mode():
            inputs = self._processor(text=texts, **tok_kwargs).to(self.device)
            feats = self._model.get_text_features(**inputs)
            feats = feats / feats.norm(p=2, dim=-1, keepdim=True).clamp(min=1e-12)
            return feats.detach().cpu().to(torch.float32).numpy()
