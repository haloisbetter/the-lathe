"""
Logging setup for The Lathe.

Configures Python's logging system based on configuration.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


_INITIALIZED = False


def setup_logging(
    level: str = "INFO",
    format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    log_file: Optional[str] = None,
) -> None:
    """
    Setup logging for The Lathe.

    This should be called once at application startup.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_str: Log message format string
        log_file: Optional path to log file
    """
    global _INITIALIZED

    if _INITIALIZED:
        return

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(format_str)

    handlers = []

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
