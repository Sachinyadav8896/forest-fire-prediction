"""
logger.py
Shared logging utility. Every module in the project should obtain its
logger via get_logger(__name__) rather than configuring logging itself,
so log format and log file destination stay consistent project-wide.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import PATHS

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured (avoid duplicate handlers on repeated imports)
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    os.makedirs(PATHS.logs_dir, exist_ok=True)
    log_file = os.path.join(PATHS.logs_dir, "app.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger
