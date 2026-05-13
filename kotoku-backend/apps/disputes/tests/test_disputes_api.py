import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APIClient

from apps.accounts.models import Account
from apps.agreements.models import Agreement
from apps.parties.models import Party
from apps.disputes.models import Dispute


@pytest.fixture
def authenticated_client():
    user = get_user_model().objects.create_user(phone="+233123456789")
    user.set_password("test")
    user.save()
    account = Account.objects.create(user=user, phone=user.phone)
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, account


@pytest.fixture
def setup_agreement_with_party(authenticated_client):
    client, account = authenticated_client
    agreement = Agreement.objects.create(
        title="Test Agreement",
        scenario_template="used_vehicle_sale",
        status=Agreement.Status.SEALED,
        created_by=account,
        sealed_at=timezone.now(),
    )
    party = Party.objects.create(
            agreement=agreement,
            display_name="Test Party",
            role=Party.Role.SELLER,
            phone="+233123456789",
        )
    return client, account, agreement, party


@pytest.mark.django_db
class TestDisputeCreateAPI:
    def test_create_dispute_on_sealed_agreement_returns_201(self, setup_agreement_with_party):
        client, account, agreement, party = setup_agreement_with_party
        response = client.post(
            f"/api/agreements/{agreement.pk}/disputes/",
            {"raised_by_party_id": party.pk, "reason": "Test dispute reason here"},
            format="json",
        )
        assert response.status_code == 201
        assert Dispute.objects.count() == 1

    def test_cannot_create_dispute_on_draft_agreement(self, authenticated_client):
        client, account = authenticated_client
        agreement = Agreement.objects.create(
            title="Draft Agreement",
            status=Agreement.Status.DRAFT,
            created_by=account,
        )
        party = Party.objects.create(
            agreement=agreement,
            display_name="Test Party",
            role=Party.Role.SELLER,
            phone="+233123456789",
        )
        response = client.post(
            f"/api/agreements/{agreement.pk}/disputes/",
            {"raised_by_party_id": party.pk, "reason": "Test dispute reason here"},
            format="json",
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestDisputeDetailAPI:
    def test_get_dispute_detail_returns_200(self, setup_agreement_with_party):
        client, account, agreement, party = setup_agreement_with_party
        dispute = Dispute.objects.create(
            agreement=agreement,
            raised_by=party,
            reason="Test reason",
        )
        response = client.get(f"/api/agreements/{agreement.pk}/disputes/{dispute.pk}/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestDisputeCasePackAPI:
    def test_generate_case_pack_returns_200(self, setup_agreement_with_party):
        client, account, agreement, party = setup_agreement_with_party
        dispute = Dispute.objects.create(
            agreement=agreement,
            raised_by=party,
            reason="Test reason",
        )
        response = client.post(f"/api/agreements/{agreement.pk}/disputes/{dispute.pk}/case_pack/")
        assert response.status_code == 200
        assert "case_pack" in response.data["data"]