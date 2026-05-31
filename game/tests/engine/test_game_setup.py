import logging
import logging.handlers
from unittest.mock import MagicMock

from src.engine import game_setup


def test_game_setup_import():
    assert True


def test_setup_logging_adds_handlers_and_prevents_duplication():
    # Setup mock settings
    mock_settings = MagicMock()
    mock_settings.LOG_LEVEL = logging.INFO

    # Obtain root logger
    logger = logging.getLogger()

    # Store original handlers to restore them after the test
    original_handlers = list(logger.handlers)

    try:
        # 1. Simulate Python's default handler pre-existing
        for h in list(logger.handlers):
            logger.removeHandler(h)

        dummy_handler = logging.StreamHandler()
        logger.addHandler(dummy_handler)
        assert len(logger.handlers) == 1

        # 2. Run setup_logging and check they are properly configured and default handler is removed
        game_setup.setup_logging(mock_settings)

        # We expect exactly one TimedRotatingFileHandler and one StreamHandler (console)
        assert len(logger.handlers) == 2

        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]
        console_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]

        assert len(file_handlers) == 1
        assert len(console_handlers) == 1

        # 3. Call setup_logging again to verify no duplicate handlers are added
        game_setup.setup_logging(mock_settings)
        assert len(logger.handlers) == 2

    finally:
        # Restore original handlers
        for h in list(logger.handlers):
            logger.removeHandler(h)
        for h in original_handlers:
            logger.addHandler(h)
