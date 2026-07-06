import pytest
from models import Image, AIAnalysis
import time

def test_search_photos_text(client, db_session):
    img = Image(
        id="search_test_1",
        parent_dir="/test",
        file_path="/test/search.jpg",
        file_name="search.jpg",
        file_size=100,
        file_mtime=time.time(),
        mime_type="image/jpeg"
    )
    ai = AIAnalysis(
        image_id="search_test_1",
        caption="A beautiful sunset over the mountains",
        tags="[\"sunset\", \"mountain\"]"
    )
    db_session.add_all([img, ai])
    db_session.commit()
    
    # Search for "sunset"
    response = client.post("/api/search", json={"query": "sunset", "limit": 10, "offset": 0})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "search_test_1"

def test_search_photos_no_results(client):
    response = client.post("/api/search", json={"query": "aliens", "limit": 10, "offset": 0})
    assert response.status_code == 200
    assert response.json() == []
