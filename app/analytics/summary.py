from __future__ import annotations

from itertools import groupby
from typing import Any

from app.config import get_logger
from app.db.queries import analytics_summary

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
    logger.info("Analytics | starting analytics run")

    summary     = analytics_summary()
    breakdown   = summary.get("breakdown", [])
    avg_monthly = summary.get("avg_monthly_spend", 0.0)

    if not breakdown:
        print("  No data found in the database.")
        logger.warning("Analytics | no data found")
        return

    # ── Spend by month and category ───────────────────────────────────────────
    print(_section("SPEND BY MONTH AND CATEGORY"))

    for month, rows in groupby(breakdown, key=lambda r: r["month"]):
        rows        = list(rows)
        month_total = sum(float(r["total_spend"]) for r in rows)

        print(f"\n  {month}  (month total: {_fmt_money(month_total)})")
        print(f"  {'Category':<14} {'Count':>6}  {'Total':>11}")
        print(f"  {_divider('-', 36)}")

        for row in rows:
            print(
                f"  {row['category']:<14} "
                f"{row['expense_count']:>6}  "
                f"{_fmt_money(row['total_spend'])}"
            )
            logger.info(
                "Analytics | month=%s | category=%s | count=%s | total=%s",
                row["month"], row["category"],
                row["expense_count"], row["total_spend"],
            )

    # ── Average monthly spend ─────────────────────────────────────────────────
    print(_section("AVERAGE MONTHLY EXPENDITURE"))
    print(f"  Avg spend / month : {_fmt_money(avg_monthly)}")
    logger.info("Analytics | avg_monthly_spend=%s", avg_monthly)

    print(f"\n{_divider()}\n")
    logger.info("Analytics | run complete")