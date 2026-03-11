from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.config import get_logger
from app.db.connections import get_session
from app.ingestion.validator import ExpenseRecord

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# INSERT
# ─────────────────────────────────────────────────────────────────────────────

def insert_expenses(
    records: list[ExpenseRecord],
    source_file: str = "unknown",
) -> int:
    """
    Bulk-insert a list of validated ExpenseRecord objects.

    Returns the number of rows successfully inserted.
    Rolls back the entire batch on any DB error to keep the table consistent.
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# AGGREGATION — SUM + AVG per category
# ─────────────────────────────────────────────────────────────────────────────

def total_and_avg_by_category() -> list[dict[str, Any]]:
    """
    SELECT category,
           COUNT(*)        AS expense_count,
           SUM(amount)     AS total_spend,
           AVG(amount)     AS avg_spend,
           MIN(amount)     AS min_spend,
           MAX(amount)     AS max_spend
    FROM expenses
    GROUP BY category
    ORDER BY total_spend DESC
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# GROUP BY month + ORDER BY spend
# ─────────────────────────────────────────────────────────────────────────────

def monthly_spend_ranked() -> list[dict[str, Any]]:
    """
    SELECT year, month, SUM(amount) AS monthly_total
    FROM expenses
    GROUP BY year, month
    ORDER BY monthly_total DESC
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# TOP SPENDERS
# ─────────────────────────────────────────────────────────────────────────────

def top_spenders() -> list[dict[str, Any]]:
    """
    SELECT submitted_by, SUM(amount), COUNT(*) expense_count
    FROM expenses
    GROUP BY submitted_by
    ORDER BY total_spend DESC
    """
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
    """
    Single-query analytical snapshot:
      - total expenses + grand total spend
      - date range (earliest → latest)
      - top category by spend
      - top spender by total amount
      - currency breakdown
    """
    sql = text("""
        WITH base AS (
            SELECT
                COUNT(*)                            AS total_records,
                ROUND(SUM(amount)::NUMERIC, 2)      AS grand_total,
                ROUND(AVG(amount)::NUMERIC, 2)      AS overall_avg,
                MIN(date)                           AS earliest_date,
                MAX(date)                           AS latest_date
            FROM expenses
        ),
        top_cat AS (
            SELECT category, ROUND(SUM(amount)::NUMERIC, 2) AS cat_total
            FROM expenses
            GROUP BY category
            ORDER BY cat_total DESC
            LIMIT 1
        ),
        top_person AS (
            SELECT submitted_by, ROUND(SUM(amount)::NUMERIC, 2) AS person_total
            FROM expenses
            GROUP BY submitted_by
            ORDER BY person_total DESC
            LIMIT 1
        )
        SELECT
            base.total_records,
            base.grand_total,
            base.overall_avg,
            base.earliest_date,
            base.latest_date,
            top_cat.category        AS top_category,
            top_cat.cat_total       AS top_category_spend,
            top_person.submitted_by AS top_spender,
            top_person.person_total AS top_spender_total
        FROM base, top_cat, top_person
    """)

    session = get_session()
    try:
        result = session.execute(sql)
        row = result.fetchone()
        summary = dict(row._mapping) if row else {}
        logger.info(
            "Analytics | summary | total_records=%s | grand_total=%s | "
            "date_range=%s → %s | top_category=%s | top_spender=%s",
            summary.get("total_records"),
            summary.get("grand_total"),
            summary.get("earliest_date"),
            summary.get("latest_date"),
            summary.get("top_category"),
            summary.get("top_spender"),
        )
        return summary
    finally:
        session.close()