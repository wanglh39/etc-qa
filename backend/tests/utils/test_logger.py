from utils.logger import get_logger, setup_logging


class TestLogger:
    def test_get_logger_returns_logger(self):
        logger = get_logger("test")
        assert logger is not None
        assert logger.name == "test"

    def test_get_logger_same_name_returns_same(self):
        logger1 = get_logger("same")
        logger2 = get_logger("same")
        assert logger1 is logger2

    def test_setup_logging_does_not_raise(self):
        setup_logging()
