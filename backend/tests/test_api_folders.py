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

def test_photo_repository_folder_methods(db_session):
    from repositories.photo_repository import PhotoRepository
    repo = PhotoRepository(db_session)
    
    # Initially empty
    assert repo.list_folders() == []
    assert repo.get_folder_by_path("/test/custom_folder") is None
    
    # Add folder via repository
    created = repo.add_folder("/test/custom_folder")
    db_session.commit()
    
    assert created.path == "/test/custom_folder"
    folders = repo.list_folders()
    assert len(folders) == 1
    assert folders[0].path == "/test/custom_folder"
    
    found = repo.get_folder_by_path("/test/custom_folder")
    assert found is not None
    assert found.path == "/test/custom_folder"

