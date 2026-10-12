"""
Logger setup for IMDb Movie Rating Scraper & Tracker.
Provides file and stream logging for debugging and audit trails.
"""

import logging
import os
from config import LOG_PATH

def get_logger(name: str = "IMDbScraper") -> logging.Logger:
    """Configures and returns a logger instance."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if logger is called multiple times
    if not logger.handlers:
        # File Handler
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console Handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger
