from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import DeviceSession

_PATCH_ARKESEL_SEND = patch("apps.auth.services.send_arkesel_otp.delay", return_value=None)
_PATCH_ARKESEL_VERIFY = patch(
    "infrastructure.sms.arkesel_client.ArkeselOtpClient.verify_otp",
    return_value=True,
)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestSendOtpApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def test_send_otp_returns_200(self):
        with _PATCH_ARKESEL_SEND:
            response = self.client.post(
                "/api/auth/send-otp/",
                {"phone": "+233501234567"},
                format="json",
            )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_send_otp_missing_phone_returns_400(self):
        response = self.client.post("/api/auth/send-otp/", {}, format="json")
        assert response.status_code == 400

    def test_send_otp_invalid_phone_format_returns_400(self):
        response = self.client.post(
            "/api/auth/send-otp/", {"phone": "0501234567"}, format="json"
        )
        assert response.status_code == 400


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestVerifyOtpApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def test_verify_otp_returns_200_with_token(self):
        with _PATCH_ARKESEL_VERIFY:
            response = self.client.post(
                "/api/auth/verify-otp/",
                {"phone": "+233501234567", "otp_code": "123456"},
                format="json",
            )
        assert response.status_code == 200
        data = response.json()
        assert "access" in data["data"]
        assert "account_id" in data["data"]["user"]
        assert isinstance(data["data"]["user"]["account_id"], int)
        assert "refresh" not in data["data"]
        assert "kotoku_refresh" in response.cookies
        assert response.cookies["kotoku_refresh"]["httponly"]

    def test_mobile_verify_otp_keeps_refresh_token_in_body(self):
        with _PATCH_ARKESEL_VERIFY:
            response = self.client.post(
                "/api/auth/verify-otp/",
                {"phone": "+233501234567", "otp_code": "123456"},
                format="json",
                HTTP_X_CLIENT_TYPE="mobile",
            )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["refresh"]
        assert "kotoku_refresh" not in response.cookies

    def test_web_refresh_uses_cookie_and_rotates_cookie(self):
        with _PATCH_ARKESEL_VERIFY:
            verify_response = self.client.post(
                "/api/auth/verify-otp/",
                {"phone": "+233501234567", "otp_code": "123456"},
                format="json",
            )
        old_cookie = verify_response.cookies["kotoku_refresh"].value
        old_session_id = old_cookie.split(".", 1)[0]

        refresh_response = self.client.post(
            "/api/auth/token/refresh/",
            {},
            format="json",
            HTTP_X_CLIENT_TYPE="web",
        )

        assert refresh_response.status_code == 200
        data = refresh_response.json()["data"]
        assert "access" in data
        assert "refresh" not in data
        assert "kotoku_refresh" in refresh_response.cookies
        assert refresh_response.cookies["kotoku_refresh"].value != old_cookie
        assert DeviceSession.objects.get(id=old_session_id).is_revoked is True

    def test_mobile_refresh_requires_body_token(self):
        response = self.client.post(
            "/api/auth/token/refresh/",
            {},
            format="json",
            HTTP_X_CLIENT_TYPE="mobile",
        )
        assert response.status_code == 401

    def test_web_signout_revokes_cookie_session_and_clears_cookie(self):
        with _PATCH_ARKESEL_VERIFY:
            verify_response = self.client.post(
                "/api/auth/verify-otp/",
                {"phone": "+233501234567", "otp_code": "123456"},
                format="json",
            )
        session_id = verify_response.cookies["kotoku_refresh"].value.split(".", 1)[0]

        response = self.client.post(
            "/api/auth/signout/",
            {},
            format="json",
            HTTP_X_CLIENT_TYPE="web",
        )

        assert response.status_code == 200
        assert DeviceSession.objects.get(id=session_id).is_revoked is True
        assert response.cookies["kotoku_refresh"]["max-age"] == 0

    def test_verify_otp_wrong_code_returns_400(self):
        with patch(
            "infrastructure.sms.arkesel_client.ArkeselOtpClient.verify_otp",
            return_value=False,
        ):
            response = self.client.post(
                "/api/auth/verify-otp/",
                {"phone": "+233501234567", "otp_code": "000000"},
                format="json",
            )
        assert response.status_code == 400

    def test_first_party_cors_preflight_allows_credentials(self):
        response = self.client.options(
            "/api/auth/token/refresh/",
            HTTP_ORIGIN="https://kotoku-app.com",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )

        assert response.status_code == 204
        assert response["Access-Control-Allow-Origin"] == "https://kotoku-app.com"
        assert response["Access-Control-Allow-Credentials"] == "true"
