import pytest
import numpy as np
from services.taxonomy import SIGLIP_VISUAL_TAXONOMY
from services.mlx_adapters import SigLIP2Adapter

def test_siglip_taxonomy_taxonomy_defined():
    assert len(SIGLIP_VISUAL_TAXONOMY) > 50
    assert "바다" in SIGLIP_VISUAL_TAXONOMY
    assert "흑백" in SIGLIP_VISUAL_TAXONOMY

def test_siglip_adapter_get_zero_shot_hints_with_mocked_taxonomy():
    adapter = SigLIP2Adapter.__new__(SigLIP2Adapter)
    adapter.cached_taxonomy_embeddings = np.zeros((len(SIGLIP_VISUAL_TAXONOMY), 768), dtype=np.float32)
    # Set high score for index 0 ("바다") and index 1 ("해변")
    adapter.cached_taxonomy_embeddings[0, 0] = 1.0
    adapter.cached_taxonomy_embeddings[1, 0] = 0.9
    
    fake_img_emb = [0.0] * 768
    fake_img_emb[0] = 1.0
    
    hints = adapter.get_zero_shot_hints(fake_img_emb, top_k=2)
    assert hints == [SIGLIP_VISUAL_TAXONOMY[0], SIGLIP_VISUAL_TAXONOMY[1]]
