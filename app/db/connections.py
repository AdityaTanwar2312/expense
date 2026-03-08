"""
db/connection.py — SQLAlchemy engine + session factory.
All DB operations import `get_engine` or `get_session` from here.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings, get_logger

logger = get_logger(__name__)

# ── Engine (created once, reused) ─────────────────────────────────────────────
def get_engine():
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,   # validate connections before use
        pool_size=5,
        echo=False,
    )
    return engine


# ── Session factory ───────────────────────────────────────────────────────────
def get_session() -> Session:
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


# ── Schema bootstrap ──────────────────────────────────────────────────────────
def init_db() -> None:
    """
    Run schema.sql against the connected database.
    Safe to call repeatedly — all statements use IF NOT EXISTS.
    """
    import pathlib
    schema_file = pathlib.Path(__file__).parent / "schema.sql"
    ddl = schema_file.read_text()

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(ddl))

    logger.info("Database schema initialised (schema.sql applied)")