import logging

from app.core.logging import (
    REDACTED_VALUE,
    configure_logging,
    get_logger,
    sanitize_for_logging,
)


def test_sensitive_values_are_redacted():
    data = {
        "username": "test-user",
        "api_key": "secret-key",
        "authorization": "Bearer secret",
        "nested": {
            "password": "secret-password",
            "token": "secret-token",
            "safe": "visible",
        },
    }

    sanitized = sanitize_for_logging(data)

    assert sanitized["username"] == "test-user"
    assert sanitized["api_key"] == REDACTED_VALUE
    assert sanitized["authorization"] == REDACTED_VALUE
    assert sanitized["nested"]["password"] == REDACTED_VALUE
    assert sanitized["nested"]["token"] == REDACTED_VALUE
    assert sanitized["nested"]["safe"] == "visible"


def test_nested_lists_are_sanitized():
    data = [
        {"secret": "hidden"},
        {"message": "safe"},
    ]

    sanitized = sanitize_for_logging(data)

    assert sanitized[0]["secret"] == REDACTED_VALUE
    assert sanitized[1]["message"] == "safe"


def test_configure_logging():
    configure_logging(debug=True)

    logger = get_logger("guardian-nexus.test")

    assert logger.isEnabledFor(logging.DEBUG)
