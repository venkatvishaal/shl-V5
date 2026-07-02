"""Centralised logging configuration for the SHL Recommender service."""

import logging
import sys


def setup_logger(log_level: str = "INFO") -> logging.Logger:
    """
    Configure the root logger with a consistent format.

    Args:
        log_level: Standard Python log level string (DEBUG, INFO, WARNING, ERROR).

    Returns:
        The configured root logger.
    """
    root = logging.getLogger()

    # Avoid adding duplicate handlers if called more than once
    if root.handlers:
        return root

    root.setLevel(log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level.upper())

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    return root