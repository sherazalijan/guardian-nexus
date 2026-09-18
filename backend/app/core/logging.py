import logging
import re
from collections.abc import Mapping
from typing import Any


SENSITIVE_KEY_PATTERN = re.compile(
    r"(api[_-]?key|authorization|access[_-]?token|refresh[_-]?token|"
    r"password|secret|credential|token)",
    re.IGNORECASE,
)

REDACTED_VALUE = "[REDACTED]"


def sanitize_for_logging(value: Any) -> Any:
    """Return a copy of a value with sensitive fields redacted."""
    if isinstance(value, Mapping):
        return {
            key: (
                REDACTED_VALUE
                if SENSITIVE_KEY_PATTERN.search(str(key))
                else sanitize_for_logging(item)
            )
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [sanitize_for_logging(item) for item in value]

    if isinstance(value, tuple):
        return tuple(sanitize_for_logging(item) for item in value)

    if isinstance(value, set):
        return {sanitize_for_logging(item) for item in value}

    return value


def configure_logging(debug: bool = False) -> None:
    """Configure application-wide logging."""
    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the requested module."""
    return logging.getLogger(name)
