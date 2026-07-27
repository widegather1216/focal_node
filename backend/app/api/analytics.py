from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from repositories.photo_repository import PhotoRepository

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/stats")
def get_analytics_stats(db: Session = Depends(get_db)):
    repo = PhotoRepository(db)
    return repo.get_gear_analytics()
