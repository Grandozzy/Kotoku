import pytest

from apps.accounts.models import Account, User
from apps.accounts.services import AccountService
from common.exceptions import DomainError


def _make_account(phone, email):
    user = User.objects.create_user(phone=phone)
    return Account.objects.create(user=user, email=email, phone=phone)


@pytest.mark.django_db
class TestAccountServiceUpdateProfile:
    def test_update_full_name(self):
        account = _make_account("+233510001001", "a@test.com")
        result = AccountService.update_profile(account=account, full_name="John Doe")
        assert result.full_name == "John Doe"

    def test_update_email(self):
        account = _make_account("+233510001002", "b@test.com")
        result = AccountService.update_profile(account=account, email="new@test.com")
        assert result.email == "new@test.com"

    def test_email_normalised_to_lowercase(self):
        account = _make_account("+233510001003", "c@test.com")
        result = AccountService.update_profile(account=account, email="NEW@Test.COM")
        assert result.email == "new@test.com"

    def test_full_name_too_long_raises(self):
        account = _make_account("+233510001004", "d@test.com")
        with pytest.raises(DomainError, match="255 characters"):
            AccountService.update_profile(account=account, full_name="x" * 256)

    def test_duplicate_email_raises(self):
        account1 = _make_account("+233510001005", "e1@test.com")
        account2 = _make_account("+233510001006", "e2@test.com")
        AccountService.update_profile(account=account1, email="shared@test.com")
        with pytest.raises(DomainError, match="already in use"):
            AccountService.update_profile(account=account2, email="shared@test.com")

    def test_same_account_can_keep_its_own_email(self):
        account = _make_account("+233510001007", "same@test.com")
        result = AccountService.update_profile(account=account, email="same@test.com")
        assert result.email == "same@test.com"

    def test_no_changes_returns_account_unchanged(self):
        account = _make_account("+233510001008", "f@test.com")
        result = AccountService.update_profile(account=account)
        assert result.pk == account.pk

    def test_update_both_fields(self):
        account = _make_account("+233510001009", "g@test.com")
        result = AccountService.update_profile(
            account=account, full_name="Jane", email="jane@test.com"
        )
        assert result.full_name == "Jane"
        assert result.email == "jane@test.com"


@pytest.mark.django_db
class TestAccountServiceCreateAccount:
    def test_creates_user_and_account(self):
        account = AccountService.create_account(
            email="create@test.com", phone="+233510002001"
        )
        assert account.email == "create@test.com"
        assert account.phone == "+233510002001"
        assert account.user is not None
        assert User.objects.filter(pk=account.user.pk).exists()

    def test_creates_account_with_full_name(self):
        account = AccountService.create_account(
            email="named@test.com", full_name="Jane Doe", phone="+233510002002"
        )
        assert account.full_name == "Jane Doe"

    def test_creates_account_with_actor(self):
        account = AccountService.create_account(
            email="actor@test.com", phone="+233510002003", actor="admin"
        )
        assert account.pk is not None
