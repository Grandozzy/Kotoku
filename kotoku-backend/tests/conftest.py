import os

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

from apps.accounts.models import Account, User  # noqa: E402


@pytest.fixture()
def make_account():
    def _make_account(email="test@example.com", phone="+233000000000", full_name="Test User"):
        user = User.objects.create_user(phone=phone or email)
        return Account.objects.create(
            user=user,
            email=email,
            phone=phone,
            full_name=full_name,
        )

    return _make_account
