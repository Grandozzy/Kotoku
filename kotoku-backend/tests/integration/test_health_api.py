from rest_framework.test import APIClient


def test_health_endpoint_returns_ok() -> None:
    response = APIClient().get("/api/health/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["data"]["status"] == "healthy"
