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
        except Exception:
            pass


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def run_migrations(bind_engine=None):
    """
    Creates tables if missing and applies schema migrations safely.
    """
    target_engine = bind_engine or engine
    from sqlalchemy import text
    Base.metadata.create_all(bind=target_engine)
    
    migrations = [
        "ALTER TABLE images ADD COLUMN is_favorite BOOLEAN DEFAULT 0 NOT NULL",
        "ALTER TABLE image_metadata ADD COLUMN focal_length_35mm FLOAT",
        "ALTER TABLE image_metadata ADD COLUMN crop_factor FLOAT",
        "ALTER TABLE image_metadata ADD COLUMN sensor_format VARCHAR(50)",
        "ALTER TABLE ai_analysis ADD COLUMN critique TEXT",
        "ALTER TABLE ai_analysis ADD COLUMN critique_updated_at DATETIME"
    ]
    
    for col_sql in migrations:
        try:
            with target_engine.begin() as conn:
                conn.execute(text(col_sql))
        except Exception:
            pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

