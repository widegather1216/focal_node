import sys
sys.path.append("backend/app")
from database import SessionLocal
from models import Image

db = SessionLocal()

parent_dir = "/Users/kimbeomjun/Desktop/photo/jpeg"
images = db.query(Image).filter(Image.parent_dir == parent_dir).all()
print(f"Found {len(images)} images for {parent_dir}")
for img in images:
    print(img.file_name)
