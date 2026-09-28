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

