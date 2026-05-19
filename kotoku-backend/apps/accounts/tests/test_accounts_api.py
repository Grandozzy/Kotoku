import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Account, User


def _make_client(phone, email):
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(user=user, email=email, phone=phone)
    token = AccessToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client, user, account


@pytest.mark.django_db
class TestMeView:
    def test_get_returns_200_with_account_data(self):
        client, _, account = _make_client("+233520001001", "me@test.com")
        response = client.get("/api/me/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["email"] == "me@test.com"
        assert data["phone"] == "+233520001001"

    def test_get_unauthenticated_returns_401(self):
        response = APIClient().get("/api/me/")
        assert response.status_code == 401

    def test_patch_updates_full_name(self):
        client, _, _ = _make_client("+233520001002", "patch@test.com")
        response = client.patch("/api/me/", {"full_name": "Test Name"}, format="json")
        assert response.status_code == 200
        assert response.json()["data"]["full_name"] == "Test Name"

    def test_patch_updates_email(self):
        client, _, _ = _make_client("+233520001003", "old@test.com")
        response = client.patch("/api/me/", {"email": "updated@test.com"}, format="json")
        assert response.status_code == 200
        assert response.json()["data"]["email"] == "updated@test.com"

    def test_patch_duplicate_email_returns_400(self):
        client1, _, _ = _make_client("+233520001004", "taken@test.com")
        client2, _, _ = _make_client("+233520001005", "other@test.com")
        client1.patch("/api/me/", {"email": "shared@test.com"}, format="json")
        response = client2.patch("/api/me/", {"email": "shared@test.com"}, format="json")
        assert response.status_code == 400

    def test_patch_unauthenticated_returns_401(self):
        response = APIClient().patch("/api/me/", {"full_name": "X"}, format="json")
        assert response.status_code == 401


@pytest.mark.django_db
class TestAccountListView:
    def test_non_admin_returns_403(self):
        client, _, _ = _make_client("+233520002001", "user@test.com")
        response = client.get("/api/accounts/")
        assert response.status_code == 403

    def test_unauthenticated_returns_401(self):
        response = APIClient().get("/api/accounts/")
        assert response.status_code == 401

    def test_admin_returns_200(self):
        user = User.objects.create_user(phone="+233520002002", is_staff=True)
        Account.objects.create(user=user, email="admin@test.com", phone="+233520002002")
        token = AccessToken.for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = client.get("/api/accounts/")
        assert response.status_code == 200
