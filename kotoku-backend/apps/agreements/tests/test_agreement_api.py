import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Account, User


@pytest.fixture()
def authenticated_client():
    user = User.objects.create_user(phone="+233500000001")
    account = Account.objects.create(
        user=user, email="test@kotoku.app", phone=user.phone
    )
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client, account


@pytest.fixture()
def second_authenticated_client():
    user = User.objects.create_user(phone="+233500000002")
    account = Account.objects.create(
        user=user, email="other@kotoku.app", phone=user.phone
    )
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client, account


@pytest.mark.django_db
class TestAgreementCreateApi:
    def test_create_agreement_returns_201(self, authenticated_client):
        client, _ = authenticated_client
        response = client.post(
            "/api/agreements/",
            {"title": "Car Sale", "scenario_template": "used_vehicle_sale"},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()["data"]["agreement"]
        assert data["title"] == "Car Sale"
        assert data["status"] == "draft"
        assert data["scenario_template"] == "used_vehicle_sale"

    def test_create_agreement_missing_title_returns_400(self, authenticated_client):
        client, _ = authenticated_client
        response = client.post("/api/agreements/", {}, format="json")
        assert response.status_code == 400

    def test_create_agreement_unauthenticated_returns_401(self):
        response = APIClient().post(
            "/api/agreements/", {"title": "Test"}, format="json"
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestAgreementListApi:
    def test_list_agreements_returns_200(self, authenticated_client):
        client, account = authenticated_client
        from apps.agreements.services import AgreementService

        AgreementService.create_draft(title="A1", created_by=account)
        AgreementService.create_draft(title="A2", created_by=account)
        response = client.get("/api/agreements/", format="json")
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert len(results) == 2


@pytest.mark.django_db
class TestAgreementDetailApi:
    def test_get_agreement_returns_200(self, authenticated_client):
        client, account = authenticated_client
        from apps.agreements.services import AgreementService

        agreement = AgreementService.create_draft(
            title="Detail Test", created_by=account
        )
        response = client.get(f"/api/agreements/{agreement.pk}/", format="json")
        assert response.status_code == 200
        data = response.json()["data"]["agreement"]
        assert data["title"] == "Detail Test"

    def test_get_nonexistent_agreement_returns_404(self, authenticated_client):
        client, _ = authenticated_client
        response = client.get("/api/agreements/99999/", format="json")
        assert response.status_code == 404

    def test_get_other_users_agreement_returns_404(
        self, authenticated_client, second_authenticated_client
    ):
        owner_client, account = authenticated_client
        other_client, _ = second_authenticated_client
        from apps.agreements.services import AgreementService

        agreement = AgreementService.create_draft(title="Private", created_by=account)
        response = other_client.get(
            f"/api/agreements/{agreement.pk}/", format="json"
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestAgreementUpdateApi:
    def test_update_draft_returns_200(self, authenticated_client):
        client, account = authenticated_client
        from apps.agreements.services import AgreementService

        agreement = AgreementService.create_draft(
            title="Original", created_by=account
        )
        response = client.patch(
            f"/api/agreements/{agreement.pk}/",
            {"title": "Updated"},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()["data"]["agreement"]
        assert data["title"] == "Updated"

    def test_update_non_draft_returns_400(self, authenticated_client):
        client, account = authenticated_client
        from apps.agreements.domain.enums import AgreementStatus
        from apps.agreements.services import AgreementService

        agreement = AgreementService.create_draft(title="Test", created_by=account)
        agreement.status = AgreementStatus.SEALED
        agreement.save()
        response = client.patch(
            f"/api/agreements/{agreement.pk}/",
            {"title": "Nope"},
            format="json",
        )
        assert response.status_code == 400

    def test_update_other_users_agreement_returns_404(
        self, authenticated_client, second_authenticated_client
    ):
        owner_client, account = authenticated_client
        other_client, _ = second_authenticated_client
        from apps.agreements.services import AgreementService

        agreement = AgreementService.create_draft(title="Private", created_by=account)
        response = other_client.patch(
            f"/api/agreements/{agreement.pk}/",
            {"title": "Hacked"},
            format="json",
        )
        assert response.status_code == 404
