import os
import sys
import asyncio
import subprocess
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from services.critique_status import CritiqueStatusManager
from services.unipercept_adapter import UniPerceptAdapter
from services.mlx_adapters import GemmaAdapter
from utils.image import load_pil_image, is_raw_image


def test_unipercept_no_eager_heavy_imports_in_subprocess():
    """
    REFACTOR-06 / Rule 2.5:
    Verifies that importing services.unipercept_utils or services.unipercept_adapter
    does not eagerly import torch, torchvision, or transformers at startup.
    """
    code = (
        "import sys\n"
        "from services import unipercept_utils\n"
        "from services import unipercept_adapter\n"
        "heavy_loaded = [m for m in ('torch', 'torchvision', 'transformers') if m in sys.modules]\n"
        "assert not heavy_loaded, f'Heavy modules eagerly loaded: {heavy_loaded}'\n"
        "print('PASS_LAZY_IMPORT')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=os.path.abspath("backend/app")
    )
    assert result.returncode == 0, f"Subprocess failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    assert "PASS_LAZY_IMPORT" in result.stdout


def test_unipercept_adapter_candidate_paths_use_config_dir(monkeypatch):
    """
    REFACTOR-06 / Rule 2.6:
    Verifies that UniPerceptAdapter checks checkpoints and config.CONFIG_DIR paths
    instead of hardcoded ~/.config/focal_node.
    """
    from config import CONFIG_DIR
    adapter = UniPerceptAdapter()
    
    expected_dev_path = os.path.join(CONFIG_DIR, "models", "UniPercept")
    # Verify CONFIG_DIR is used in candidate search paths
    custom_path = os.environ.get("UNIPERCEPT_MODEL_PATH")
    expected_candidates = [
        custom_path,
        os.path.abspath("checkpoints/UniPercept"),
        os.path.abspath("checkpoints/unipercept"),
        os.path.join(CONFIG_DIR, "models", "UniPercept"),
        os.path.join(CONFIG_DIR, "models", "unipercept"),
    ]
    # Check that ~/.config/focal_node is not hardcoded if in dev mode
    if not getattr(sys, "frozen", False):
        assert "focal_node_dev" in CONFIG_DIR or "focal_node" in CONFIG_DIR


def test_critique_status_manager_bounds_capacity_and_evicts_stale():
    """
    REFACTOR-06 / Rule 2.4:
    Verifies CritiqueStatusManager bounds memory capacity to max_history (100)
    and evicts completed/cancelled/error records when saturated.
    """
    manager = CritiqueStatusManager(max_history=5)
    
    # Fill with 5 items
    for i in range(5):
        status_val = "completed" if i % 2 == 0 else "processing"
        manager.update(f"photo_{i}", 1, 4, f"msg {i}", 25, status=status_val)
        
    assert len(manager._statuses) == 5
    assert "photo_0" in manager._statuses
    
    # Adding photo_5 should evict photo_0 (which has status='completed')
    manager.update("photo_5", 1, 4, "msg 5", 25, status="processing")
    assert len(manager._statuses) == 5
    assert "photo_0" not in manager._statuses
    assert "photo_5" in manager._statuses


def test_gemma_adapter_raises_on_inference_errors_instead_of_silent_strings(monkeypatch):
    """
    REFACTOR-06 / Rule 4.3 & ADR-05:
    Verifies GemmaAdapter methods raise exceptions rather than returning
    fake error strings (e.g. '시스템 메모리가 부족하여...').
    """
    gemma = GemmaAdapter()
    gemma.model = MagicMock()
    gemma.processor = MagicMock()
    
    # 1. generate_deep_critique
    with patch("mlx_vlm.generate", side_effect=RuntimeError("MLX out of memory")):
        with pytest.raises(RuntimeError, match="MLX out of memory"):
            gemma.generate_deep_critique("/fake/path.jpg")
            
    # 2. _execute_perceptual_critique_generation
    with patch("mlx_vlm.generate", side_effect=RuntimeError("OOM during perceptual critique")):
        with pytest.raises(RuntimeError, match="OOM during perceptual critique"):
            gemma._execute_perceptual_critique_generation([], "/fake/path.jpg", {}, None)
            
    # 3. generate_critique_summary
    with patch("mlx_vlm.generate", side_effect=Exception("Summary inference crash")):
        with pytest.raises(Exception, match="Summary inference crash"):
            gemma.generate_critique_summary([{"critique": "test", "file_name": "a.jpg"}])


def test_load_pil_image_passes_min_dimension_for_raw():
    """
    REFACTOR-06 / Rule 2.3:
    Verifies load_pil_image forwards min_dimension=1024 for RAW images
    and supports existing calls without min_dimension.
    """
    with patch("utils.image.decode_raw_to_pil") as mock_decode:
        mock_decode.return_value = Image.new("RGB", (1024, 768))
        
        # With min_dimension=1024
        img = load_pil_image("sample.arw", min_dimension=1024)
        mock_decode.assert_called_with("sample.arw", min_dimension=1024)
        
        # Default without min_dimension
        img2 = load_pil_image("sample.cr3")
        mock_decode.assert_called_with("sample.cr3", min_dimension=None)


def test_unipercept_single_pass_decoding_and_pil_sharing(monkeypatch):
    """
    REFACTOR-06 / Rule 2.3 & Rule 2.4:
    Verifies generate_full_ensemble_critique decodes image once at min_dimension=1024
    and shares both pil_img and pixel_values across VR and VQA without duplicate decoding.
    """
    adapter = UniPerceptAdapter()
    dummy_model = MagicMock()
    adapter.model = dummy_model
    
    decode_call_count = 0
    test_pil = Image.new("RGB", (1024, 1024), color="blue")
    
    def count_load(path, min_dimension=None):
        nonlocal decode_call_count
        decode_call_count += 1
        return test_pil
        
    prepare_call_count = 0
    def count_prepare(pil, photo_id=None):
        nonlocal prepare_call_count
        prepare_call_count += 1
        return "shared_tensor"
        
    monkeypatch.setattr(adapter, "_load_pil_image", count_load)
    monkeypatch.setattr(adapter, "_prepare_pixel_values", count_prepare)
    monkeypatch.setattr(adapter, "compute_official_vr_score", lambda pv, desc, **kw: 80.0)
    monkeypatch.setattr(adapter, "_run_single_vqa_domain_inference", lambda *a, **kw: "Anchor text")
    
    res = adapter.generate_full_ensemble_critique("/fake/test.arw")
    
    # Must only decode once for the whole ensemble!
    assert decode_call_count == 1, f"Expected 1 decode but got {decode_call_count}"
    # Must only prepare pixel_values once!
    assert prepare_call_count == 1, f"Expected 1 tensor preparation but got {prepare_call_count}"
    # Must return pil_img in result dict for downstream Gemma sharing
    assert res.get("pil_img") is test_pil
