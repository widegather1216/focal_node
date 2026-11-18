"""SQLAlchemy engine configuration, WAL pragmas, and non-destructive schema migrations."""

import json
import logging
import os
from typing import Callable, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

from config import CONFIG_DIR, DATABASE_URL

logger = logging.getLogger(__name__)

os.makedirs(CONFIG_DIR, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
    pool_size=20,
    max_overflow=40,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
    except Exception:
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()
        except Exception as fallback_err:
            print(f"[Database] Warning: SQLite PRAGMA configuration failed: {fallback_err}", flush=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

_MIGRATION_STATEMENTS = (
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
    "CREATE INDEX IF NOT EXISTS idx_ai_analysis_iaa_score ON ai_analysis (iaa_score)",
)


def _execute_migration_sql(target_engine, sql_statement: str) -> None:
    try:
        with target_engine.begin() as conn:
            conn.execute(text(sql_statement))
    except OperationalError as op_err:
        if "duplicate column name" not in str(op_err).lower():
            print(f"[Database] Migration note for '{sql_statement}': {op_err}", flush=True)
    except Exception as err:
        print(f"[Database] Migration error executing '{sql_statement}': {err}", flush=True)


def run_migrations(bind_engine=None) -> None:
    """Creates missing tables and executes non-destructive schema migrations."""
    target_engine = bind_engine or engine
    Base.metadata.create_all(bind=target_engine)
    for col_sql in _MIGRATION_STATEMENTS:
        _execute_migration_sql(target_engine, col_sql)
    _backfill_critique_scores(target_engine)
    _backfill_adaptive_overall_scores(target_engine)
    _normalize_escaped_ai_tags(target_engine)


def _resolve_scoreboard_parser() -> Optional[Callable]:
    try:
        from services.ai_parser import parse_scoreboard_scores
        return parse_scoreboard_scores
    except ImportError:
        try:
            from app.services.ai_parser import parse_scoreboard_scores
            return parse_scoreboard_scores
        except ImportError as import_err:
            print(f"[Database] Notice: Skipping critique backfill (ai_parser import unavailable): {import_err}", flush=True)
            return None


def _resolve_overall_calculator() -> Optional[Callable]:
    try:
        from services.scoring import calculate_overall_vr_score
        return calculate_overall_vr_score
    except ImportError:
        try:
            from app.services.scoring import calculate_overall_vr_score
            return calculate_overall_vr_score
        except ImportError as import_err:
            print(f"[Database] Notice: Skipping adaptive score backfill (scoring import unavailable): {import_err}", flush=True)
            return None


def _apply_critique_score_backfill_row(conn, image_id: str, critique_text: str, parser_fn: Callable) -> bool:
    scores = parser_fn(critique_text)
    if not any(val is not None for val in scores.values()):
        return False
    conn.execute(
        text(
            "UPDATE ai_analysis SET overall_score = :overall, iaa_score = :iaa, "
            "iqa_score = :iqa, ista_score = :ista WHERE image_id = :image_id"
        ),
        {
            "overall": scores.get("overall"),
            "iaa": scores.get("iaa"),
            "iqa": scores.get("iqa"),
            "ista": scores.get("ista"),
            "image_id": image_id,
        },
    )
    return True


def _backfill_critique_scores(target_engine) -> None:
    """Backfills 4-dim scores from legacy critique text when overall_score IS NULL."""
    parser_fn = _resolve_scoreboard_parser()
    if parser_fn is None:
        return

    try:
        with target_engine.begin() as conn:
            rows = conn.execute(
                text("SELECT image_id, critique FROM ai_analysis WHERE critique IS NOT NULL AND critique != '' AND overall_score IS NULL")
            ).fetchall()
            update_count = sum(
                1 for row in rows if _apply_critique_score_backfill_row(conn, row[0], row[1], parser_fn)
            )
            if update_count > 0:
                print(f"[Database] Successfully backfilled scores for {update_count} critique records.", flush=True)
    except Exception as err:
        print(f"[Database] Warning: Failed to backfill critique scores: {err}", flush=True)


def _apply_adaptive_backfill_row(conn, row: tuple, calculator_fn: Callable) -> bool:
    image_id, iaa_raw, iqa_raw, ista_raw, current_raw, f_num_raw, iso_raw = row
    if iaa_raw is None:
        return False
    iaa = float(iaa_raw)
    iqa = float(iqa_raw) if iqa_raw is not None else iaa
    ista = float(ista_raw) if ista_raw is not None else iaa
    current_overall = float(current_raw) if current_raw is not None else None
    f_number = float(f_num_raw) if f_num_raw is not None else None
    iso = float(iso_raw) if iso_raw is not None else None

    new_overall = float(calculator_fn(iaa=iaa, iqa=iqa, ista=ista, f_number=f_number, iso=iso))
    if current_overall is not None and round(current_overall, 2) == round(new_overall, 2):
        return False
    conn.execute(text("UPDATE ai_analysis SET overall_score = :score WHERE image_id = :id"), {"score": new_overall, "id": image_id})
    return True


def _backfill_adaptive_overall_scores(target_engine) -> None:
    """Recalculates overall_score using EXIF-adaptive perceptual weights for iaa_score rows."""
    calculator_fn = _resolve_overall_calculator()
    if calculator_fn is None:
        return

    try:
        with target_engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT a.image_id, a.iaa_score, a.iqa_score, a.ista_score, a.overall_score, m.f_number, m.iso "
                    "FROM ai_analysis a LEFT JOIN image_metadata m ON a.image_id = m.image_id "
                    "WHERE a.iaa_score IS NOT NULL"
                )
            ).fetchall()
            update_count = sum(
                1 for row in rows if _apply_adaptive_backfill_row(conn, row, calculator_fn)
            )
            if update_count > 0:
                print(f"[Database] Successfully backfilled adaptive overall_score for {update_count} critique records.", flush=True)
    except Exception as err:
        print(f"[Database] Warning: Failed to backfill adaptive overall scores: {err}", flush=True)


def _normalize_tag_json_column(raw_value: Optional[str], image_id: str, column_name: str) -> Optional[str]:
    """Decodes escaped \\uXXXX sequences in a JSON tag column into UTF-8 JSON."""
    if not raw_value or "\\u" not in raw_value:
        return None
    try:
        parsed_tags = json.loads(raw_value)
        normalized = json.dumps(parsed_tags, ensure_ascii=False)
        normalized.encode("utf-8")
    except (json.JSONDecodeError, TypeError, ValueError, UnicodeEncodeError) as parse_err:
        logger.warning(
            "[Database] Skipping malformed %s JSON for image %s: %s",
            column_name,
            image_id,
            parse_err,
        )
        return None
    return normalized if normalized != raw_value else None


def _apply_ai_tag_normalization_row(conn, row: tuple) -> bool:
    image_id, raw_tags, raw_aesthetic_tags = row
    updated_tags = _normalize_tag_json_column(raw_tags, image_id, "tags")
    updated_aesthetic = _normalize_tag_json_column(raw_aesthetic_tags, image_id, "aesthetic_tags")
    if updated_tags is None and updated_aesthetic is None:
        return False
    conn.execute(
        text(
            "UPDATE ai_analysis SET tags = :tags, aesthetic_tags = :aesthetic_tags "
            "WHERE image_id = :image_id"
        ),
        {
            "tags": raw_tags if updated_tags is None else updated_tags,
            "aesthetic_tags": raw_aesthetic_tags if updated_aesthetic is None else updated_aesthetic,
            "image_id": image_id,
        },
    )
    return True


def _normalize_escaped_ai_tags(target_engine) -> None:
    """Normalizes legacy \\uXXXX-escaped JSON strings in ai_analysis tags columns."""
    try:
        with target_engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT image_id, tags, aesthetic_tags FROM ai_analysis "
                    "WHERE (tags IS NOT NULL AND instr(tags, :needle) > 0) "
                    "OR (aesthetic_tags IS NOT NULL AND instr(aesthetic_tags, :needle) > 0)"
                ),
                {"needle": "\\u"},
            ).fetchall()
            update_count = sum(1 for row in rows if _apply_ai_tag_normalization_row(conn, row))
            if update_count > 0:
                logger.info("[Database] Normalized escaped AI tags for %d records.", update_count)
    except Exception as err:
        logger.warning("[Database] Failed to normalize escaped AI tags: %s", err)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
