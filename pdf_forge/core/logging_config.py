"""Configure application logging — local file + console."""
import logging
import logging.handlers
import os
from pathlib import Path


def _log_dir() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home())) / "PDFD" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def setup_logging(level: int = logging.DEBUG) -> None:
    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler — keeps last 5 × 2 MB
    log_file = _log_dir() / "pdfd.log"
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)

    # Console handler — INFO+ only
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(logging.INFO)

    root.addHandler(fh)
    root.addHandler(ch)

    logging.getLogger("pikepdf").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
