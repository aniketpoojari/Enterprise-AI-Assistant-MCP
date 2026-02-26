"""Simple logging setup for the Enterprise AI Assistant."""

import logging
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_file: str = None, format: str = "%(asctime)s - %(levelname)s - %(message)s"):
    """Simple logging setup."""
    try:

        # Create logs directory if needed
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)

        # Basic configuration
        logging.basicConfig(
            level=log_level,
            format=format,
            handlers=[
                logging.StreamHandler(),  # Console
                logging.FileHandler(log_file) if log_file else logging.NullHandler()
            ]
        )

    except Exception as e:
        print(f"Error setting up logging -> {e}")
        # Fallback to basic logging
        logging.basicConfig(level=logging.INFO)


def get_logger(name):
    """Get a logger."""
    try:
        return logging.getLogger(name)

    except Exception as e:
        print(f"Error getting logger {name} -> {e}")
        return logging.getLogger()
