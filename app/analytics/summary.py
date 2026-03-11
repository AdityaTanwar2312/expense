from __future__ import annotations

from typing import Any

from app.config import get_logger
from app.db.queries import (
    analytics_summary,
    monthly_spend_ranked,
    top_spenders,
    total_and_avg_by_category,
)

logger = get_logger(__name__)

# ── Formatting helpers ────────────────────────────────────────────────────────

def _divider(char: str = "─", width: int = 60) -> str:
    return char * width


def _fmt_money(value: Any) -> str:
    try:
        return f"${float(value):>10,.2f}"
    except (TypeError, ValueError):
        return f"{'N/A':>11}"


def _section(title: str) -> str:
    return f"\n{_divider()}\n  {title}\n{_divider()}"


# ── Main entry point ──────────────────────────────────────────────────────────

def run_and_log_analytics() -> None:
    logger.info("Analytics | starting full analytics run")

    # ── 1. High-level summary ─────────────────────────────────────────────────
    summary = analytics_summary()

    print(_section("EXPENSE ANALYTICS SUMMARY"))
    if not summary:
        print("  No data found in the database.")
        logger.warning("Analytics | summary returned no data")
        return

    print(f"  Total records    : {summary.get('total_records', 0):,}")
    print(f"  Grand total      : {_fmt_money(summary.get('grand_total'))}")
    print(f"  Overall avg      : {_fmt_money(summary.get('overall_avg'))}")
    print(f"  Date range       : {summary.get('earliest_date')}  →  {summary.get('latest_date')}")
    print(f"  Top category     : {summary.get('top_category')}  "
          f"({_fmt_money(summary.get('top_category_spend'))})")
    print(f"  Top spender      : {summary.get('top_spender')}  "
          f"({_fmt_money(summary.get('top_spender_total'))})")

    # ── 2. Spend by category (SUM + AVG) ─────────────────────────────────────
    by_category = total_and_avg_by_category()

    print(_section("SPEND BY CATEGORY  (SUM + AVG)"))
    header = f"  {'Category':<14} {'Count':>6}  {'Total':>11}  {'Avg':>11}  {'Min':>10}  {'Max':>10}"
    print(header)
    print(f"  {_divider('-', 58)}")

    for row in by_category:
        print(
            f"  {row['category']:<14} "
            f"{row['expense_count']:>6}  "
            f"{_fmt_money(row['total_spend'])}  "
            f"{_fmt_money(row['avg_spend'])}  "
            f"{_fmt_money(row['min_spend'])}  "
            f"{_fmt_money(row['max_spend'])}"
        )
        logger.info(
            "Analytics | category=%s | count=%s | total=%s | avg=%s",
            row["category"], row["expense_count"],
            row["total_spend"], row["avg_spend"],
        )

    # ── 3. Monthly spend ranked ───────────────────────────────────────────────
    monthly = monthly_spend_ranked()

    print(_section("MONTHLY SPEND  (GROUP BY month, ORDER BY total DESC)"))
    header = f"  {'Month':<10} {'Count':>6}  {'Monthly Total':>14}  {'Avg / Expense':>14}"
    print(header)
    print(f"  {_divider('-', 50)}")

    for row in monthly:
        print(
            f"  {row['month']:<10} "
            f"{row['expense_count']:>6}  "
            f"{_fmt_money(row['monthly_total']):>14}  "
            f"{_fmt_money(row['avg_per_expense']):>14}"
        )
        logger.info(
            "Analytics | month=%s | count=%s | total=%s",
            row["month"], row["expense_count"], row["monthly_total"],
        )

    # ── 4. Top spenders ───────────────────────────────────────────────────────
    spenders = top_spenders()

    print(_section("TOP SPENDERS  (GROUP BY submitter, ORDER BY total DESC)"))
    header = f"  {'Submitted By':<28} {'Count':>6}  {'Total':>11}  {'Avg':>11}"
    print(header)
    print(f"  {_divider('-', 58)}")

    for rank, row in enumerate(spenders, start=1):
        print(
            f"  {rank}. {row['submitted_by']:<26} "
            f"{row['expense_count']:>6}  "
            f"{_fmt_money(row['total_spend'])}  "
            f"{_fmt_money(row['avg_spend'])}"
        )
        logger.info(
            "Analytics | rank=%d | submitter=%s | total=%s | count=%s",
            rank, row["submitted_by"], row["total_spend"], row["expense_count"],
        )

    print(f"\n{_divider()}\n")
    logger.info("Analytics | run complete")