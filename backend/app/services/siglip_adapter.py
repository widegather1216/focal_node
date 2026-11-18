"""SigLIP 2 visual-text embedding adapter (resident lightweight model)."""

import threading
from typing import Any

from core.ports import ImageEmbeddingPort, TextEmbeddingPort
from services.base_model import GPU_LOCK

SIGLIP_TEXT_MAX_LENGTH = 64


class SigLIP2Adapter(ImageEmbeddingPort, TextEmbeddingPort):
    """Generates normalized 768-d image/text embeddings and zero-shot visual tags."""

    def __init__(self):
        import torch

        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.model_id = "google/siglip2-base-patch16-224"
        self.model = None
        self.processor = None
        self.cached_taxonomy_embeddings = None
        self.lock = threading.RLock()
        self._load_model()

    def _load_pretrained_with_fallback(self) -> tuple[Any, Any]:
        from transformers import AutoModel, AutoProcessor

        try:
            loaded_model = AutoModel.from_pretrained(
                self.model_id,
                attn_implementation="sdpa",
                local_files_only=True,
            ).to(self.device)
            loaded_processor = AutoProcessor.from_pretrained(self.model_id, local_files_only=True)
            return loaded_model, loaded_processor
        except Exception as local_load_err:
            print(f"[SigLIP2Adapter] Local cache miss, loading from hub: {local_load_err}", flush=True)
            loaded_model = AutoModel.from_pretrained(
                self.model_id,
                attn_implementation="sdpa",
            ).to(self.device)
            loaded_processor = AutoProcessor.from_pretrained(self.model_id)
            return loaded_model, loaded_processor

    def _load_model(self) -> None:
        if self.model is not None:
            return
        with GPU_LOCK:
            with self.lock:
                if self.model is None:
                    print(f"[SigLIP2Adapter] Loading model {self.model_id} on {self.device}...", flush=True)
                    self.model, self.processor = self._load_pretrained_with_fallback()
                    print("[SigLIP2Adapter] Model loaded successfully.", flush=True)
        self._precompute_taxonomy_embeddings()

    def _resolve_text_max_length(self) -> int:
        text_config = getattr(getattr(self.model, "config", None), "text_config", None)
        configured_limit = getattr(text_config, "max_position_embeddings", None)
        if isinstance(configured_limit, int) and not isinstance(configured_limit, bool) and configured_limit > 0:
            return configured_limit
        return SIGLIP_TEXT_MAX_LENGTH

    def _precompute_taxonomy_embeddings(self) -> None:
        if self.cached_taxonomy_embeddings is not None:
            return
        try:
            import torch
            from services.taxonomy import SIGLIP_VISUAL_TAXONOMY

            max_length = self._resolve_text_max_length()
            encoded = self.processor(
                text=SIGLIP_VISUAL_TAXONOMY,
                padding="max_length",
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            ).to(self.device)
            with GPU_LOCK:
                with torch.no_grad():
                    feature_output = self.model.get_text_features(**encoded)
                text_features = feature_output.pooler_output
                normalized = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
                self.cached_taxonomy_embeddings = normalized.cpu().numpy()
            print(f"[SigLIP2Adapter] Precomputed taxonomy embeddings for {len(SIGLIP_VISUAL_TAXONOMY)} visual concepts.", flush=True)
        except Exception as err:
            print(f"[SigLIP2Adapter] Failed to precompute taxonomy embeddings: {err}", flush=True)
            self.cached_taxonomy_embeddings = None

    def get_image_embedding(self, image_path: str) -> list[float]:
        import torch
        from utils.image import load_pil_image

        self._load_model()
        pil_image = load_pil_image(image_path)
        encoded = self.processor(images=pil_image, return_tensors="pt")
        with GPU_LOCK:
            encoded = encoded.to(self.device)
            with torch.no_grad():
                feature_output = self.model.get_image_features(**encoded)
                image_features = feature_output.pooler_output
                normalized = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
                return normalized[0].tolist()

    def get_text_embedding(self, text: str) -> list[float]:
        import torch

        self._load_model()
        max_length = self._resolve_text_max_length()
        encoded = self.processor(
            text=[text],
            padding="max_length",
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        with GPU_LOCK:
            encoded = encoded.to(self.device)
            with torch.no_grad():
                feature_output = self.model.get_text_features(**encoded)
            text_features = feature_output.pooler_output
            normalized = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
            return normalized[0].tolist()

    def get_zero_shot_hints(self, image_input: Any, top_k: int = 15, min_score: float = 0.22) -> list[str]:
        """Returns matching visual keyword strings exceeding min_score cosine similarity."""
        import numpy as np
        from services.taxonomy import SIGLIP_VISUAL_TAXONOMY

        if self.cached_taxonomy_embeddings is None:
            return []

        image_emb = self.get_image_embedding(image_input) if isinstance(image_input, str) else image_input
        if image_emb is None or len(image_emb) == 0:
            return []

        image_vector = np.array(image_emb)
        image_vector = image_vector / np.linalg.norm(image_vector)
        similarity_scores = np.dot(self.cached_taxonomy_embeddings, image_vector)
        sorted_indices = np.argsort(similarity_scores)[::-1]

        filtered_hints = [
            SIGLIP_VISUAL_TAXONOMY[idx] for idx in sorted_indices if similarity_scores[idx] >= min_score
        ][:top_k]
        if not filtered_hints and len(sorted_indices) > 0:
            return [SIGLIP_VISUAL_TAXONOMY[idx] for idx in sorted_indices[:3]]
        return filtered_hints
