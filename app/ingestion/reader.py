from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from app.config import get_logger

logger = get_logger(__name__)

# Required columns every CSV must contain
REQUIRED_COLUMNS = {"date", "category", "amount", "submitted_by"}


def _read_single_file(filepath: Path) -> list[dict[str, Any]]:
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    if filepath.suffix.lower() != ".csv":
        raise ValueError(f"Expected a .csv file, got: {filepath.name}")

    with filepath.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        # Normalise header names (strip whitespace, lowercase)
        if reader.fieldnames is None:
            raise ValueError(f"Empty or unreadable CSV: {filepath.name}")

        reader.fieldnames = [col.strip().lower() for col in reader.fieldnames]

        # Guard: required columns present?
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"CSV '{filepath.name}' is missing required columns: {missing}"
            )

        rows = [dict(row) for row in reader]

    logger.info(
        "Ingestion | file=%s | rows_read=%d", filepath.name, len(rows)
    )
    return rows


def read_files(
    filepaths: list[str | Path],
) -> dict[str, list[dict[str, Any]]]:

    total_files = len(filepaths)
    logger.info("Ingestion | starting batch | files_requested=%d", total_files)

    results: dict[str, list[dict[str, Any]]] = {}
    failed = 0

    for raw_path in filepaths:
        path = Path(raw_path)
        try:
            rows = _read_single_file(path)
            results[path.name] = rows
        except (FileNotFoundError, ValueError, OSError) as exc:
            failed += 1
            logger.error("Ingestion | file=%s | FAILED — %s", path.name, exc)

    succeeded = total_files - failed
    logger.info(
        "Ingestion | batch complete | succeeded=%d | failed=%d",
        succeeded,
        failed,
    )

    return results