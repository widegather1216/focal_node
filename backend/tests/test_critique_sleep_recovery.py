import pytest
import asyncio
from unittest.mock import patch, MagicMock
from services.critique_status import critique_status_manager
from services.chat_service import ChatService
import schemas
import models
from contextlib import contextmanager

def test_critique_status_db_fallback(db_session, monkeypatch):
    """
    Verifies that when in-memory status is missing or cleared (e.g. after sleep/restart),
    critique_status_manager.get() falls back to database to recover completed critique.
    """
    test_id = "test_photo_sleep_recovery_1"
    critique_status_manager.reset(test_id)

    @contextmanager
    def mock_session_scope():
        yield db_session

    monkeypatch.setattr("services.critique_status.SessionLocal", mock_session_scope, raising=False)
    # Also patch database in critique_status module
    import database
    monkeypatch.setattr(database, "SessionLocal", mock_session_scope)

    # Insert photo and existing AI critique in DB
    now = models.utcnow()
    img = models.Image(
        id=test_id,
        parent_dir="/fake",
        file_name="sleep_test.jpg",
        file_path="/fake/sleep_test.jpg",
        file_size=2048,
        file_mtime=1234567.0,
        mime_type="image/jpeg",
        is_favorite=False
    )
    ai = models.AIAnalysis(
        image_id=test_id,
        critique="[복구된 비평] 멋진 풍경 사진입니다.",
        critique_updated_at=now
    )
    db_session.add(img)
    db_session.add(ai)
    db_session.commit()

    # Query status - should self-heal and return completed with critique from DB
    status = critique_status_manager.get(test_id)
    assert status["status"] == "completed"
    assert status["progress"] == 100
    assert status["critique"] == "[복구된 비평] 멋진 풍경 사진입니다."
    assert status["photo_id"] == test_id


@pytest.mark.asyncio
async def test_critique_task_shielded_against_cancellation(db_session, monkeypatch):
    """
    Verifies that if client cancels the outer request (e.g. sleep causes client disconnect),
    the background generation task is shielded and completes execution.
    """
    test_id = "test_photo_shield_sleep"
    critique_status_manager.reset(test_id)

    @contextmanager
    def mock_session_scope():
        yield db_session

    monkeypatch.setattr("services.chat_service.SessionLocal", mock_session_scope)

    img = models.Image(
        id=test_id,
        parent_dir="/fake",
        file_name="shield_test.jpg",
        file_path="/fake/shield_test.jpg",
        file_size=2048,
        file_mtime=1234567.0,
        mime_type="image/jpeg",
        is_favorite=False
    )
    db_session.add(img)
    db_session.commit()

    pipeline_completed = asyncio.Event()

    async def mock_gemma_pipeline(*args, **kwargs):
        # Simulate long-running VLM execution
        await asyncio.sleep(0.1)
        pipeline_completed.set()
        return "완성된 비평 내용"

    monkeypatch.setattr("services.chat_service._execute_gemma_critique_pipeline", mock_gemma_pipeline)

    req = schemas.CritiqueRequest(photo_id=test_id, engine="gemma")
    
    # Start generation in a task, then cancel the outer caller task early (simulating disconnect)
    caller_task = asyncio.create_task(ChatService.generate_photo_critique(req))
    await asyncio.sleep(0.02)
    caller_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await caller_task

    # The background shielded task must finish execution despite caller being cancelled!
    await asyncio.wait_for(pipeline_completed.wait(), timeout=1.0)
    await asyncio.sleep(0.05)

    # Check status manager has recorded completed status
    status = critique_status_manager.get(test_id)
    assert status["status"] == "completed"
    assert status["critique"] == "완성된 비평 내용"
