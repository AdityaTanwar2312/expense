from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.config import get_logger
from app.db.connections import get_session
from app.ingestion.validator import ExpenseRecord

logger = get_logger(__name__)


# INSERT

def insert_expenses(
    records: list[ExpenseRecord],
    source_file: str = "unknown",
) -> int:
    if not records:
        logger.warning("DB Save | source=%s | no records to insert", source_file)
        return 0

    rows = [
        {
            "date":         r.date,
            "category":     r.category.value,
            "description":  r.description,
            "amount":       float(r.amount),
            "currency":     r.currency,
            "submitted_by": r.submitted_by,
            "source_file":  source_file,
        }
        for r in records
    ]

    insert_sql = text("""
        INSERT INTO expenses
            (date, category, description, amount, currency, submitted_by, source_file)
        VALUES
            (:date, :category, :description, :amount, :currency, :submitted_by, :source_file)
    """)

    session = get_session()
    try:
        session.execute(insert_sql, rows)
        session.commit()
        logger.info(
            "DB Save | source=%s | rows_inserted=%d", source_file, len(rows)
        )
        return len(rows)
    except Exception as exc:
        session.rollback()
        logger.error(
            "DB Save | source=%s | FAILED — rolling back | error=%s",
            source_file, exc,
        )
        raise
    finally:
        session.close()


# AGGREGATION — SUM + AVG per category

def total_and_avg_by_category() -> list[dict[str, Any]]:
    sql = text("""
        SELECT
            category,
            COUNT(*)                        AS expense_count,
            ROUND(SUM(amount)::NUMERIC, 2)  AS total_spend,
            ROUND(AVG(amount)::NUMERIC, 2)  AS avg_spend,
            ROUND(MIN(amount)::NUMERIC, 2)  AS min_spend,
            ROUND(MAX(amount)::NUMERIC, 2)  AS max_spend
        FROM expenses
        GROUP BY category
        ORDER BY total_spend DESC
    """)

    session = get_session()
    try:
        result = session.execute(sql)
        rows = [dict(row._mapping) for row in result]
        logger.info("Analytics | total_and_avg_by_category | categories_found=%d", len(rows))
        return rows
    finally:
        session.close()


# GROUP BY month + ORDER BY spend

def monthly_spend_ranked() -> list[dict[str, Any]]:
    sql = text("""
        SELECT
            TO_CHAR(date, 'YYYY-MM')        AS month,
            COUNT(*)                        AS expense_count,
            ROUND(SUM(amount)::NUMERIC, 2)  AS monthly_total,
            ROUND(AVG(amount)::NUMERIC, 2)  AS avg_per_expense
        FROM expenses
        GROUP BY TO_CHAR(date, 'YYYY-MM')
        ORDER BY monthly_total DESC
    """)

    session = get_session()
    try:
        result = session.execute(sql)
        rows = [dict(row._mapping) for row in result]
        logger.info("Analytics | monthly_spend_ranked | months_found=%d", len(rows))
        return rows
    finally:
        session.close()


# TOP SPENDERS

def top_spenders() -> list[dict[str, Any]]:
    sql = text("""
        SELECT
            submitted_by,
            COUNT(*)                        AS expense_count,
            ROUND(SUM(amount)::NUMERIC, 2)  AS total_spend,
            ROUND(AVG(amount)::NUMERIC, 2)  AS avg_spend
        FROM expenses
        GROUP BY submitted_by
        ORDER BY total_spend DESC
    """)

    session = get_session()
    try:
        result = session.execute(sql)
        rows = [dict(row._mapping) for row in result]
        logger.info("Analytics | top_spenders | submitters_found=%d", len(rows))
        return rows
    finally:
        session.close()


# ─────────────────────────────────────────────────────────────────────────────
# FULL ANALYTICAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

 
def analytics_summary() -> dict[str, Any]:
    breakdown_sql = text("""
        SELECT
            TO_CHAR(date, 'YYYY-MM')        AS month,
            category,
            COUNT(*)                        AS expense_count,
            ROUND(SUM(amount)::NUMERIC, 2)  AS total_spend
        FROM expenses
        GROUP BY TO_CHAR(date, 'YYYY-MM'), category
        ORDER BY month, total_spend DESC
    """)
 
    avg_sql = text("""
        SELECT ROUND(AVG(monthly_total)::NUMERIC, 2) AS avg_monthly_spend
        FROM (
            SELECT SUM(amount) AS monthly_total
            FROM expenses
            GROUP BY TO_CHAR(date, 'YYYY-MM')
        ) monthly
    """)
 
    session = get_session()
    try:
        breakdown = [
            dict(row._mapping)
            for row in session.execute(breakdown_sql)
        ]
        avg_row  = session.execute(avg_sql).fetchone()
        avg_monthly = float(avg_row[0]) if avg_row and avg_row[0] else 0.0
 
        summary = {
            "breakdown":        breakdown,
            "avg_monthly_spend": avg_monthly,
        }
 
        logger.info(
            "Analytics | summary | months=%d | avg_monthly_spend=%s",
            len({r["month"] for r in breakdown}),
            avg_monthly,
        )
        return summary
    finally:
        session.close()