import pytest
from models import IndexedFolder, Image
import time

def test_get_folders_empty(client):
    response = client.get("/api/folders")
    assert response.status_code == 200
    assert response.json() == []

def test_get_folders_with_data(client, db_session):
    folder = IndexedFolder(path="/test/my_photos")
    db_session.add(folder)
    db_session.commit()
    
    response = client.get("/api/folders")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["path"] == "/test/my_photos"

def test_delete_folder(client, db_session):
    folder_path = "/test/delete_me/"
    folder = IndexedFolder(path=folder_path)
    img = Image(
        id="hash_delete_1",
        parent_dir=folder_path,
        file_path=f"{folder_path}img.jpg",
        file_name="img.jpg",
        file_size=100,
        file_mtime=time.time(),
        mime_type="image/jpeg"
    )
    db_session.add_all([folder, img])
    db_session.commit()
    
    # Verify existence
    assert db_session.query(IndexedFolder).count() == 1
    assert db_session.query(Image).count() == 1
    
    # Delete API
    response = client.delete(f"/api/folders?path={folder_path}")
    assert response.status_code == 200
    
    # Verify deletion (Cascade)
    assert db_session.query(IndexedFolder).count() == 0
    assert db_session.query(Image).count() == 0
