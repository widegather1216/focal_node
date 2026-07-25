import pytest
from services.indexing_service import indexing_status, pause_event, cancel_requested

def test_indexing_control_endpoints(client):
    # Reset status
    indexing_status["status"] = "idle"
    indexing_status["processed_files"] = 0
    indexing_status["total_files"] = 0

    # 1. Initial status check
    res = client.get("/api/index/status")
    assert res.status_code == 200
    assert res.json()["status"] == "idle"

    # 2. Cannot pause when idle
    res = client.post("/api/index/pause")
    assert res.status_code == 400

    # 3. Cannot resume when idle
    res = client.post("/api/index/resume")
    assert res.status_code == 400

    # 4. Cannot cancel when idle
    res = client.post("/api/index/cancel")
    assert res.status_code == 400

    # 5. Simulate processing status and test pause/resume/cancel
    indexing_status["status"] = "processing"

    res = client.post("/api/index/pause")
    assert res.status_code == 200
    assert indexing_status["status"] == "paused"

    res = client.post("/api/index/resume")
    assert res.status_code == 200
    assert indexing_status["status"] == "processing"

    res = client.post("/api/index/cancel")
    assert res.status_code == 200
    assert indexing_status["status"] == "cancelled"

    # Reset back to idle
    indexing_status["status"] = "idle"
