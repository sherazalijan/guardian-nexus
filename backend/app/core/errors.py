from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class GuardianError(Exception):
    """Base exception for expected Guardian Nexus application errors."""

    status_code = 500
    error_code = "guardian_error"

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(GuardianError):
    """Raised when application configuration is invalid."""

    status_code = 500
    error_code = "configuration_error"


class ValidationFailedError(GuardianError):
    """Raised when application-level validation fails."""

    status_code = 422
    error_code = "validation_failed"


class NotFoundError(GuardianError):
    """Raised when a requested Guardian Nexus resource does not exist."""

    status_code = 404
    error_code = "not_found"


async def guardian_exception_handler(
    request: Request,
    exc: GuardianError,
) -> JSONResponse:
    """Convert expected Guardian Nexus errors into consistent JSON responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )
