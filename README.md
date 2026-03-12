# Expense Processor

A CLI-based expense processing application that ingests CSV files, validates records, persists them to PostgreSQL, and surfaces spend analytics — all from a single command.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Data Flow](#data-flow)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Setup and Run](#setup-and-run)
  - [Prerequisites](#prerequisites)
  - [Local Setup](#local-setup)
  - [Docker Setup](#docker-setup)
- [CLI Reference](#cli-reference)
- [Running Tests](#running-tests)
- [Sample Analytics Output](#sample-analytics-output)
- [Git Workflow](#git-workflow)
- [Assumptions](#assumptions)
- [Challenges](#challenges)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                          CLI                                │
│                        app/cli.py                           │
│         ingest │ analytics │ init-db                        │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐
  │  Ingestion   │ │     DB       │ │      Analytics       │
  │  reader.py   │ │ connection.py│ │      summary.py      │
  │ validator.py │ │  queries.py  │ │                      │
  └──────┬───────┘ └──────┬───────┘ └──────────────────────┘
         │                │
         ▼                ▼
  ┌──────────────┐ ┌──────────────┐
  │  CSV Files   │ │  PostgreSQL  │
  │  data/*.csv  │ │  expenses    │
  └──────────────┘ └──────────────┘

  ┌──────────────────────────────┐
  │         config.py            │
  │  Settings + Logger factory   │
  │  (used by every module)      │
  └──────────────────────────────┘
```

**Tech stack**

| Layer          | Tool                            |
|----------------|---------------------------------|
| CLI            | Click 8                         |
| Validation     | Pydantic v2                     |
| ORM / Driver   | SQLAlchemy 2 + psycopg2         |
| Database       | PostgreSQL 15                   |
| Env vars       | python-dotenv                   |
| Logging        | Python stdlib `logging`         |
| Containerisation | Docker + Docker Compose       |
| Testing        | pytest                          |

---

## Data Flow

```
 CSV file(s)
     │
     ▼
 reader.py          — reads one or many CSVs into raw dicts
                      normalises headers to lowercase
                      raises per-file on missing required columns
                      skips unreadable files without aborting the batch
     │
     ▼
 validator.py       — validates every row with Pydantic ExpenseRecord
                      enforces category enum, amount > 0, non-empty submitter
                      separates valid records from error rows
                      invalid rows are logged and skipped, never crash the run
     │
     ▼
 queries.py         — bulk INSERT valid records into PostgreSQL
  insert_expenses()   wraps each file's batch in a transaction
                      rolls back on DB error, logs result
     │
     ▼
 analytics_summary() — GROUP BY month + category → total spend per cell
                       subquery AVG across all monthly totals
     │
     ▼
 summary.py         — formats and prints the analytics report
                      logs every metric to logs/expense_processor.log
```

**What gets logged at each stage**

| Stage          | Log content                                              |
|----------------|----------------------------------------------------------|
| Ingestion      | Files received, row count per file, batch totals         |
| Preprocessing  | Valid / invalid counts per file, per-row validation err  |
| DB Save        | Rows inserted per file, rollback events                  |
| Analytics      | Monthly breakdown, average monthly spend                 |

---

## Project Structure

```
expense-processor/
│
├── app/
│   ├── cli.py                  # Click commands (ingest, analytics, init-db)
│   ├── config.py               # Settings (dotenv) + get_logger() factory
│   │
│   ├── ingestion/
│   │   ├── reader.py           # Multi-file CSV reader
│   │   └── validator.py        # Pydantic ExpenseRecord model + batch validation
│   │
│   ├── db/
│   │   ├── connection.py       # SQLAlchemy engine, session factory, init_db()
│   │   ├── schema.sql          # DDL — auto-applied on first Postgres boot
│   │   └── queries.py          # insert_expenses(), analytics queries
│   │
│   └── analytics/
│       └── summary.py          # Formats + logs the analytics report
│
├── tests/
│   ├── conftest.py             # Shared pytest fixtures
│   ├── test_validator.py       # ExpenseRecord model unit tests
│   ├── test_validate_rows.py   # validate_rows() batch function tests
│   ├── test_reader.py          # CSV reader unit tests
│   └── test_config.py          # Settings + logger factory tests
│
├── data/                       # Drop CSV files here
│   ├── expenses_jan.csv
│   └── expenses_feb.csv
│
├── logs/                       # Log files written here (gitignored)
├── .env                        # Local env vars (gitignored)
├── .env.example                # Template — copy to .env
├── requirements.txt
├── pyproject.toml              # pytest config
├── Dockerfile
└── docker-compose.yml
```

---

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS expenses (
    id              SERIAL          PRIMARY KEY,
    date            DATE            NOT NULL,
    category        VARCHAR(50)     NOT NULL,
    description     TEXT,
    amount          NUMERIC(12, 2)  NOT NULL CHECK (amount > 0),
    currency        VARCHAR(10)     NOT NULL DEFAULT 'USD',
    submitted_by    VARCHAR(100)    NOT NULL,
    source_file     VARCHAR(255),        -- tracks which CSV this row came from
    ingested_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_expenses_date         ON expenses (date);
CREATE INDEX idx_expenses_category     ON expenses (category);
CREATE INDEX idx_expenses_submitted_by ON expenses (submitted_by);
```

**Allowed categories:** `Food` · `Travel` · `Office` · `Software` · `Marketing` · `Utilities` · `Other`

---

## Setup and Run

### Prerequisites

- Docker and Docker Compose (recommended), **or**
- Python 3.12+ and a running PostgreSQL 15 instance

---

### Local Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd expense-processor

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
.env
# Edit .env — set POSTGRES_HOST=localhost and your DB credentials

# 5. Apply the schema (run once)
python -m app.cli init-db

# 6. Run ingestion
python -m app.cli ingest --files data/expenses_jan.csv data/expenses_feb.csv

# 7. Run analytics only (on existing data)
python -m app.cli analytics
```

---

### Docker Setup

```bash
# 1. Configure environment
.env          

# 2. Build and start Postgres
docker compose up -d postgres

# 3. Ingest CSV files + view analytics  (full pipeline, single command)
docker compose run --rm --remove-orphans app ingest --files data/expenses_jan.csv data/expenses_feb.csv

# 4. Analytics only (on data already in the DB)
docker compose run --rm --remove-orphans app analytics

# 5. Validate files without writing to the DB
docker compose run --rm --remove-orphans app ingest --files data/expenses_jan.csv --dry-run

# 6. Bootstrap schema manually (not usually needed — Postgres does this on first boot)
docker compose run --rm --remove-orphans app init-db
```

**Tip — create a shell alias to avoid typing the flags every time:**

```bash
alias dcr="docker compose run --rm --remove-orphans"

dcr app ingest --files data/expenses_jan.csv data/expenses_feb.csv
dcr app analytics
dcr test
```

---

## CLI Reference

```
Commands:
  ingest      Read CSVs → validate → insert → analytics
  analytics   Run the analytics report on existing DB data
  init-db     Apply schema.sql (idempotent, safe to re-run)

Options for `ingest`:
  -f, --files PATH        One or more CSV file paths  [required]
  --dry-run               Validate without writing to the DB
  --skip-analytics        Insert records but skip the analytics report
```

---

## Running Tests

```bash
# Via Docker (recommended)
docker compose run --rm --remove-orphans test

# Locally
pytest

# Useful flags
pytest -x                          # stop on first failure
pytest tests/test_validator.py     # single file
```

**Test coverage (31 tests across 4 files)**

| File                    | What it tests                                      |
|-------------------------|----------------------------------------------------|
| `test_validator.py`     | Pydantic model — valid parse, field normalisation, rejection cases |
| `test_validate_rows.py` | Batch validation — splits, error structure, empty input |
| `test_reader.py`        | CSV reader — row counts, header normalisation, error handling |
| `test_config.py`        | Settings, logger handlers, no duplicate handlers, log file creation |

---

## Sample Analytics Output

Running `ingest` against the two sample files (`expenses_jan.csv` + `expenses_feb.csv`) produces the following output. Note that `expenses_feb.csv` contains 2 intentionally invalid rows which are caught and skipped.

```
────────────────────────────────────────────────────────────
  EXPENSE PROCESSOR  |  LOG_LEVEL=INFO
────────────────────────────────────────────────────────────

  Database schema ready

  Reading 2 file(s)…

  Validating rows…
    expenses_jan.csv                ✓  10 valid   ✗  0 invalid
    expenses_feb.csv                ✓   9 valid   ✗  2 invalid
      row  4: INVALID_CAT is not a valid Category
      row 10: amount must be greater than 0 / submitted_by cannot be empty

  Total valid: 19  |  Total invalid: 2

  Saving to database…
    expenses_jan.csv                →  10 rows inserted
    expenses_feb.csv                →   9 rows inserted

  19 total rows saved.

────────────────────────────────────────────────────────────
  SPEND BY MONTH AND CATEGORY
────────────────────────────────────────────────────────────

  2024-01  (month total: $  1,451.74)
  Category        Count        Total
  ------------------------------------
  Travel              2  $    443.40
  Food                3  $    314.60
  Utilities           1  $    310.75
  Marketing           1  $    250.00
  Office              2  $    113.99
  Software            1  $     19.00

  2024-02  (month total: $  1,037.90)
  Category        Count        Total
  ------------------------------------
  Travel              2  $    395.00
  Software            2  $    194.90
  Marketing           1  $    180.00
  Food                2  $    168.00
  Utilities           1  $     87.50
  Office              1  $     12.50

────────────────────────────────────────────────────────────
  AVERAGE MONTHLY EXPENDITURE
────────────────────────────────────────────────────────────
  Avg spend / month : $  1,244.82

────────────────────────────────────────────────────────────
```

**SQL behind the analytics**

```sql
-- Spend grouped by month and category
SELECT
    TO_CHAR(date, 'YYYY-MM')        AS month,
    category,
    COUNT(*)                        AS expense_count,
    ROUND(SUM(amount)::NUMERIC, 2)  AS total_spend
FROM expenses
GROUP BY TO_CHAR(date, 'YYYY-MM'), category
ORDER BY month, total_spend DESC;

-- Average monthly expenditure
SELECT ROUND(AVG(monthly_total)::NUMERIC, 2) AS avg_monthly_spend
FROM (
    SELECT SUM(amount) AS monthly_total
    FROM expenses
    GROUP BY TO_CHAR(date, 'YYYY-MM')
) monthly;
```

---

## Git Workflow

```
main                    — stable, production-ready code
  └── develop           — integration branch
        ├── feature/*   — individual feature branches
        └── fix/*       — bug fix branches
```

**Branch naming**

```
feature/add-duplicate-detection
feature/ingestion-audit-table
fix/invalid-category-handling
fix/docker-entrypoint
```

**Commit message convention**

```
<type>: <short description>

feat:     new feature
fix:      bug fix
test:     adding or updating tests
refactor: code change that doesn't affect behaviour
docs:     documentation only
chore:    config, tooling, dependencies
```

**Feature workflow**

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create a feature branch
git checkout -b feature/add-duplicate-detection

# Work, commit in small logical steps
git add app/db/queries.py
git commit -m "add ingested_files audit table"

git add tests/test_duplicate_detection.py
git commit -m "add duplicate file detection tests"

# Push and open a PR into develop
git push origin feature/add-duplicate-detection

# After review, merge into develop
# After QA on develop, merge develop → main and tag a release
git tag -a v1.1.0 -m "Add duplicate file detection"
git push origin v1.1.0
```

**What to always gitignore**

```
.env                  # real secrets never go to version control
logs/*.log            # runtime artefacts
__pycache__/
.venv/
```

---

## Assumptions

- **CSV format is fixed.** Required columns are `date`, `category`, `amount`, and `submitted_by`. Additional columns (`description`, `currency`) are optional and default gracefully.
- **One currency per deployment.** Currency is stored as-is; no conversion logic is applied. USD is the default.
- **Categories are a closed enum.** Any category not in `Food / Travel / Office / Software / Marketing / Utilities / Other` is rejected at validation time. The enum list is intentionally small for this scope.
- **A file may contain partial valid data.** Invalid rows are skipped and logged; valid rows in the same file are still inserted. A file is not treated as all-or-nothing at the row level.
- **Schema is applied externally.** `schema.sql` is mounted into Postgres's `docker-entrypoint-initdb.d/` directory, which runs it automatically on first boot. The `init-db` CLI command exists for local / manual setups.
- **No authentication layer.** The tool is designed for internal / local use. Access control is delegated to the PostgreSQL credentials in `.env`.
- **Dates are ISO 8601.** Dates in CSVs are expected in `YYYY-MM-DD` format. Pydantic's date parser will reject anything it cannot parse.

---

## Challenges

**1. Docker entrypoint vs CLI subcommands**
The initial `CMD ["expense-processor", "--help"]` caused Docker to treat `ingest` as a binary to execute rather than a subcommand to pass. Fixed by splitting into `ENTRYPOINT ["python", "-m", "app.cli"]` + `CMD ["--help"]`, with `PYTHONPATH=/app` set so the `app` package resolves correctly without a package install step.

**2. Editable install failures inside Docker**
`pip install -e .` with `setuptools.backends.legacy:build` failed on the slim Python 3.12 image because the bundled `setuptools` was too old to support that backend name. Resolved by dropping the editable install entirely in favour of `PYTHONPATH=/app`, which is simpler and has no build-time dependencies.

**3. Orphan container warnings**
`docker compose run` creates short-lived containers that Docker flags as orphans on the next run. Addressed by always pairing `--rm` with `--remove-orphans` and documenting an alias for convenience.

**4. Row-level vs file-level error handling**
Deciding the right granularity for error handling — should one bad row fail the whole file, or just be skipped? The chosen approach (skip invalid rows, insert valid ones, log all errors) matches real-world ETL expectations but required careful separation between the reader (IO errors → skip file) and the validator (data errors → skip row).