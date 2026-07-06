import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock

# Import app and database AFTER adding path
from database import Base, get_db
import models
from main import app
import services.indexing_service

from sqlalchemy.pool import StaticPool

# Setup in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def cleanup_database():
    """Clear database tables before each test to ensure isolation."""
    for table in reversed(Base.metadata.sorted_tables):
        with engine.begin() as conn:
            conn.execute(table.delete())
    yield

@pytest.fixture()
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def mock_ai_adapters(monkeypatch):
    # Mock SessionLocal for modules that import it
    monkeypatch.setattr("services.indexing_service.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("database.SessionLocal", TestingSessionLocal)
    
    # Also mock thumbnail generation so it doesn't write to disk
    """
    Mock the heavy ML adapters so tests run instantly without GPU/Memory overhead.
    """
    mock_siglip = MagicMock()
    mock_siglip.get_image_embedding.return_value = [0.1] * 768
    mock_siglip.get_text_embedding.return_value = [0.1] * 768
    
    mock_gemma = MagicMock()
    mock_gemma.generate_caption_and_tags.return_value = {
        "caption": "A beautiful test image.",
        "tags": ["test", "image"],
        "aesthetic_tags": ["mocked"]
    }
    mock_gemma.generate_deep_critique.return_value = "This is a great test photo."
    
    monkeypatch.setattr("services.indexing_service.get_siglip_adapter", lambda: mock_siglip)
    monkeypatch.setattr("services.indexing_service.get_gemma_adapter", lambda: mock_gemma)
    
    mock_chroma_collection = MagicMock()
    mock_chroma_collection.count.return_value = 0
    mock_chroma_collection.query.return_value = {"ids": [[]]}
    monkeypatch.setattr("chroma.get_chroma_collection", lambda: mock_chroma_collection)
    monkeypatch.setattr("services.photo.generate_and_cache_thumbnail", lambda path, img_id: None)
