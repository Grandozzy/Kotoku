import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement

_DELETE_PATH = "/api/agreements/{id}/"


def _make_client(phone: str):
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(
        user=user,
        email=f"{phone.replace('+', '')}@delete.test",
        phone=phone,
    )
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, account


@pytest.mark.django_db
def test_owner_can_delete_draft_agreement():
    client, account = _make_client("+233501100001")
    agreement = Agreement.objects.create(
        title="Delete draft",
        created_by=account,
        status=AgreementStatus.DRAFT,
    )

    response = client.delete(_DELETE_PATH.format(id=agreement.pk))

    assert response.status_code == 200
    assert not Agreement.objects.filter(pk=agreement.pk).exists()


@pytest.mark.django_db
def test_owner_can_delete_pending_consent_agreement():
    client, account = _make_client("+233501100002")
    agreement = Agreement.objects.create(
        title="Delete pending",
        created_by=account,
        status=AgreementStatus.PENDING_CONSENT,
    )

    response = client.delete(_DELETE_PATH.format(id=agreement.pk))

    assert response.status_code == 200
    assert not Agreement.objects.filter(pk=agreement.pk).exists()


@pytest.mark.django_db
def test_owner_cannot_delete_active_agreement():
    client, account = _make_client("+233501100003")
    agreement = Agreement.objects.create(
        title="Keep active",
        created_by=account,
        status=AgreementStatus.ACTIVE,
    )

    response = client.delete(_DELETE_PATH.format(id=agreement.pk))

    assert response.status_code == 400
    assert Agreement.objects.filter(pk=agreement.pk).exists()


@pytest.mark.django_db
def test_non_owner_cannot_delete_pending_consent_agreement():
    client, _account = _make_client("+233501100004")
    _other_client, other_account = _make_client("+233501100005")
    agreement = Agreement.objects.create(
        title="Other pending",
        created_by=other_account,
        status=AgreementStatus.PENDING_CONSENT,
    )

    response = client.delete(_DELETE_PATH.format(id=agreement.pk))

    assert response.status_code == 404
    assert Agreement.objects.filter(pk=agreement.pk).exists()
