import os
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from database import SessionLocal
from models import Image as DBImage, IndexedFolder
from repositories.vector_repository import VectorRepository
from services.photo import get_thumbnail_path

vector_repo = VectorRepository()

def delete_photo_atomic_sync(db: Session, image_id: str):
    """
    Atomically removes database records of an image from SQLite and ChromaDB.
    Maintains a compensation transaction style for deletion.
    """
    # 1. Fetch from SQLite
    db_image = db.query(DBImage).filter(DBImage.id == image_id).first()
    if db_image:
        db.delete(db_image)
        
    # 2. Commit SQLite deletion
    db.commit()
    
    # 3. Delete from ChromaDB via VectorRepository
    vector_repo.delete([image_id])

def cleanup_zombie_records(db: Session = None):
    """
    Checks all indexed images and batch deletes records if:
    1) Their physical files are missing from disk.
    2) Their parent folder is no longer in IndexedFolder list.
    Also acts as a Garbage Collector for ChromaDB and Thumbnail Cache.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
        
    try:
        indexed_folders = db.query(IndexedFolder.path).all()
        folder_paths = [f.path for f in indexed_folders]
        
        def belongs_to_any_folder(file_path: str, parent_dir: str) -> bool:
            if not folder_paths:
                return False
            try:
                real_parent = os.path.realpath(parent_dir).lower()
                real_file = os.path.realpath(file_path).lower()
            except Exception:
                real_parent = os.path.normpath(parent_dir).lower()
                real_file = os.path.normpath(file_path).lower()

            for f_path in folder_paths:
                try:
                    real_f = os.path.realpath(f_path).lower()
                except Exception:
                    real_f = os.path.normpath(f_path).lower()
                f_prefix = real_f if real_f.endswith(os.sep) else real_f + os.sep
                if real_parent == real_f or real_parent.startswith(f_prefix) or real_file.startswith(f_prefix):
                    return True
            return False

        all_images = db.query(DBImage.id, DBImage.file_path, DBImage.parent_dir).all()
        sqlite_ids = set()
        zombie_ids = []
        
        for img_id, file_path, parent_dir in all_images:
            if not os.path.exists(file_path) or not belongs_to_any_folder(file_path, parent_dir):
                zombie_ids.append(img_id)
            else:
                sqlite_ids.add(img_id)
                
        # 1. SQLite Zombie Cleanup
        if zombie_ids:
            print(f"[Indexer] Found {len(zombie_ids)} unindexed/zombie records in SQLite. Cleaning up...", flush=True)
            for i in range(0, len(zombie_ids), 900):
                chunk = zombie_ids[i:i+900]
                db.query(DBImage).filter(DBImage.id.in_(chunk)).delete(synchronize_session=False)
                for zid in chunk:
                    t_path = get_thumbnail_path(zid)
                    if os.path.exists(t_path):
                        try:
                            os.remove(t_path)
                        except Exception:
                            pass
            db.commit()
        else:
            print("[Indexer] No SQLite zombie/unindexed records found.", flush=True)

        # 2. ChromaDB Garbage Collection
        try:
            chroma_data = vector_repo.collection.get(include=[])
            if chroma_data and chroma_data.get('ids'):
                chroma_ids = set(chroma_data['ids'])
                orphaned_ids = list(chroma_ids - sqlite_ids)
                
                if orphaned_ids:
                    print(f"[Indexer] Found {len(orphaned_ids)} orphaned embeddings in ChromaDB. Cleaning up...", flush=True)
                    vector_repo.delete(orphaned_ids)
                else:
                    print("[Indexer] No ChromaDB garbage vectors found.", flush=True)
        except Exception as chroma_err:
            print(f"[Compensating Tx Error] Failed to access/clean ChromaDB: {chroma_err}", flush=True)
            
        print("[Indexer] Zombie cleanup completed.", flush=True)
    finally:
        if close_db:
            db.close()

def remove_folder_data(folder_path: str, db: Session = None):
    """
    Deletes a folder from IndexedFolder and removes all associated photos
    from SQLite, ChromaDB, and Thumbnail cache.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        real_target = os.path.realpath(folder_path)
        search_prefix = real_target if real_target.endswith(os.sep) else real_target + os.sep
        path_without_sep = real_target.rstrip(os.sep)
        
        target_lower = real_target.lower()
        prefix_lower = search_prefix.lower()
        without_sep_lower = path_without_sep.lower()
        orig_lower = folder_path.lower()
        orig_prefix_lower = (folder_path if folder_path.endswith(os.sep) else folder_path + os.sep).lower()

        images_to_delete = db.query(DBImage.id).filter(
            or_(
                func.lower(DBImage.parent_dir) == target_lower,
                func.lower(DBImage.parent_dir) == without_sep_lower,
                func.lower(DBImage.parent_dir) == orig_lower,
                func.lower(DBImage.parent_dir).startswith(prefix_lower),
                func.lower(DBImage.parent_dir).startswith(orig_prefix_lower),
                func.lower(DBImage.file_path).startswith(prefix_lower),
                func.lower(DBImage.file_path).startswith(orig_prefix_lower),
                func.lower(DBImage.file_path) == target_lower
            )
        ).all()
        image_ids = list(set(row.id for row in images_to_delete)) if images_to_delete else []

        if image_ids:
            print(f"[Indexer] Removing {len(image_ids)} images for folder {folder_path}", flush=True)
            for i in range(0, len(image_ids), 900):
                chunk = image_ids[i:i+900]
                db.query(DBImage).filter(DBImage.id.in_(chunk)).delete(synchronize_session=False)
                for img_id in chunk:
                    t_path = get_thumbnail_path(img_id)
                    if os.path.exists(t_path):
                        try:
                            os.remove(t_path)
                        except Exception:
                            pass

        all_indexed = db.query(IndexedFolder).all()
        for f_rec in all_indexed:
            f_real = os.path.realpath(f_rec.path).lower()
            if f_real in [target_lower, without_sep_lower, orig_lower] or f_rec.path.lower() in [target_lower, without_sep_lower, orig_lower]:
                db.delete(f_rec)

        db.commit()
        
        if image_ids:
            vector_repo.delete(image_ids)
    except Exception as e:
        db.rollback()
        print(f"[Indexer] Error removing folder data: {e}", flush=True)
    finally:
        if close_db:
            db.close()

