from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
@patch("apps.health.api.views._check_db", return_value=True)
@patch("apps.health.api.views._check_redis", return_value=True)
def test_health_endpoint_returns_healthy(mock_redis, mock_db):
    response = APIClient().get("/api/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["checks"]["database"]["status"] == "ok"
    assert response.json()["checks"]["redis"]["status"] == "ok"


@pytest.mark.django_db
@patch("apps.health.api.views._check_db", return_value=False)
@patch("apps.health.api.views._check_redis", return_value=True)
def test_health_endpoint_returns_503_when_db_down(mock_redis, mock_db):
    response = APIClient().get("/api/health/")
    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["checks"]["database"]["status"] == "error"
