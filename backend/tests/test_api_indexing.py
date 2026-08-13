import pytest
from services.indexing_state import indexing_state_manager

def test_indexing_control_endpoints(client):
    # Reset status
    indexing_state_manager.reset_status()

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
    indexing_state_manager.status = "processing"

    res = client.post("/api/index/pause")
    assert res.status_code == 200
    assert indexing_state_manager.status == "paused"

    res = client.post("/api/index/resume")
    assert res.status_code == 200
    assert indexing_state_manager.status == "processing"

    res = client.post("/api/index/cancel")
    assert res.status_code == 200
    assert indexing_state_manager.status == "cancelled"

    # Reset back to idle
    indexing_state_manager.reset_status()
