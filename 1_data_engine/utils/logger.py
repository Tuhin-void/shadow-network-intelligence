"""
Logger - Logging configuration for the data engine
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    Configure logging for the data engine.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file logging
        format_string: Custom format string

    Returns:
        Configured logger
    """
    if format_string is None:
        format_string = "%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s"

    formatter = logging.Formatter(format_string)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module"""
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capability to any class"""

    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, "_logger"):
            self._logger = logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)
        return self._logger


class ProgressLogger:
    """Logger for tracking progress of long-running operations"""

    def __init__(self, total: int, name: str = "Operation", logger: Optional[logging.Logger] = None):
        self.total = total
        self.current = 0
        self.name = name
        self.logger = logger or logging.getLogger("progress")
        self.start_time = datetime.now()

    def update(self, increment: int = 1) -> None:
        self.current += increment
        if self.current % max(1, self.total // 20) == 0 or self.current == self.total:
            pct = (self.current / self.total) * 100
            elapsed = (datetime.now() - self.start_time).total_seconds()
            rate = self.current / elapsed if elapsed > 0 else 0
            self.logger.info(
                f"{self.name}: {self.current}/{self.total} ({pct:.1f}%) | "
                f"Rate: {rate:.1f}/s | Elapsed: {elapsed:.1f}s"
            )

    def finish(self) -> None:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.logger.info(f"{self.name} completed in {elapsed:.2f}s")