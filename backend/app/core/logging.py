import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "logs"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 30

SENSITIVE_PATTERNS = [
    re.compile(r"(password|passwd|pwd)\s*[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"(token|api[_-]?key|secret|authorization|bearer)\s*[=:]\s*\S+", re.IGNORECASE),
]


class SensitiveDataFilter(logging.Filter):
    """Redacts sensitive information from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        return True

    @staticmethod
    def _redact(text: str) -> str:
        for pattern in SENSITIVE_PATTERNS:
            text = pattern.sub(r"\1=[REDACTED]", text)
        return text


def setup_logging() -> None:
    """Initialize the application logging system."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    sensitive_filter = SensitiveDataFilter()

    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(sensitive_filter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(sensitive_filter)
    console_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    app_logger.info("日志系统初始化完成 | dir=%s", str(LOG_DIR))


def get_logger(name: str) -> logging.Logger:
    """Get a logger under the app namespace."""
    return logging.getLogger(f"app.{name}")
