from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, field_validator, model_validator, Field

from app.config import get_logger

logger = get_logger(__name__)


# ── Allowed categories ────────────────────────────────────────────────────────
class Category(str, Enum):
    FOOD        = "Food"
    TRAVEL      = "Travel"
    OFFICE      = "Office"
    SOFTWARE    = "Software"
    MARKETING   = "Marketing"
    UTILITIES   = "Utilities"
    OTHER       = "Other"


# ── Pydantic model ────────────────────────────────────────────────────────────
class ExpenseRecord(BaseModel):
    date:           date
    category:       Category
    description:    str | None  = None
    amount:         Decimal     = Field(..., gt=0, decimal_places=2)
    currency:       str         = "USD"
    submitted_by:   str

    # ── Field-level validators ────────────────────────────────────────────────
    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("submitted_by")
    @classmethod
    def non_empty_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("submitted_by cannot be empty")
        return v

    @field_validator("category", mode="before")
    @classmethod
    def normalise_category(cls, v: str) -> str:
        """Case-insensitive category matching."""
        return v.strip().title()

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> Any:
        """Accept ISO strings (YYYY-MM-DD) or pass through date objects."""
        if isinstance(v, str):
            return v.strip()
        return v

    # ── Model-level validators ────────────────────────────────────────────────
    @model_validator(mode="after")
    def description_stripped(self) -> "ExpenseRecord":
        if self.description:
            self.description = self.description.strip() or None
        return self


# ── Batch validation ──────────────────────────────────────────────────────────
def validate_rows(
    raw_rows: list[dict[str, Any]],
    source_file: str = "unknown",
) -> tuple[list[ExpenseRecord], list[dict]]:
    
    valid:  list[ExpenseRecord] = []
    errors: list[dict]          = []

    logger.info(
        "Preprocessing | file=%s | total_rows=%d", source_file, len(raw_rows)
    )

    for idx, row in enumerate(raw_rows, start=1):
        try:
            record = ExpenseRecord.model_validate(row)
            valid.append(record)
        except Exception as exc:          # pydantic.ValidationError
            errors.append({
                "row_index":  idx,
                "raw_data":   row,
                "errors":     str(exc),
            })
            logger.warning(
                "Preprocessing | file=%s | row=%d INVALID — %s",
                source_file, idx, exc,
            )

    logger.info(
        "Preprocessing | file=%s | valid=%d | invalid=%d",
        source_file, len(valid), len(errors),
    )

    return valid, errors