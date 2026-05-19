import pytest
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.utils import timezone

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.vault.models import VaultEntry
from apps.vault.tasks import archive_expired_vault_entries, recover_stuck_pdf_generating


def _make_vault_entry(pdf_status=VaultEntry.PdfStatus.PENDING):
    user = User.objects.create_user(phone=f"+23354{VaultEntry.objects.count():07d}")
    account = Account.objects.create(user=user, email=f"v{user.pk}@test.com", phone=user.phone)
    agreement = Agreement.objects.create(
        title="Vault Test",
        scenario_template="used_vehicle_sale",
        status=AgreementStatus.SEALED,
        created_by=account,
        sealed_at=timezone.now(),
        seal_hash="testhash",
    )
    return VaultEntry.objects.create(
        agreement=agreement,
        pdf_status=pdf_status,
    )


@pytest.mark.django_db
class TestArchiveExpiredVaultEntries:
    def test_archives_expired_entries(self):
        entry = _make_vault_entry()
        entry.retain_until = timezone.now() - timedelta(days=1)
        entry.save()
        result = archive_expired_vault_entries()
        assert result["archived"] == 1
        entry.refresh_from_db()
        assert entry.archived is True

    def test_skips_unexpired_entries(self):
        entry = _make_vault_entry()
        entry.retain_until = timezone.now() + timedelta(days=365)
        entry.save()
        result = archive_expired_vault_entries()
        assert result["archived"] == 0
        entry.refresh_from_db()
        assert entry.archived is False

    def test_skips_already_archived(self):
        entry = _make_vault_entry()
        entry.retain_until = timezone.now() - timedelta(days=1)
        entry.archived = True
        entry.save()
        result = archive_expired_vault_entries()
        assert result["archived"] == 0

    def test_returns_zero_when_nothing_to_archive(self):
        result = archive_expired_vault_entries()
        assert result == {"archived": 0}


@pytest.mark.django_db
class TestRecoverStuckPdfGenerating:
    def test_recovers_stuck_generating_entries(self):
        entry = _make_vault_entry(pdf_status=VaultEntry.PdfStatus.GENERATING)
        # Force updated_at to be older than 5 minutes
        VaultEntry.objects.filter(pk=entry.pk).update(
            updated_at=timezone.now() - timedelta(minutes=10)
        )
        result = recover_stuck_pdf_generating()
        assert result["recovered"] == 1
        entry.refresh_from_db()
        assert entry.pdf_status == VaultEntry.PdfStatus.FAILED

    def test_skips_recently_generating_entries(self):
        entry = _make_vault_entry(pdf_status=VaultEntry.PdfStatus.GENERATING)
        result = recover_stuck_pdf_generating()
        assert result["recovered"] == 0
        entry.refresh_from_db()
        assert entry.pdf_status == VaultEntry.PdfStatus.GENERATING

    def test_returns_zero_when_nothing_stuck(self):
        result = recover_stuck_pdf_generating()
        assert result == {"recovered": 0}
