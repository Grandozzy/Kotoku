from django.http import HttpResponse
from django.test import RequestFactory

from common.middleware import ProbeShieldMiddleware


def _ok_response(_request):
    return HttpResponse("ok")


def test_probe_shield_blocks_common_env_probe():
    request = RequestFactory().get("/.env")
    response = ProbeShieldMiddleware(_ok_response)(request)
    assert response.status_code == 404


def test_probe_shield_blocks_php_probe():
    request = RequestFactory().get("/phpinfo.php")
    response = ProbeShieldMiddleware(_ok_response)(request)
    assert response.status_code == 404


def test_probe_shield_allows_normal_api_request():
    request = RequestFactory().get("/api/health/")
    response = ProbeShieldMiddleware(_ok_response)(request)
    assert response.status_code == 200
