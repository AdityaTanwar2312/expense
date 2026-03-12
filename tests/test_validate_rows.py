from app.ingestion.validator import validate_rows


class TestValidateRows:

    def test_all_valid_rows(self, valid_rows):
        valid, errors = validate_rows(valid_rows, source_file="test.csv")

        assert len(valid) == len(valid_rows)
        assert errors == []

    def test_mixed_batch_splits_correctly(self, mixed_rows):
        
        valid, errors = validate_rows(mixed_rows, source_file="mixed.csv")

        assert len(valid) == 2
        assert len(errors) == 3

    def test_invalid_rows_carry_correct_index(self, mixed_rows):
        _, errors = validate_rows(mixed_rows, source_file="mixed.csv")

        error_indices = [e["row_index"] for e in errors]
        assert error_indices == [2, 3, 4]

    def test_error_dict_contains_raw_data(self, mixed_rows):
        _, errors = validate_rows(mixed_rows, source_file="mixed.csv")

        for err in errors:
            assert "row_index" in err
            assert "raw_data"  in err
            assert "errors"    in err

    def test_empty_input_returns_empty(self):
        valid, errors = validate_rows([], source_file="empty.csv")

        assert valid  == []
        assert errors == []
