"""
Loguru logging configuration for FamiliePlanner.

- Console: coloured, human-readable
- File: logs/familieplanner-YYYY-MM-DD.log, rotated daily, retained 7 days
- Stdlib logging (uvicorn, sqlalchemy) is routed through loguru via InterceptHandler
"""

import logging
import sys
from pathlib import Path

from loguru import logger

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{message}"
)

FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}"


class InterceptHandler(logging.Handler):
    """Route stdlib logging records into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(level: str = "INFO") -> None:
    """Initialise loguru sinks and intercept stdlib logging."""
    logger.remove()  # remove default stderr sink

    # Console sink – coloured
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # File sink – one file per day, kept for 7 days
    logger.add(
        LOGS_DIR / "familieplanner-{time:YYYY-MM-DD}.log",
        format=FILE_FORMAT,
        level=level,
        rotation="00:00",  # new file every midnight
        retention="7 days",  # delete files older than 7 days
        compression="gz",  # compress rotated files
        backtrace=True,
        diagnose=False,  # avoid leaking sensitive data in file
        encoding="utf-8",
    )

    # Intercept uvicorn + sqlalchemy stdlib loggers
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        std_logger = logging.getLogger(name)
        std_logger.handlers = [InterceptHandler()]
        std_logger.propagate = False

    logger.info("Logging initialised – level={}, log_dir={}", level, LOGS_DIR)
