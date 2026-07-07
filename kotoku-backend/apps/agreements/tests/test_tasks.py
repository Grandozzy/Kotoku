from datetime import timedelta

from django.utils import timezone

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.agreements.tasks import cleanup_stale_drafts


def test_cleanup_deletes_old_drafts(db):
    from apps.accounts.models import Account, User
    user = User.objects.create_user(phone="+1234567890")
    account = Account.objects.create(user=user, email="test@example.com")
    old_draft = Agreement.objects.create(
        title="Old Draft",
        status=AgreementStatus.DRAFT,
        created_by=account
    )
    Agreement.objects.filter(id=old_draft.id).update(
        created_at=timezone.now() - timedelta(days=31)
    )

    recent_draft = Agreement.objects.create(
        title="Recent Draft",
        status=AgreementStatus.DRAFT,
        created_by=user.account
    )

    result = cleanup_stale_drafts()

    assert result["deleted"] == 1
    assert Agreement.objects.filter(id=old_draft.id).exists() is False
    assert Agreement.objects.filter(id=recent_draft.id).exists() is True