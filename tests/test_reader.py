import pytest
from pathlib import Path

from app.ingestion.reader import read_files, _read_single_file, REQUIRED_COLUMNS


class TestReadSingleFile:

    def test_reads_correct_row_count(self, valid_csv):
        rows = _read_single_file(valid_csv)
        assert len(rows) == 3

    def test_headers_are_normalised_to_lowercase(self, valid_csv):
        rows = _read_single_file(valid_csv)
        for row in rows:
            for key in row:
                assert key == key.lower(), f"Key '{key}' is not lowercase"

    def test_all_required_columns_present(self, valid_csv):
        rows = _read_single_file(valid_csv)
        for row in rows:
            for col in REQUIRED_COLUMNS:
                assert col in row

    def test_missing_required_columns_raises(self, missing_columns_csv):
        with pytest.raises(ValueError, match="missing required columns"):
            _read_single_file(missing_columns_csv)

    def test_nonexistent_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _read_single_file(tmp_path / "ghost.csv")

    def test_non_csv_extension_raises(self, tmp_path):
        bad_file = tmp_path / "data.xlsx"
        bad_file.write_text("some content")
        with pytest.raises(ValueError, match=".csv"):
            _read_single_file(bad_file)


class TestReadFiles:

    def test_valid_file_appears_in_results(self, valid_csv):
        results = read_files([valid_csv])
        assert valid_csv.name in results
        assert len(results[valid_csv.name]) == 3

    def test_missing_file_is_skipped_not_raised(self, tmp_path):
        ghost = tmp_path / "missing.csv"
        results = read_files([ghost])
        assert results == {}

    def test_mixed_batch_skips_bad_keeps_good(self, valid_csv, tmp_path):
        ghost = tmp_path / "missing.csv"
        results = read_files([valid_csv, ghost])

        assert valid_csv.name in results
        assert "missing.csv" not in results
