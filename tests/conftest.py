

import pytest
from pathlib import Path


# ── Raw row fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def valid_row() -> dict:
    return {
        "date":         "2024-01-15",
        "category":     "Food",
        "description":  "Team lunch",
        "amount":       "42.50",
        "currency":     "usd",           # intentionally lowercase — validator should upper it
        "submitted_by": "alice@company.com",
    }


@pytest.fixture
def valid_rows() -> list[dict]:
    return [
        {"date": "2024-01-05", "category": "Food",     "amount": "87.50",  "currency": "USD", "submitted_by": "alice@company.com", "description": "Lunch"},
        {"date": "2024-01-08", "category": "travel",   "amount": "23.40",  "currency": "USD", "submitted_by": "bob@company.com",   "description": "Uber"},
        {"date": "2024-01-10", "category": "SOFTWARE", "amount": "19.00",  "currency": "USD", "submitted_by": "alice@company.com", "description": "GitHub"},
    ]


@pytest.fixture
def mixed_rows() -> list[dict]:
    return [
        {"date": "2024-02-01", "category": "Office",   "amount": "45.00",  "currency": "USD", "submitted_by": "carol@company.com", "description": "Supplies"},
        {"date": "2024-02-02", "category": "BADCAT",   "amount": "30.00",  "currency": "USD", "submitted_by": "bob@company.com",   "description": "Unknown"},   # bad category
        {"date": "2024-02-03", "category": "Travel",   "amount": "-99.00", "currency": "USD", "submitted_by": "dave@company.com",  "description": "Refund"},    # negative amount
        {"date": "2024-02-04", "category": "Food",     "amount": "55.00",  "currency": "USD", "submitted_by": "",                  "description": "Dinner"},    # empty submitted_by
        {"date": "2024-02-05", "category": "Software", "amount": "15.00",  "currency": "USD", "submitted_by": "alice@company.com", "description": "Zoom"},
    ]


# ── CSV file fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def valid_csv(tmp_path: Path) -> Path:
    content = (
        "date,category,description,amount,currency,submitted_by\n"
        "2024-01-05,Food,Team lunch,87.50,USD,alice@company.com\n"
        "2024-01-08,Travel,Uber ride,23.40,USD,bob@company.com\n"
        "2024-01-10,Software,GitHub,19.00,USD,alice@company.com\n"
    )
    p = tmp_path / "test_expenses.csv"
    p.write_text(content)
    return p


@pytest.fixture
def missing_columns_csv(tmp_path: Path) -> Path:
    content = (
        "date,category,description,submitted_by\n"
        "2024-01-05,Food,Lunch,alice@company.com\n"
    )
    p = tmp_path / "bad_columns.csv"
    p.write_text(content)
    return p
