from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
@patch("apps.health.api.views._check_db", return_value=True)
@patch("apps.health.api.views._redis_check_result", return_value="ok")
def test_health_endpoint_returns_healthy(mock_redis, mock_db):
    response = APIClient().get("/api/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["checks"]["database"]["status"] == "ok"
    assert response.json()["checks"]["redis"]["status"] == "ok"


@pytest.mark.django_db
@patch("apps.health.api.views._check_db", return_value=False)
@patch("apps.health.api.views._redis_check_result", return_value="ok")
def test_health_endpoint_returns_503_when_db_down(mock_redis, mock_db):
    response = APIClient().get("/api/health/")
    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["checks"]["database"]["status"] == "error"


@pytest.mark.django_db
@patch("apps.health.api.views._check_db", return_value=True)
@patch("apps.health.api.views._redis_check_result", return_value="error")
def test_health_endpoint_stays_healthy_when_only_redis_is_down(mock_redis, mock_db):
    response = APIClient().get("/api/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["checks"]["redis"]["status"] == "error"


@pytest.mark.django_db
@patch("apps.health.api.views._check_db", return_value=True)
@patch("apps.health.api.views._redis_check_result", return_value="error")
def test_readiness_endpoint_returns_503_when_redis_is_down(mock_redis, mock_db):
    response = APIClient().get("/api/health/readiness/")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["database"]["status"] == "ok"
    assert response.json()["checks"]["redis"]["status"] == "error"


@pytest.mark.django_db
@patch("apps.health.api.views._check_db", return_value=True)
@patch("apps.health.api.views._redis_check_result", return_value="ok")
@patch("apps.health.api.views._storage_check_result", return_value={"status": "ok"})
def test_readiness_endpoint_surfaces_missing_runtime_config_when_strict(
    mock_storage, mock_redis, mock_db, settings
):
    settings.STRICT_RUNTIME_VALIDATION = True
    settings.AWS_SECRET_ACCESS_KEY = ""

    response = APIClient().get("/api/health/readiness/")

    assert response.status_code == 503
    assert response.json()["checks"]["config"]["status"] == "error"
    assert "AWS_SECRET_ACCESS_KEY" in response.json()["checks"]["config"]["missing"]


@pytest.mark.django_db
@patch("apps.health.api.views._check_db", return_value=True)
@patch("apps.health.api.views._redis_check_result", return_value="ok")
@patch("apps.health.api.views._storage_check_result", return_value={"status": "error"})
def test_readiness_endpoint_returns_503_when_storage_probe_fails(
    mock_storage, mock_redis, mock_db, settings
):
    settings.STRICT_RUNTIME_VALIDATION = True

    response = APIClient().get("/api/health/readiness/")

    assert response.status_code == 503
    assert response.json()["checks"]["storage"]["status"] == "error"
