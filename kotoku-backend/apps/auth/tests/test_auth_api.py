from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestSendOtpApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def test_send_otp_returns_200(self):
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

    def test_send_otp_rate_limited_returns_400(self):
        self.client.post("/api/auth/send-otp/", {"phone": "+233501234567"}, format="json")
        response = self.client.post(
            "/api/auth/send-otp/",
            {"phone": "+233501234567"},
            format="json",
        )
        assert response.status_code == 400


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestVerifyOtpApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def test_verify_otp_returns_200_with_token(self):
        self.client.post("/api/auth/send-otp/", {"phone": "+233501234567"}, format="json")
        otp = cache.get("auth_otp:+233501234567")
        response = self.client.post(
            "/api/auth/verify-otp/",
            {"phone": "+233501234567", "otp_code": otp},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data["data"]

    def test_verify_otp_wrong_code_returns_400(self):
        self.client.post("/api/auth/send-otp/", {"phone": "+233501234567"}, format="json")
        response = self.client.post(
            "/api/auth/verify-otp/",
            {"phone": "+233501234567", "otp_code": "00000000"},
            format="json",
        )
        assert response.status_code == 400
