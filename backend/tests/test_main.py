from fastapi.testclient import TestClient

from app.core.errors import NotFoundError
from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "guardian-nexus-backend",
    }


def test_guardian_exception_handler():
    @app.get("/__test_guardian_error")
    async def test_guardian_error():
        raise NotFoundError(
            "Threat session not found",
            details={"session_id": "test-session"},
        )

    with TestClient(app) as client:
        response = client.get("/__test_guardian_error")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Threat session not found",
            "details": {"session_id": "test-session"},
        }
    }


def test_unknown_route_returns_404():
    with TestClient(app) as client:
        response = client.get("/does-not-exist")

    assert response.status_code == 404
