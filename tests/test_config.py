import logging
from app.config import settings, get_logger


class TestSettings:

    def test_database_url_contains_host(self):
        assert settings.POSTGRES_HOST in settings.database_url

    def test_database_url_contains_db_name(self):
        assert settings.POSTGRES_DB in settings.database_url

    def test_database_url_scheme(self):
        assert settings.database_url.startswith("postgresql+psycopg2://")

    def test_log_dir_is_set(self):
        assert settings.LOG_DIR is not None
        assert str(settings.LOG_DIR) != ""


class TestGetLogger:

    def test_returns_logger_with_correct_name(self):
        logger = get_logger("test.mymodule")
        assert logger.name == "test.mymodule"

    def test_logger_has_two_handlers(self):
        logger = get_logger("test.handlers")
        handler_types = [type(h) for h in logger.handlers]

        assert logging.StreamHandler in handler_types
        assert logging.FileHandler  in handler_types

    def test_no_duplicate_handlers_on_repeated_calls(self):
        name = "test.dedup"
        logger_a = get_logger(name)
        handler_count_first = len(logger_a.handlers)

        logger_b = get_logger(name)
        handler_count_second = len(logger_b.handlers)

        assert logger_a is logger_b
        assert handler_count_first == handler_count_second

    def test_log_file_created(self):
        get_logger("test.file_creation")
        log_path = settings.LOG_DIR / settings.LOG_FILE
        assert log_path.exists()