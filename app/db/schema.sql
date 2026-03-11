CREATE TABLE IF NOT EXISTS expenses (
    id              SERIAL          PRIMARY KEY,
    date            DATE            NOT NULL,
    category        VARCHAR(50)     NOT NULL,
    description     TEXT,
    amount          NUMERIC(12, 2)  NOT NULL CHECK (amount > 0),
    currency        VARCHAR(10)     NOT NULL DEFAULT 'USD',
    submitted_by    VARCHAR(100)    NOT NULL,
    source_file     VARCHAR(255),                       -- which CSV this row came from
    ingested_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_expenses_date        ON expenses (date);
CREATE INDEX IF NOT EXISTS idx_expenses_category    ON expenses (category);
CREATE INDEX IF NOT EXISTS idx_expenses_submitted_by ON expenses (submitted_by);