import pytest
from decimal import Decimal
from pydantic import ValidationError

from app.ingestion.validator import ExpenseRecord, Category


class TestExpenseRecordValid:

    def test_valid_row_parses(self, valid_row):
        record = ExpenseRecord.model_validate(valid_row)

        assert record.amount == Decimal("42.50")
        assert record.submitted_by == "alice@company.com"
        assert record.category == Category.FOOD

    def test_currency_is_uppercased(self, valid_row):
        valid_row["currency"] = "usd"
        record = ExpenseRecord.model_validate(valid_row)
        assert record.currency == "USD"

    def test_category_is_case_insensitive(self, valid_row):
        for variant in ["food", "FOOD", "fOoD"]:
            valid_row["category"] = variant
            record = ExpenseRecord.model_validate(valid_row)
            assert record.category == Category.FOOD

    def test_description_is_optional(self, valid_row):
        valid_row.pop("description", None)
        record = ExpenseRecord.model_validate(valid_row)
        assert record.description is None


class TestExpenseRecordInvalid:

    def test_negative_amount_rejected(self, valid_row):
        valid_row["amount"] = "-10.00"
        with pytest.raises(ValidationError, match="greater than 0"):
            ExpenseRecord.model_validate(valid_row)

    def test_zero_amount_rejected(self, valid_row):
        valid_row["amount"] = "0.00"
        with pytest.raises(ValidationError, match="greater than 0"):
            ExpenseRecord.model_validate(valid_row)

    def test_invalid_category_rejected(self, valid_row):
        valid_row["category"] = "UNICORN"
        with pytest.raises(ValidationError):
            ExpenseRecord.model_validate(valid_row)

    def test_empty_submitted_by_rejected(self, valid_row):
        with pytest.raises(ValidationError, match="submitted_by cannot be empty"):
            ExpenseRecord.model_validate(valid_row)

    def test_invalid_date_rejected(self, valid_row):
        valid_row["date"] = "not-a-date"
        with pytest.raises(ValidationError):
            ExpenseRecord.model_validate(valid_row)
