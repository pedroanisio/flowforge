"""
Structured logging configuration
"""
import logging
import sys
from pythonjsonlogger import jsonlogger
from .config import settings


def setup_logging():
    """Configure application logging with JSON or text format"""

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Remove existing handlers
    logger.handlers = []

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)

    # Choose format based on settings
    if settings.log_format.lower() == "json":
        # JSON formatter for structured logging
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        # Text formatter for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Log initial configuration
    logger.info(
        f"Logging configured: level={settings.log_level}, format={settings.log_format}"
    )

    return logger


# Create logger instance
logger = setup_logging()
