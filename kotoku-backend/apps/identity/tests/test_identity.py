import pytest

from apps.accounts.models import Account, User
from apps.identity.models import IdentityRecord
from apps.identity.selectors import IdentitySelector
from apps.identity.services import IdentityService


def _account(phone: str, email: str) -> Account:
    user = User.objects.create_user(phone=phone)
    return Account.objects.create(user=user, phone=phone, email=email)


@pytest.mark.django_db
class TestIdentityService:
    def test_create_identity_record(self):
        account = _account("+233700000001", "id1@test.com")
        identity = IdentityService.create_identity_record(
            account=account,
            reference="GHA-1234",
            verification_type=IdentityRecord.VerificationType.GHANA_CARD,
        )
        assert identity.account == account
        assert identity.reference == "GHA-1234"
        assert identity.verified_at is None

    def test_mark_verified_sets_timestamp(self):
        account = _account("+233700000002", "id2@test.com")
        identity = IdentityService.create_identity_record(
            account=account,
            reference="PHONE-1234",
            verification_type=IdentityRecord.VerificationType.PHONE,
        )
        verified = IdentityService.mark_verified(identity_record=identity)
        assert verified.verified_at is not None


@pytest.mark.django_db
class TestIdentitySelector:
    def test_list_for_account_returns_only_matching_records(self):
        account = _account("+233700000003", "id3@test.com")
        other = _account("+233700000004", "id4@test.com")
        IdentityService.create_identity_record(
            account=account,
            reference="GHA-1",
            verification_type=IdentityRecord.VerificationType.GHANA_CARD,
        )
        IdentityService.create_identity_record(
            account=other,
            reference="GHA-2",
            verification_type=IdentityRecord.VerificationType.GHANA_CARD,
        )
        result = list(IdentitySelector.list_for_account(account.pk))
        assert len(result) == 1
        assert result[0].account_id == account.pk

    def test_get_for_account_scopes_to_owner(self):
        account = _account("+233700000005", "id5@test.com")
        identity = IdentityService.create_identity_record(
            account=account,
            reference="GHA-5",
            verification_type=IdentityRecord.VerificationType.GHANA_CARD,
        )
        result = IdentitySelector.get_for_account(
            identity_id=identity.pk,
            account_id=account.pk,
        )
        assert result.pk == identity.pk

    def test_get_verified_for_reference_returns_verified_record(self):
        account = _account("+233700000006", "id6@test.com")
        identity = IdentityService.create_identity_record(
            account=account,
            reference="GHA-6",
            verification_type=IdentityRecord.VerificationType.GHANA_CARD,
        )
        IdentityService.mark_verified(identity_record=identity)
        result = IdentitySelector.get_verified_for_reference("GHA-6")
        assert result.pk == identity.pk
