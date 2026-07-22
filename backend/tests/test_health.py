from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_health_returns_service_name():
    response = TestClient(create_app()).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "crawler-api"}
