"""Game initialization utilities: logging setup and project file loading.

Extracted from Game._setup_logging (L704-L732) and Game._load_property_types
(L691-L702) as part of Phase 1.5 refactoring.

Deep links:
  - Origin: src/engine/game.py#L691-L732
  - Spec: docs/game/specs/phase-1.5-game-refactoring.md
"""

import json
import logging
import logging.handlers
import os
from pathlib import Path
from typing import Any


def setup_logging(settings: Any) -> None:
    """Configure rotating file logging and console output.

    Extracted from Game._setup_logging. Creates logs/ directory if absent.
    Avoids adding duplicate handlers on re-initialization.

    Args:
        settings: Settings object with LOG_LEVEL attribute.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = str(Path(log_dir) / "game.log")

    logger = logging.getLogger()
    logger.setLevel(settings.LOG_LEVEL)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file, when="D", interval=1, backupCount=7
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Check if we already have our TimedRotatingFileHandler
    has_file_handler = any(
        isinstance(h, logging.handlers.TimedRotatingFileHandler) for h in logger.handlers
    )

    if not has_file_handler:
        # Remove any existing handlers (e.g. default StreamHandler) to prevent duplicate or unformatted logs
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)


def load_property_types(path: str) -> list:
    """Load propertyTypes array from a Tiled .tiled-project JSON file.

    Returns [] on any error (file not found, invalid JSON, missing key).
    Logs errors at ERROR level; does not raise.

    Extracted from Game._load_property_types (L691-L702).
    Note: original returned dict; spec mandates list to match the
    propertyTypes JSON array structure.

    Args:
        path: Absolute or relative path to the .tiled-project file.
    """
    if not os.path.exists(path):
        logging.error(f"Property types file not found: {path}")
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("propertyTypes", [])
    except (OSError, json.JSONDecodeError) as e:
        logging.error(f"Failed to load property types from {path}: {e}")
        return []
