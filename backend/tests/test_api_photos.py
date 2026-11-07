import pytest
from models import Image, ImageMetadata, AIAnalysis
import time

def test_get_photos_empty(client):
    response = client.get("/api/photos")
    assert response.status_code == 200
    assert response.json() == []

def test_get_photos_with_data(client, db_session):
    # Insert dummy data
    img = Image(
        id="test_hash_1",
        parent_dir="/test/dir",
        file_path="/test/dir/photo1.jpg",
        file_name="photo1.jpg",
        file_size=1024,
        file_mtime=time.time(),
        mime_type="image/jpeg",
        is_favorite=True
    )
    db_session.add(img)
    db_session.commit()
    
    response = client.get("/api/photos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "test_hash_1"
    assert data[0]["file_name"] == "photo1.jpg"
    assert data[0]["is_favorite"] is True

def test_update_photo_metadata(client, db_session):
    # Insert dummy data
    img = Image(
        id="test_hash_2",
        parent_dir="/test/dir",
        file_path="/test/dir/photo2.jpg",
        file_name="photo2.jpg",
        file_size=1024,
        file_mtime=time.time(),
        mime_type="image/jpeg"
    )
    ai = AIAnalysis(
        image_id="test_hash_2",
        caption="Old caption",
        tags="[\"old\"]",
        aesthetic_tags="[\"cinematic\"]",
        is_user_edited=False,
        critique="기존 한국어 심층 비평",
        critique_en="Existing English perceptual anchor.",
        overall_score=89.5,
        iaa_score=92.0,
        iqa_score=87.0,
        ista_score=88.5,
    )
    db_session.add_all([img, ai])
    db_session.commit()
    
    payload = {
        "caption": "New user edited caption",
        "tags": ["new", "tags"]
    }
    response = client.patch("/api/photos/test_hash_2/metadata", json=payload)
    assert response.status_code == 200
    resp_data = response.json()
    resp_ai = resp_data["ai_analysis"]
    assert resp_ai["caption"] == "New user edited caption"
    assert resp_ai["tags"] == ["new", "tags"]
    assert resp_ai["aesthetic_tags"] == ["cinematic"]
    assert resp_ai["is_user_edited"] is True
    assert resp_ai["critique"] == "기존 한국어 심층 비평"
    assert resp_ai["critique_en"] == "Existing English perceptual anchor."
    assert resp_ai["overall_score"] == 89.5
    assert resp_ai["iaa_score"] == 92.0
    assert resp_ai["iqa_score"] == 87.0
    assert resp_ai["ista_score"] == 88.5
    
    # Verify DB update
    updated_ai = db_session.query(AIAnalysis).filter(AIAnalysis.image_id == "test_hash_2").first()
    assert updated_ai.caption == "New user edited caption"
    assert updated_ai.is_user_edited is True
    assert "new" in updated_ai.tags
    assert updated_ai.critique == "기존 한국어 심층 비평"
