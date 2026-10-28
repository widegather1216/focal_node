import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL, CONFIG_DIR

# Ensure CONFIG_DIR exists
os.makedirs(CONFIG_DIR, exist_ok=True)


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
    pool_size=20,
    max_overflow=40
)



@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
    except Exception as e:
        # Fallback for in-memory or uninitialized directory
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()
        except Exception as fallback_err:
            print(f"[Database] Warning: SQLite PRAGMA configuration failed: {fallback_err}", flush=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def run_migrations(bind_engine=None):
    """
    Creates tables if missing and applies schema migrations safely.
    """
    target_engine = bind_engine or engine
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    Base.metadata.create_all(bind=target_engine)
    
    migrations = [
        "ALTER TABLE images ADD COLUMN is_favorite BOOLEAN DEFAULT 0 NOT NULL",
        "ALTER TABLE image_metadata ADD COLUMN focal_length_35mm FLOAT",
        "ALTER TABLE image_metadata ADD COLUMN crop_factor FLOAT",
        "ALTER TABLE image_metadata ADD COLUMN sensor_format VARCHAR(50)",
        "ALTER TABLE ai_analysis ADD COLUMN critique TEXT",
        "ALTER TABLE ai_analysis ADD COLUMN critique_updated_at DATETIME",
        "ALTER TABLE ai_analysis ADD COLUMN overall_score FLOAT",
        "ALTER TABLE ai_analysis ADD COLUMN iaa_score FLOAT",
        "ALTER TABLE ai_analysis ADD COLUMN iqa_score FLOAT",
        "ALTER TABLE ai_analysis ADD COLUMN ista_score FLOAT",
        "ALTER TABLE ai_analysis ADD COLUMN critique_en TEXT",
        "CREATE INDEX IF NOT EXISTS idx_images_is_favorite ON images (is_favorite)",
        "CREATE INDEX IF NOT EXISTS idx_image_metadata_camera_model ON image_metadata (camera_model)",
        "CREATE INDEX IF NOT EXISTS idx_image_metadata_lens_model ON image_metadata (lens_model)",
        "CREATE INDEX IF NOT EXISTS idx_image_metadata_iso ON image_metadata (iso)",
        "CREATE INDEX IF NOT EXISTS idx_image_metadata_f_number ON image_metadata (f_number)",
        "CREATE INDEX IF NOT EXISTS idx_image_metadata_focal_length ON image_metadata (focal_length)",
        "CREATE INDEX IF NOT EXISTS idx_ai_analysis_overall_score ON ai_analysis (overall_score)",
        "CREATE INDEX IF NOT EXISTS idx_ai_analysis_iaa_score ON ai_analysis (iaa_score)"
    ]
    
    for col_sql in migrations:
        try:
            with target_engine.begin() as conn:
                conn.execute(text(col_sql))
        except OperationalError as op_err:
            # Expected error when column already exists in SQLite
            if "duplicate column name" not in str(op_err).lower():
                print(f"[Database] Migration note for '{col_sql}': {op_err}", flush=True)
        except Exception as err:
            print(f"[Database] Migration error executing '{col_sql}': {err}", flush=True)

    _backfill_critique_scores(target_engine)
    _backfill_adaptive_overall_scores(target_engine)


def _backfill_critique_scores(target_engine):
    """
    Backfills overall_score, iaa_score, iqa_score, and ista_score
    from existing legacy critique text for rows where critique IS NOT NULL and overall_score IS NULL.
    """
    from sqlalchemy import text
    try:
        from services.ai_parser import parse_scoreboard_scores
    except ImportError:
        try:
            from app.services.ai_parser import parse_scoreboard_scores
        except ImportError as import_err:
            print(f"[Database] Notice: Skipping critique backfill (ai_parser import unavailable): {import_err}", flush=True)
            return

    try:
        with target_engine.begin() as conn:
            rows = conn.execute(
                text("SELECT image_id, critique FROM ai_analysis WHERE critique IS NOT NULL AND critique != '' AND overall_score IS NULL")
            ).fetchall()

            if not rows:
                return

            update_count = 0
            for row in rows:
                image_id = row[0]
                critique_text = row[1]
                scores = parse_scoreboard_scores(critique_text)

                if any(v is not None for v in scores.values()):
                    conn.execute(
                        text(
                            "UPDATE ai_analysis SET "
                            "overall_score = :overall, "
                            "iaa_score = :iaa, "
                            "iqa_score = :iqa, "
                            "ista_score = :ista "
                            "WHERE image_id = :image_id"
                        ),
                        {
                            "overall": scores.get("overall"),
                            "iaa": scores.get("iaa"),
                            "iqa": scores.get("iqa"),
                            "ista": scores.get("ista"),
                            "image_id": image_id,
                        }
                    )
                    update_count += 1
            if update_count > 0:
                print(f"[Database] Successfully backfilled scores for {update_count} critique records.", flush=True)
    except Exception as err:
        print(f"[Database] Warning: Failed to backfill critique scores: {err}", flush=True)


def _backfill_adaptive_overall_scores(target_engine):
    """
    Recalculates and backfills overall_score using the EXIF-adaptive perceptual scoring model
    for all records in ai_analysis where iaa_score IS NOT NULL.
    Joins with image_metadata to obtain f_number and iso.
    """
    from sqlalchemy import text
    try:
        from services.scoring import calculate_overall_vr_score
    except ImportError:
        try:
            from app.services.scoring import calculate_overall_vr_score
        except ImportError as import_err:
            print(f"[Database] Notice: Skipping adaptive score backfill (scoring import unavailable): {import_err}", flush=True)
            return

    try:
        with target_engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT a.image_id, a.iaa_score, a.iqa_score, a.ista_score, a.overall_score, "
                    "m.f_number, m.iso "
                    "FROM ai_analysis a "
                    "LEFT JOIN image_metadata m ON a.image_id = m.image_id "
                    "WHERE a.iaa_score IS NOT NULL"
                )
            ).fetchall()

            if not rows:
                return

            update_count = 0
            for row in rows:
                image_id = row[0]
                iaa = float(row[1]) if row[1] is not None else None
                if iaa is None:
                    continue

                iqa = float(row[2]) if row[2] is not None else iaa
                ista = float(row[3]) if row[3] is not None else iaa
                current_overall = float(row[4]) if row[4] is not None else None
                f_number = float(row[5]) if row[5] is not None else None
                iso = float(row[6]) if row[6] is not None else None

                new_overall = float(calculate_overall_vr_score(
                    iaa=iaa,
                    iqa=iqa,
                    ista=ista,
                    f_number=f_number,
                    iso=iso,
                ))

                if current_overall is None or round(current_overall, 2) != round(new_overall, 2):
                    conn.execute(
                        text("UPDATE ai_analysis SET overall_score = :score WHERE image_id = :id"),
                        {"score": new_overall, "id": image_id}
                    )
                    update_count += 1

            if update_count > 0:
                print(f"[Database] Successfully backfilled adaptive overall_score for {update_count} critique records.", flush=True)
    except Exception as err:
        print(f"[Database] Warning: Failed to backfill adaptive overall scores: {err}", flush=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

