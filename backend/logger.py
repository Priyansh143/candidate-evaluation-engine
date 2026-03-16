import logging
from pathlib import Path
from datetime import datetime


def setup_run_logger(run_id: str | None = None) -> logging.Logger:
    """
    Creates a per-run logger that writes to logs/<timestamp>.log
    """

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    timestamp = run_id or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = logs_dir / f"{timestamp}.log"

    logger = logging.getLogger(f"interview_run_{timestamp}")
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers if reused
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger