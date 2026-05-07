"""Integration tests for the vault API.

Endpoints under test:
  GET  /api/vault/
  GET  /api/vault/{agreementId}/
  POST /api/vault/{agreementId}/export/
"""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

import apps.vault.pdf  # noqa: F401 — ensures submodule is loaded so patch() can resolve it
from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.consent.models import ConsentRecord
from apps.evidence.models import EvidenceItem
from apps.parties.services import PartyService
from apps.vault.models import VaultEntry
from apps.vault.services import VaultService

_LIST_PATH = "/api/vault/"
_DETAIL_PATH = "/api/vault/{id}/"
_EXPORT_PATH = "/api/vault/{id}/export/"
_RETRY_PATH = "/api/vault/{id}/retry-export/"

_seq = 0


def _make_client(phone):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(user=user, email=f"vault{_seq}@api.com", phone=phone)
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client, account


def _sealed_agreement_with_vault(account, initiator_phone, second_phone):
    agreement = Agreement.objects.create(
        title="Vault Test",
        created_by=account,
        scenario_template="used_vehicle_sale",
    )
    PartyService.set_parties(
        agreement_id=agreement.pk,
        initiator_account=account,
        parties_data=[
            {"role": "seller", "full_name": "Kofi", "phone": initiator_phone,
             "id_type": "ghana_card", "id_number": "GHA-S"},
            {"role": "buyer", "full_name": "Ama", "phone": second_phone,
             "id_type": "ghana_card", "id_number": "GHA-B"},
        ],
    )
    EvidenceItem.objects.create(
        agreement=agreement,
        file_type=EvidenceItem.FileType.PHOTO,
        evidence_type="vehicle_photo_front",
        mime_type="image/jpeg",
        upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        storage_url="https://storage.kotoku/fake/photo.jpg",
    )
    agreement.status = AgreementStatus.PENDING_CONSENT
    agreement.save()
    now = timezone.now()
    ConsentRecord.objects.bulk_create([
        ConsentRecord(
            agreement=agreement,
            party=p,
            otp_code_hash="fakehash",
            channel=ConsentRecord.Channel.SMS,
            granted=True,
            granted_at=now,
            expires_at=now + timedelta(minutes=10),
        )
        for p in agreement.parties.all()
    ])
    from apps.agreements.services import AgreementService
    agreement = AgreementService.seal_agreement(agreement_id=agreement.pk)

    fake_pdf = b"%PDF-fake"
    fake_url = "https://storage.kotoku/exports/test.pdf"
    with patch("apps.vault.pdf.render_vault_pdf", return_value=fake_pdf), \
         patch("infrastructure.storage.s3.S3StorageClient.upload", return_value=fake_url):
        entry = VaultService.create_for_agreement(agreement_id=agreement.pk)

    return agreement, entry


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/vault/
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestVaultList:
    def test_returns_200_and_lists_entries(self):
        client, acct = _make_client("+233700100001")
        _sealed_agreement_with_vault(acct, acct.phone, "+233700100002")
        resp = client.get(_LIST_PATH)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["count"] == 1
        assert len(data["results"]) == 1

    def test_does_not_return_other_users_entries(self):
        client, acct = _make_client("+233700100003")
        _, other_acct = _make_client("+233700100004")
        _sealed_agreement_with_vault(other_acct, other_acct.phone, "+233700100005")
        resp = client.get(_LIST_PATH)
        assert resp.status_code == 200
        assert resp.json()["data"]["count"] == 0

    def test_unauthenticated_returns_401(self):
        resp = APIClient().get(_LIST_PATH)
        assert resp.status_code == 401

    def test_entry_shape(self):
        client, acct = _make_client("+233700100006")
        _sealed_agreement_with_vault(acct, acct.phone, "+233700100007")
        resp = client.get(_LIST_PATH)
        entry = resp.json()["data"]["results"][0]
        assert "id" in entry
        assert "agreement" in entry
        assert "pdf_status" in entry
        assert "retain_until" in entry
        assert entry["pdf_status"] == VaultEntry.PdfStatus.PENDING


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/vault/{agreementId}/
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestVaultDetail:
    def test_returns_200_with_vault_entry(self):
        client, acct = _make_client("+233700200001")
        agreement, _ = _sealed_agreement_with_vault(acct, acct.phone, "+233700200002")
        resp = client.get(_DETAIL_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        data = resp.json()["data"]["vault_entry"]
        assert data["agreement"]["id"] == agreement.pk
        assert data["agreement"]["status"] == AgreementStatus.SEALED
        assert data["agreement"]["seal_hash"] != ""

    def test_returns_404_for_other_users_agreement(self):
        client, acct = _make_client("+233700200003")
        _, other_acct = _make_client("+233700200004")
        agreement, _ = _sealed_agreement_with_vault(other_acct, other_acct.phone, "+233700200005")
        resp = client.get(_DETAIL_PATH.format(id=agreement.pk))
        assert resp.status_code == 404

    def test_returns_404_for_nonexistent_agreement(self):
        client, _ = _make_client("+233700200006")
        resp = client.get(_DETAIL_PATH.format(id=99999))
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self):
        resp = APIClient().get(_DETAIL_PATH.format(id=1))
        assert resp.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/vault/{agreementId}/export/
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestVaultExport:
    def test_export_returns_202_and_triggers_task(self):
        client, acct = _make_client("+233700300001")
        agreement, _ = _sealed_agreement_with_vault(acct, acct.phone, "+233700300002")

        fake_pdf = b"%PDF-fake"
        fake_url = "https://storage.kotoku/exports/test.pdf"

        with patch("apps.vault.pdf.render_vault_pdf", return_value=fake_pdf), \
             patch("infrastructure.storage.s3.S3StorageClient.upload", return_value=fake_url):
            resp = client.post(_EXPORT_PATH.format(id=agreement.pk))

        assert resp.status_code == 202
        # The 202 response reflects the moment the task was enqueued (generating).
        # In production, the client polls GET /vault/{id}/ to see when it's ready.
        data = resp.json()["data"]["vault_entry"]
        assert data["pdf_status"] == VaultEntry.PdfStatus.GENERATING

        # With CELERY_TASK_ALWAYS_EAGER=True the task ran synchronously, so the
        # DB record should already be updated to READY.
        from apps.vault.models import VaultEntry as VE
        entry_db = VE.objects.get(agreement=agreement)
        assert entry_db.pdf_status == VE.PdfStatus.READY
        assert entry_db.pdf_url == fake_url

    def test_export_marks_failed_on_pdf_error(self):
        client, acct = _make_client("+233700300003")
        agreement, _ = _sealed_agreement_with_vault(acct, acct.phone, "+233700300004")

        with patch("apps.vault.pdf.render_vault_pdf", side_effect=RuntimeError("render fail")):
            # Eager Celery will raise after max_retries — suppress it
            try:
                client.post(_EXPORT_PATH.format(id=agreement.pk))
            except Exception:
                pass

        entry = VaultEntry.objects.get(agreement=agreement)
        assert entry.pdf_status == VaultEntry.PdfStatus.FAILED

    def test_export_blocked_while_already_generating(self):
        client, acct = _make_client("+233700300005")
        agreement, entry = _sealed_agreement_with_vault(acct, acct.phone, "+233700300006")
        entry.pdf_status = VaultEntry.PdfStatus.GENERATING
        entry.save()

        resp = client.post(_EXPORT_PATH.format(id=agreement.pk))
        assert resp.status_code == 400

    def test_export_returns_404_for_other_users_agreement(self):
        client, acct = _make_client("+233700300007")
        _, other_acct = _make_client("+233700300008")
        agreement, _ = _sealed_agreement_with_vault(other_acct, other_acct.phone, "+233700300009")
        resp = client.post(_EXPORT_PATH.format(id=agreement.pk))
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self):
        resp = APIClient().post(_EXPORT_PATH.format(id=1))
        assert resp.status_code == 401


from apps.vault.api.audit import build_audit_timeline

_AUDIT_PATH = "/api/vault/{id}/audit-log/"


@pytest.mark.django_db
class TestVaultAuditLog:
    def test_returns_200_with_events(self):
        client, acct = _make_client("+233700400001")
        agreement, _ = _sealed_agreement_with_vault(acct, acct.phone, "+233700400002")
        resp = client.get(_AUDIT_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        events = resp.json()["data"]["events"]
        assert len(events) >= 1
        types = [e["type"] for e in events]
        assert "agreement_created" in types
        assert "sealed" in types

    def test_events_include_parties_and_evidence(self):
        client, acct = _make_client("+233700400003")
        agreement, _ = _sealed_agreement_with_vault(acct, acct.phone, "+233700400004")
        resp = client.get(_AUDIT_PATH.format(id=agreement.pk))
        types = [e["type"] for e in resp.json()["data"]["events"]]
        assert "party_added" in types
        assert "evidence_uploaded" in types

    def test_returns_404_for_other_users_agreement(self):
        client, acct = _make_client("+233700400005")
        _, other_acct = _make_client("+233700400006")
        agreement, _ = _sealed_agreement_with_vault(other_acct, other_acct.phone, "+233700400007")
        resp = client.get(_AUDIT_PATH.format(id=agreement.pk))
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self):
        resp = APIClient().get(_AUDIT_PATH.format(id=1))
        assert resp.status_code == 401

    def test_build_audit_timeline_includes_consent(self):
        client, acct = _make_client("+233700400008")
        agreement, _ = _sealed_agreement_with_vault(acct, acct.phone, "+233700400009")
        events = build_audit_timeline(agreement)
        types = [e["type"] for e in events]
        assert "consent_requested" in types
        assert "consent_confirmed" in types

    def test_build_audit_timeline_sorted_by_timestamp(self):
        client, acct = _make_client("+233700400010")
        agreement, _ = _sealed_agreement_with_vault(acct, acct.phone, "+233700400011")
        events = build_audit_timeline(agreement)
        timestamps = [e["timestamp"] for e in events]
        assert timestamps == sorted(timestamps)


@pytest.mark.django_db
class TestVaultRetryExport:
    def test_retry_failed_returns_202(self):
        client, acct = _make_client("+233700500001")
        agreement, entry = _sealed_agreement_with_vault(acct, acct.phone, "+233700500002")
        entry.pdf_status = VaultEntry.PdfStatus.FAILED
        entry.save()

        fake_pdf = b"%PDF-fake"
        fake_url = "https://storage.kotoku/exports/retry.pdf"
        with patch("apps.vault.pdf.render_vault_pdf", return_value=fake_pdf), \
             patch("infrastructure.storage.s3.S3StorageClient.upload", return_value=fake_url):
            resp = client.post(_RETRY_PATH.format(id=agreement.pk))

        assert resp.status_code == 202
        data = resp.json()["data"]["vault_entry"]
        assert data["pdf_status"] in (VaultEntry.PdfStatus.READY, VaultEntry.PdfStatus.PENDING)

    def test_retry_non_failed_returns_400(self):
        client, acct = _make_client("+233700500003")
        agreement, entry = _sealed_agreement_with_vault(acct, acct.phone, "+233700500004")

        resp = client.post(_RETRY_PATH.format(id=agreement.pk))
        assert resp.status_code == 400

    def test_retry_returns_404_for_other_users_agreement(self):
        client, acct = _make_client("+233700500007")
        _, other_acct = _make_client("+233700500008")
        agreement, entry = _sealed_agreement_with_vault(
            other_acct, other_acct.phone, "+233700500009"
        )
        entry.pdf_status = VaultEntry.PdfStatus.FAILED
        entry.save()

        resp = client.post(_RETRY_PATH.format(id=agreement.pk))
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self):
        resp = APIClient().post(_RETRY_PATH.format(id=1))
        assert resp.status_code == 401
