import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail

from apps.accounts.models import Account, AdminMfaCode


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/admin/login/"])
def test_admin_login_requires_email_code(client, settings, path):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    user = get_user_model().objects.create_superuser(
        phone="+233550000001",
        password="AdminSecret123!",
    )
    Account.objects.create(user=user, email="admin1@test.com", phone=user.phone)

    response = client.post(
        path,
        {
            "username": user.phone,
            "password": "AdminSecret123!",
        },
    )
    assert response.status_code == 302
    assert response.url.endswith("/admin/verify/")
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["admin1@test.com"]

    code = re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)
    verify = client.post("/admin/verify/", {"code": code})
    assert verify.status_code == 302
    assert verify.url.endswith("/admin/")
    assert str(user.pk) == client.session.get("_auth_user_id")
    assert AdminMfaCode.objects.filter(user=user, used_at__isnull=False).exists()


@pytest.mark.django_db
def test_admin_login_enrolls_email_before_sending_code(client, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    user = get_user_model().objects.create_superuser(
        phone="+233550000002",
        password="AdminSecret123!",
    )

    response = client.post(
        "/admin/login/",
        {
            "username": user.phone,
            "password": "AdminSecret123!",
        },
    )
    assert response.status_code == 302
    assert response.url.endswith("/admin/enroll-email/")

    enroll = client.post("/admin/enroll-email/", {"email": "admin2@test.com"})
    assert enroll.status_code == 302
    assert enroll.url.endswith("/admin/verify/")
    assert Account.objects.get(user=user).email == "admin2@test.com"
    assert len(mail.outbox) == 1
