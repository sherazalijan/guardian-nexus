from app.core.errors import (
    ConfigurationError,
    GuardianError,
    NotFoundError,
    ValidationFailedError,
)


def test_guardian_error_defaults():
    error = GuardianError("Something went wrong")

    assert error.message == "Something went wrong"
    assert error.details == {}
    assert error.status_code == 500
    assert error.error_code == "guardian_error"


def test_configuration_error():
    error = ConfigurationError("Invalid configuration")

    assert isinstance(error, GuardianError)
    assert error.status_code == 500
    assert error.error_code == "configuration_error"


def test_validation_error():
    error = ValidationFailedError(
        "Invalid score",
        details={"field": "score"},
    )

    assert isinstance(error, GuardianError)
    assert error.status_code == 422
    assert error.error_code == "validation_failed"
    assert error.details == {"field": "score"}


def test_not_found_error():
    error = NotFoundError("Session not found")

    assert isinstance(error, GuardianError)
    assert error.status_code == 404
    assert error.error_code == "not_found"
