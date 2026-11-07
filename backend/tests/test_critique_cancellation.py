import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from services.critique_status import (
    critique_status_manager,
    CritiqueCancelledException
)
import schemas
from services.chat_service import ChatService
import models

def test_critique_status_manager_cancellation():
    test_id = "test_cancel_photo_1"
    critique_status_manager.reset(test_id)
    assert not critique_status_manager.is_cancelled(test_id)

    # Status update during processing
    critique_status_manager.update(test_id, 1, 4, "테스트 진행 중", 25)
    st = critique_status_manager.get(test_id)
    assert st["status"] == "processing"

    # Request cancel
    critique_status_manager.request_cancel(test_id)
    assert critique_status_manager.is_cancelled(test_id)
    st = critique_status_manager.get(test_id)
    assert st["status"] == "cancelled"
    assert "중단" in st["message"]

    # check_cancelled raises exception
    with pytest.raises(CritiqueCancelledException):
        critique_status_manager.check_cancelled(test_id)

    # Subsequent update does not overwrite cancelled status
    critique_status_manager.update(test_id, 2, 4, "비평 작성 중", 50)
    assert critique_status_manager.get(test_id)["status"] == "cancelled"

    # Reset clears cancellation
    critique_status_manager.reset(test_id)
    assert not critique_status_manager.is_cancelled(test_id)

def test_cancel_api_endpoint(client: TestClient):
    test_id = "test_api_cancel_photo"
    critique_status_manager.reset(test_id)

    response = client.post(f"/api/chat/critique/cancel/{test_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
    assert data["photo_id"] == test_id
    assert critique_status_manager.is_cancelled(test_id)

    # Alternate route /api/chat/critique/{photo_id}/cancel
    test_id_alt = "test_api_cancel_photo_alt"
    critique_status_manager.reset(test_id_alt)
    resp_alt = client.post(f"/api/chat/critique/{test_id_alt}/cancel")
    assert resp_alt.status_code == 200
    assert resp_alt.json()["status"] == "cancelled"
    assert critique_status_manager.is_cancelled(test_id_alt)

from contextlib import contextmanager

@pytest.mark.asyncio
async def test_chat_service_generate_critique_cancelled(db_session, monkeypatch):
    test_id = "test_cancel_service_photo"
    critique_status_manager.reset(test_id)

    @contextmanager
    def mock_session_scope():
        yield db_session

    monkeypatch.setattr("services.chat_service.SessionLocal", mock_session_scope)

    # Create dummy image in db with required fields
    img = models.Image(
        id=test_id,
        parent_dir="/fake",
        file_name="test.jpg",
        file_path="/fake/test.jpg",
        file_size=1024,
        file_mtime=1234567.0,
        mime_type="image/jpeg",
        is_favorite=False
    )
    db_session.add(img)
    db_session.commit()

    # Simulate cancellation triggered while in progress (e.g. during Gemma inference)
    with patch("services.chat_service.get_gemma_adapter") as mock_adapter_getter:
        mock_adapter = MagicMock()
        def cancel_during_generation(*args, **kwargs):
            # Cancel requested during model execution
            critique_status_manager.request_cancel(test_id)
            critique_status_manager.check_cancelled(test_id)
            return "This should not be reached"

        mock_adapter.generate_deep_critique.side_effect = cancel_during_generation
        mock_adapter_getter.return_value = mock_adapter

        req = schemas.CritiqueRequest(photo_id=test_id, engine="gemma")
        res = await ChatService.generate_photo_critique(req)

        assert res["status"] == "cancelled"
        assert res["critique"] == ""

        # Verify no critique was committed to DB
        ai = db_session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == test_id).first()
        assert ai is None or not ai.critique


@pytest.mark.asyncio
async def test_critique_cancellation_unloads_models(db_session, monkeypatch):
    """
    Verifies that when critique is cancelled, both UniPercept and Gemma models
    are immediately unloaded from RAM to prevent memory accumulation.
    """
    test_id = "test_cancel_unload_photo"
    critique_status_manager.reset(test_id)

    @contextmanager
    def mock_session_scope():
        yield db_session

    monkeypatch.setattr("services.chat_service.SessionLocal", mock_session_scope)

    img = models.Image(
        id=test_id,
        parent_dir="/fake",
        file_name="unload_test.jpg",
        file_path="/fake/unload_test.jpg",
        file_size=1024,
        file_mtime=1234567.0,
        mime_type="image/jpeg",
        is_favorite=False
    )
    db_session.add(img)
    db_session.commit()

    with patch("services.unipercept_adapter.get_unipercept_adapter") as mock_uni_getter, \
         patch("services.chat_service.get_gemma_adapter") as mock_gemma_getter:

        mock_uni = MagicMock()
        mock_gemma = MagicMock()
        mock_gemma.active_requests = 0

        def cancel_during_unipercept(*args, **kwargs):
            critique_status_manager.request_cancel(test_id)
            critique_status_manager.check_cancelled(test_id)
            return {}

        mock_uni.generate_full_ensemble_critique.side_effect = cancel_during_unipercept
        mock_uni_getter.return_value = mock_uni
        mock_gemma_getter.return_value = mock_gemma

        req = schemas.CritiqueRequest(photo_id=test_id, engine="unipercept")
        res = await ChatService.generate_photo_critique(req)

        assert res["status"] == "cancelled"
        # UniPercept must be unloaded immediately upon cancellation!
        mock_uni.unload_model.assert_called()
        # Gemma must also be unloaded upon cancellation!
        mock_gemma.unload_model.assert_called()


def test_cancel_critique_forces_gemma_unload_when_active_requests_nonzero():
    """
    TC-CRT-10 reproduction:
    Verifies that ChatService.cancel_critique forces Gemma unloading even when
    active_requests > 0 (during an ongoing critique request).
    """
    test_id = "test_force_unload_photo"
    with patch("services.chat_service.get_gemma_adapter") as mock_gemma_getter, \
         patch("services.unipercept_adapter.get_unipercept_adapter") as mock_uni_getter:
        mock_gemma = MagicMock()
        mock_gemma.active_requests = 1
        mock_gemma_getter.return_value = mock_gemma

        mock_uni = MagicMock()
        mock_uni_getter.return_value = mock_uni

        ChatService.cancel_critique(test_id)

        # In DEFECT-01, this fails because active_requests > 0 prevented unload!
        mock_gemma.unload_model.assert_called_once()
        mock_uni.unload_model.assert_called_once()


def test_cancel_critique_cancels_asyncio_task():
    """
    TC-CRT-10 reproduction:
    Verifies that ChatService.cancel_critique calls task.cancel() on the ongoing task
    stored in _critique_tasks.
    """
    import services.chat_service as cs
    test_id = "test_cancel_task_photo"
    mock_task = MagicMock()
    mock_task.done.return_value = False

    with cs._critique_tasks_lock:
        cs._critique_tasks[test_id] = mock_task

    try:
        cs.ChatService.cancel_critique(test_id)
        mock_task.cancel.assert_called_once()
    finally:
        with cs._critique_tasks_lock:
            cs._critique_tasks.pop(test_id, None)


def test_clear_device_caches_calls_mps_synchronize():
    """
    TC-CRT-10 reproduction:
    Verifies that _clear_device_caches synchronizes torch MPS queue before empty_cache.
    """
    import sys
    mock_torch = MagicMock()
    mock_torch.mps = MagicMock()

    with patch.dict(sys.modules, {"torch": mock_torch}):
        from services.chat_service import _clear_device_caches
        _clear_device_caches()

        mock_torch.mps.synchronize.assert_called_once()
        mock_torch.mps.empty_cache.assert_called_once()


def test_base_model_unload_locked_synchronizes_mps():
    """
    TC-CRT-10 reproduction:
    Verifies that BaseKeepAliveModel._unload_model_locked synchronizes MPS before empty_cache.
    """
    import sys
    from services.base_model import BaseKeepAliveModel

    class DummyModel(BaseKeepAliveModel):
        def _load_model(self):
            return "dummy"

    dummy = DummyModel(model_name="dummy", keep_alive_timeout=60)
    dummy.model = "loaded"

    mock_torch = MagicMock()
    mock_torch.mps = MagicMock()

    with patch.dict(sys.modules, {"torch": mock_torch}):
        dummy._unload_model_locked()
        mock_torch.mps.synchronize.assert_called_once()
        mock_torch.mps.empty_cache.assert_called_once()


def test_defect_02_cancelled_during_model_load_immediately_unloads():
    """
    DEFECT-02 reproduction (Case 1):
    If user cancels while Worker Thread A is inside _load_model_locked() (10-15s disk load),
    cancel_critique's unload_model() sees self.model is None and does nothing.
    Once _load_model_locked() finishes loading the 28GB model, Thread A must detect
    cancellation, immediately unload self.model (and _cached_weight_tensor), and raise
    CritiqueCancelledException so 28GB is never stranded in RAM.
    """
    from services.unipercept_adapter import UniPerceptAdapter

    photo_id = "test_defect02_load_race"
    critique_status_manager.reset(photo_id)
    adapter = UniPerceptAdapter()
    adapter._cached_weight_tensor = "mock_mps_weight_tensor"

    def fake_slow_disk_load():
        # Simulate user pressing cancel while 28GB weights are loading from disk
        critique_status_manager.request_cancel(photo_id)
        adapter.model = MagicMock(name="UniPercept28GBModel")

    adapter._load_model_locked = fake_slow_disk_load

    with pytest.raises(CritiqueCancelledException):
        adapter.generate_vr_scores("/fake/img.jpg", photo_id=photo_id)

    assert adapter.model is None, "28GB model remained stranded in RAM after cancellation during load!"
    assert adapter._cached_weight_tensor is None, "_cached_weight_tensor was not cleared on unload!"
    assert adapter.active_requests == 0


def test_defect_02_cancelled_before_vqa_prevents_28gb_reload():
    """
    DEFECT-02 reproduction (Case 2):
    If photo_id is already cancelled when entering generate_perceptual_anchor_vqa
    (or generate_vr_scores), _load_model_locked() must NOT be called to reload 28GB from disk.
    """
    from services.unipercept_adapter import UniPerceptAdapter

    photo_id = "test_defect02_no_reload"
    critique_status_manager.reset(photo_id)
    critique_status_manager.request_cancel(photo_id)

    adapter = UniPerceptAdapter()
    load_calls = []

    def forbidden_reload():
        load_calls.append(1)
        adapter.model = MagicMock(name="Reloaded28GBModel")

    adapter._load_model_locked = forbidden_reload

    with pytest.raises(CritiqueCancelledException):
        adapter.generate_perceptual_anchor_vqa("/fake/img.jpg", photo_id=photo_id)

    assert len(load_calls) == 0, "_load_model_locked() was called for an already-cancelled photo_id!"
    assert adapter.model is None
    assert adapter.active_requests == 0


def test_defect_02_full_ensemble_worker_thread_unloads_in_finally(monkeypatch):
    """
    DEFECT-02 reproduction (Case 3):
    Verifies that generate_full_ensemble_critique guarantees self.unload_model() in its own
    outermost finally block and cleans up _cached_weight_tensor and submodule references.
    """
    from services.unipercept_adapter import UniPerceptAdapter

    photo_id = "test_defect02_ensemble_finally"
    critique_status_manager.reset(photo_id)
    adapter = UniPerceptAdapter()

    dummy_model = MagicMock(name="UniPercept28GB")
    dummy_model.language_model = MagicMock()
    dummy_model.vision_model = MagicMock()
    dummy_model.mlp1 = MagicMock()
    adapter.model = dummy_model
    adapter._cached_weight_tensor = "cached_mps_tensor"
    adapter._cached_preferential_ids = [1, 2, 3]

    monkeypatch.setattr(adapter, "compute_official_vr_score", lambda pv, desc, **kw: 85.0)
    monkeypatch.setattr(adapter, "_load_pil_image", lambda path: None)
    monkeypatch.setattr(adapter, "_prepare_pixel_values", lambda pil_img, **kw: None)
    monkeypatch.setattr(adapter, "_run_single_vqa_domain_inference", lambda *a, **kw: "Valid English anchor.")

    res = adapter.generate_full_ensemble_critique("/fake/img.jpg", photo_id=photo_id)
    assert res["critique"] == "Valid English anchor."
    assert adapter.model is None, "generate_full_ensemble_critique did not unload model in finally!"
    assert adapter._cached_weight_tensor is None
    assert adapter._cached_preferential_ids is None




