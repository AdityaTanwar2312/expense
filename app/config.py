"""
config.py — Environment variables + logger factory.
All other modules import `settings` and `get_logger` from here.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv()


# ── Settings ──────────────────────────────────────────────────────────────────
class Settings:
    # Database
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 5432))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "expenses_db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "expense_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "expense_pass")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", "logs"))
    LOG_FILE: str = os.getenv("LOG_FILE", "expense_processor.log")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()


# ── Logger factory ────────────────────────────────────────────────────────────
def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger with:
      - StreamHandler  → console output
      - FileHandler    → logs/<LOG_FILE>
    Both handlers respect the LOG_LEVEL env var.
    """
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    logger.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # File handler
    file_handler = logging.FileHandler(settings.LOG_DIR / settings.LOG_FILE)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger