from datetime import timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.agreements.services import AgreementService
from apps.audit.models import AuditLog
from apps.evidence.models import EvidenceItem
from apps.identity.models import IdentityRecord
from apps.parties.models import Party
from apps.vault.models import VaultEntry
from apps.vault.pdf import render_vault_pdf
from apps.vault.selectors import VaultSelector
from apps.vault.services import VaultService
from apps.vault.snapshot import build_export_snapshot

_seq = 0


def _account(email="vault@test.com"):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=f"+233{_seq:09d}")
    return Account.objects.create(user=user, email=email, phone=user.phone)


def _identity(account, ref=None):
    global _seq
    _seq += 1
    return IdentityRecord.objects.create(
        account=account,
        reference=ref or f"GC{_seq:06d}",
        verification_type="ghana_card",
    )


def _sealed_agreement(account):
    agreement = Agreement.objects.create(
        title="Test Agreement",
        scenario_template="cash_sale",
        created_by=account,
        status=AgreementStatus.ACTIVE,
    )
    id1 = _identity(account)
    id2 = _identity(account)
    party1 = Party.objects.create(
        agreement=agreement, identity=id1, role="buyer", display_name="Alice"
    )
    Party.objects.create(
        agreement=agreement, identity=id2, role="seller", display_name="Bob"
    )
    EvidenceItem.objects.create(
        agreement=agreement,
        uploaded_by=party1,
        file_type="photo",
        file_hash="abc123def456",
        original_name="photo.jpg",
    )
    return AgreementService.seal_agreement(agreement_id=agreement.pk)


class TestVaultEntryCreationOnSeal:
    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_creates_vault_entry_on_seal(self, mock_delay, db):
        account = _account("seal1@test.com")
        agreement = _sealed_agreement(account)
        assert VaultEntry.objects.filter(agreement=agreement).exists()
        entry = VaultEntry.objects.get(agreement=agreement)
        assert entry.export_status == VaultEntry.ExportStatus.PENDING
        assert entry.sealed_at == agreement.sealed_at
        assert entry.is_free_retention is True
        assert entry.retry_count == 0
        assert entry.archived is False

    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_records_audit_event(self, mock_delay, db):
        account = _account("seal2@test.com")
        _sealed_agreement(account)
        assert AuditLog.objects.filter(
            event_type="vault.entry_created",
            entity_type="vault_entry",
        ).exists()

    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_queues_celery_task(self, mock_delay, db):
        account = _account("seal3@test.com")
        agreement = _sealed_agreement(account)
        entry = VaultEntry.objects.get(agreement=agreement)
        mock_delay.assert_called_once_with(vault_entry_id=entry.pk)


class TestVaultListing:
    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_returns_only_owned_entries(self, mock_delay, db):
        acc1 = _account("list1@test.com")
        acc2 = _account("list2@test.com")
        _sealed_agreement(acc1)
        _sealed_agreement(acc2)
        qs = VaultSelector.list_entries(account_id=acc1.pk)
        assert qs.count() == 1

    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_filter_by_export_status(self, mock_delay, db):
        acc = _account("list3@test.com")
        _sealed_agreement(acc)
        entry = VaultEntry.objects.first()
        entry.export_status = VaultEntry.ExportStatus.COMPLETED
        entry.save()
        qs = VaultSelector.list_entries(
            account_id=acc.pk, export_status="completed"
        )
        assert qs.count() == 1
        qs2 = VaultSelector.list_entries(
            account_id=acc.pk, export_status="failed"
        )
        assert qs2.count() == 0

    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_exclude_archived_by_default(self, mock_delay, db):
        acc = _account("list4@test.com")
        _sealed_agreement(acc)
        entry = VaultEntry.objects.first()
        entry.archived = True
        entry.save()
        qs = VaultSelector.list_entries(account_id=acc.pk)
        assert qs.count() == 0

    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_include_archived_when_requested(self, mock_delay, db):
        acc = _account("list5@test.com")
        _sealed_agreement(acc)
        entry = VaultEntry.objects.first()
        entry.archived = True
        entry.save()
        qs = VaultSelector.list_entries(account_id=acc.pk, archived=True)
        assert qs.count() == 1


class TestVaultDetail:
    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_returns_entry_with_nested_data(self, mock_delay, db):
        acc = _account("det1@test.com")
        agreement = _sealed_agreement(acc)
        entry = VaultSelector.get_detail(agreement.pk, acc.pk)
        assert entry.agreement.title == "Test Agreement"
        assert agreement.parties.count() == 2

    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_raises_for_wrong_owner(self, mock_delay, db):
        acc1 = _account("det2@test.com")
        acc2 = _account("det3@test.com")
        agreement = _sealed_agreement(acc1)
        with pytest.raises(VaultEntry.DoesNotExist):
            VaultSelector.get_detail(agreement.pk, acc2.pk)

    def test_raises_for_missing_entry(self, db):
        acc = _account("det4@test.com")
        with pytest.raises(VaultEntry.DoesNotExist):
            VaultSelector.get_detail(99999, acc.pk)


class TestExportIdempotency:
    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_completed_returns_existing_pdf(self, mock_delay, db):
        acc = _account("exp1@test.com")
        agreement = _sealed_agreement(acc)
        entry = VaultEntry.objects.get(agreement=agreement)
        entry.export_status = VaultEntry.ExportStatus.COMPLETED
        entry.pdf_storage_key = "vault/1/test.pdf"
        entry.save()
        mock_delay.reset_mock()
        result = VaultService.trigger_export(entry.pk, acc)
        assert result["status"] == "completed"
        mock_delay.assert_not_called()

    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_pending_does_not_queue_again(self, mock_delay, db):
        acc = _account("exp2@test.com")
        agreement = _sealed_agreement(acc)
        entry = VaultEntry.objects.get(agreement=agreement)
        mock_delay.reset_mock()
        result = VaultService.trigger_export(entry.pk, acc)
        assert result["status"] == "pending"
        mock_delay.assert_not_called()

    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_failed_retries_and_increments_count(self, mock_delay, db):
        acc = _account("exp3@test.com")
        agreement = _sealed_agreement(acc)
        entry = VaultEntry.objects.get(agreement=agreement)
        entry.export_status = VaultEntry.ExportStatus.FAILED
        entry.save()
        mock_delay.reset_mock()
        result = VaultService.trigger_export(entry.pk, acc)
        assert result["status"] == "pending"
        entry.refresh_from_db()
        assert entry.retry_count == 1
        assert entry.export_status == VaultEntry.ExportStatus.PENDING
        mock_delay.assert_called_once_with(vault_entry_id=entry.pk)
        assert AuditLog.objects.filter(
            event_type="vault.export_retried",
            entity_id=str(entry.pk),
        ).exists()


class TestSnapshotBuilder:
    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_builds_complete_snapshot(self, mock_delay, db):
        acc = _account("snap1@test.com")
        agreement = _sealed_agreement(acc)
        snapshot = build_export_snapshot(agreement.pk)
        assert snapshot["agreement_id"] == agreement.pk
        assert snapshot["title"] == "Test Agreement"
        assert snapshot["scenario_template"] == "cash_sale"
        assert snapshot["sealed_at"] is not None
        assert len(snapshot["parties"]) == 2
        assert len(snapshot["evidence_items"]) == 1
        assert "snapshot_hash" in snapshot
        assert len(snapshot["snapshot_hash"]) == 64

    def test_handles_missing_optional_data(self, db):
        acc = _account("snap2@test.com")
        agreement = Agreement.objects.create(
            title="Empty Agreement",
            created_by=acc,
            status=AgreementStatus.SEALED,
            sealed_at=timezone.now(),
        )
        snapshot = build_export_snapshot(agreement.pk)
        assert snapshot["parties"] == []
        assert snapshot["evidence_items"] == []
        assert snapshot["consent_records"] == []
        assert "snapshot_hash" in snapshot


class TestPdfRenderer:
    def test_produces_pdf_bytes(self):
        snapshot = {
            "agreement_id": 1,
            "title": "Test",
            "scenario_template": "cash_sale",
            "sealed_at": "2026-01-01T00:00:00+00:00",
            "parties": [
                {"display_name": "Alice", "role": "buyer", "phone": "+233123"}
            ],
            "evidence_items": [
                {
                    "file_type": "photo",
                    "original_name": "photo.jpg",
                    "file_hash": "abc123",
                }
            ],
            "consent_records": [
                {"actor": "Alice", "consented_at": "2026-01-01T00:00:00+00:00"}
            ],
            "snapshot_hash": "a" * 64,
        }
        result = render_vault_pdf(snapshot)
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF")

    def test_deterministic_content(self):
        snapshot = {
            "agreement_id": 1,
            "title": "Test",
            "scenario_template": "",
            "sealed_at": "2026-01-01T00:00:00+00:00",
            "parties": [],
            "evidence_items": [],
            "consent_records": [],
            "snapshot_hash": "b" * 64,
        }
        first = render_vault_pdf(snapshot)
        second = render_vault_pdf(snapshot)
        assert first == second

    def test_handles_empty_sections(self):
        snapshot = {
            "agreement_id": 1,
            "title": "Empty",
            "scenario_template": "",
            "sealed_at": None,
            "parties": [],
            "evidence_items": [],
            "consent_records": [],
            "snapshot_hash": "c" * 64,
        }
        result = render_vault_pdf(snapshot)
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF")


class TestCeleryTask:
    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_successful_export(self, mock_delay, db):
        acc = _account("task1@test.com")
        agreement = _sealed_agreement(acc)
        entry = VaultEntry.objects.get(agreement=agreement)
        from apps.vault.tasks import generate_vault_pdf

        generate_vault_pdf(vault_entry_id=entry.pk)
        entry.refresh_from_db()
        assert entry.export_status == VaultEntry.ExportStatus.COMPLETED
        assert entry.pdf_storage_key.startswith("vault/")
        assert AuditLog.objects.filter(
            event_type="vault.export_generated",
            entity_id=str(entry.pk),
        ).exists()

    @patch("apps.vault.services.generate_vault_pdf.delay")
    @patch("apps.vault.tasks.S3StorageClient.upload", side_effect=Exception("S3 down"))
    def test_failed_export(self, mock_upload, mock_delay, db):
        acc = _account("task2@test.com")
        agreement = _sealed_agreement(acc)
        entry = VaultEntry.objects.get(agreement=agreement)
        from apps.vault.tasks import generate_vault_pdf

        with pytest.raises(Exception, match="S3 down"):
            generate_vault_pdf(vault_entry_id=entry.pk)
        entry.refresh_from_db()
        assert entry.export_status == VaultEntry.ExportStatus.FAILED
        assert AuditLog.objects.filter(
            event_type="vault.export_failed",
            entity_id=str(entry.pk),
        ).exists()

    def test_missing_entry_returns_silently(self, db):
        from apps.vault.tasks import generate_vault_pdf

        generate_vault_pdf(vault_entry_id=99999)


class TestRetentionFieldDefaults:
    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_retention_calculated_from_settings(self, mock_delay, db):
        acc = _account("ret1@test.com")
        agreement = _sealed_agreement(acc)
        entry = VaultEntry.objects.get(agreement=agreement)
        expected = agreement.sealed_at + timedelta(
            days=settings.VAULT_FREE_RETENTION_DAYS
        )
        assert entry.retention_until is not None
        assert abs((entry.retention_until - expected).total_seconds()) < 2

    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_is_free_retention_true(self, mock_delay, db):
        acc = _account("ret2@test.com")
        agreement = _sealed_agreement(acc)
        entry = VaultEntry.objects.get(agreement=agreement)
        assert entry.is_free_retention is True
