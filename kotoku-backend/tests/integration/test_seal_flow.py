"""Integration test: full seal flow → vault entry + PDF export.

Covers issue #8:
  create agreement → add parties → add evidence → bilateral consent
  → seal → verify vault entry → verify PDF export queued

Uses the console SMS backend to capture OTPs programmatically.
"""
import apps.vault.pdf  # noqa: F401
import re
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.agreements.services import AgreementService
from apps.audit.models import AuditLog
from apps.consent.models import ConsentRecord
from apps.evidence.models import EvidenceItem
from apps.parties.services import PartyService
from apps.vault.models import VaultEntry
from apps.vault.services import VaultService

_AGREEMENTS_PATH = "/api/agreements/"
_REQUEST_OTP_PATH = "/api/agreements/{id}/consent/request-otp/"
_CONFIRM_PATH = "/api/agreements/{id}/consent/confirm/"
_SEAL_PATH = "/api/agreements/{id}/seal/"
_VAULT_EXPORT = "/api/vault/{id}/export/"

_seq = 0


def _make_account(phone_suffix: str) -> tuple[Account, APIClient]:
    global _seq
    _seq += 1
    phone = f"+2338{phone_suffix}"
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(
        user=user, email=f"seal{_seq}@test.com", phone=phone,
    )
    token = AccessToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return account, client


def _otp_capture(to, body):
    match = re.search(r"\b(\d{6,8})\b", body)
    return match.group(1) if match else None


@pytest.mark.django_db
class TestFullSealFlow:
    def test_complete_seal_to_vault_and_pdf_export(self):
        acct, client = _make_account("00010001")
        seller_phone = acct.phone
        buyer_phone = "+233800010002"

        resp = client.post(
            _AGREEMENTS_PATH,
            data={
                "title": "Cash Sale — Toyota Corolla 2020",
                "description": "Full seal flow integration test.",
                "scenario_template": "used_vehicle_sale",
            },
            format="json",
        )
        assert resp.status_code == 201
        agreement_id = resp.json()["data"]["agreement"]["id"]
        assert resp.json()["data"]["agreement"]["status"] == AgreementStatus.DRAFT

        PartyService.set_parties(
            agreement_id=agreement_id,
            initiator_account=acct,
            parties_data=[
                {"role": "seller", "full_name": "Kofi Atta", "phone": seller_phone,
                 "id_type": "ghana_card", "id_number": "GHA-S-SEAL"},
                {"role": "buyer", "full_name": "Ama Owusu", "phone": buyer_phone,
                 "id_type": "ghana_card", "id_number": "GHA-B-SEAL"},
            ],
        )

        EvidenceItem.objects.create(
            agreement_id=agreement_id,
            file_type=EvidenceItem.FileType.PHOTO,
            evidence_type="vehicle_photo_front",
            mime_type="image/jpeg",
            upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            storage_url="https://storage.kotoku/fake/seal-flow.jpg",
        )

        otp_map = {}

        class MockGateway:
            def send(self, to, body):
                otp = _otp_capture(to, body)
                if otp:
                    otp_map[to] = otp
                return True

        with patch("apps.consent.services.get_sms_gateway", return_value=MockGateway()):
            resp = client.post(_REQUEST_OTP_PATH.format(id=agreement_id))
        assert resp.status_code == 201
        assert len(otp_map) == 2

        agr = Agreement.objects.get(pk=agreement_id)
        assert agr.status == AgreementStatus.PENDING_CONSENT

        for phone, otp in otp_map.items():
            resp = client.post(
                _CONFIRM_PATH.format(id=agreement_id),
                data={"party_phone": phone, "otp_code": otp},
                format="json",
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["consent_record"]["granted"] is True

        assert ConsentRecord.objects.filter(
            agreement_id=agreement_id, granted=True,
        ).count() == 2

        resp = client.post(_SEAL_PATH.format(id=agreement_id))
        assert resp.status_code == 200
        seal_data = resp.json()["data"]["agreement"]
        assert seal_data["status"] == AgreementStatus.SEALED
        assert seal_data["sealed_at"] is not None
        assert seal_data["seal_hash"] != ""

        vault_entry = VaultEntry.objects.get(agreement_id=agreement_id)
        assert vault_entry.pdf_status == VaultEntry.PdfStatus.PENDING

        fake_pdf = b"%PDF-fake-seal-flow"
        fake_url = "https://storage.kotoku/exports/seal-flow-test.pdf"

        with patch("apps.vault.pdf.render_vault_pdf", return_value=fake_pdf), \
             patch("infrastructure.storage.s3.S3StorageClient.upload", return_value=fake_url):
            resp = client.post(_VAULT_EXPORT.format(id=agreement_id))

        assert resp.status_code == 202
        assert resp.json()["data"]["vault_entry"]["pdf_status"] == VaultEntry.PdfStatus.GENERATING

        vault_entry.refresh_from_db()
        assert vault_entry.pdf_status == VaultEntry.PdfStatus.READY
        assert vault_entry.pdf_url == fake_url

        audit_events = set(
            AuditLog.objects.filter(
                entity_type="agreement", entity_id=str(agreement_id),
            ).values_list("event_type", flat=True)
        )
        assert "agreement.created" in audit_events
        assert "agreement.consent_requested" in audit_events
        assert "agreement.sealed" in audit_events

        assert AuditLog.objects.filter(
            entity_type="consent_record",
            event_type__in=["consent.granted", "consent.otp_issued"],
        ).count() >= 2

        vault_audit = set(
            AuditLog.objects.filter(
                entity_type="vault_entry", entity_id=str(vault_entry.pk),
            ).values_list("event_type", flat=True)
        )
        assert "vault.entry_created" in vault_audit
        assert "vault.export_requested" in vault_audit
        assert "vault.export_ready" in vault_audit

    def test_seal_api_auto_creates_vault_entry(self):
        acct, client = _make_account("00020001")
        agr = AgreementService.create_draft(
            title="Vault Auto", created_by=acct, scenario_template="used_vehicle_sale",
        )
        PartyService.set_parties(
            agreement_id=agr.pk,
            initiator_account=acct,
            parties_data=[
                {"role": "seller", "full_name": "S", "phone": acct.phone,
                 "id_type": "ghana_card", "id_number": "GHA-VAS"},
                {"role": "buyer", "full_name": "B", "phone": "+233800020002",
                 "id_type": "ghana_card", "id_number": "GHA-VAB"},
            ],
        )
        EvidenceItem.objects.create(
            agreement=agr,
            file_type=EvidenceItem.FileType.PHOTO,
            evidence_type="vehicle_photo_front",
            mime_type="image/jpeg",
            upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            storage_url="https://storage.kotoku/fake/vault-auto.jpg",
        )
        agr.status = AgreementStatus.PENDING_CONSENT
        agr.save()
        for p in agr.parties.all():
            ConsentRecord.objects.create(
                agreement=agr, party=p, otp_code_hash="fakehash",
                channel=ConsentRecord.Channel.SMS, granted=True,
                granted_at=timezone.now(),
                expires_at=timezone.now() + timedelta(minutes=10),
            )

        resp = client.post(_SEAL_PATH.format(id=agr.pk))
        assert resp.status_code == 200

        entry = VaultEntry.objects.get(agreement_id=agr.pk)
        assert entry.pdf_status == VaultEntry.PdfStatus.PENDING

    def test_pdf_celery_task_runs_and_marks_ready(self):
        acct, _ = _make_account("00030001")
        agr = AgreementService.create_draft(
            title="Celery PDF", created_by=acct, scenario_template="used_vehicle_sale",
        )
        PartyService.set_parties(
            agreement_id=agr.pk,
            initiator_account=acct,
            parties_data=[
                {"role": "seller", "full_name": "S", "phone": acct.phone,
                 "id_type": "ghana_card", "id_number": "GHA-CS"},
                {"role": "buyer", "full_name": "B", "phone": "+233800030002",
                 "id_type": "ghana_card", "id_number": "GHA-CB"},
            ],
        )
        EvidenceItem.objects.create(
            agreement=agr,
            file_type=EvidenceItem.FileType.PHOTO,
            evidence_type="vehicle_photo_front",
            mime_type="image/jpeg",
            upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            storage_url="https://storage.kotoku/fake/celery.jpg",
        )
        agr.status = AgreementStatus.PENDING_CONSENT
        agr.save()
        for p in agr.parties.all():
            ConsentRecord.objects.create(
                agreement=agr, party=p, otp_code_hash="fakehash",
                channel=ConsentRecord.Channel.SMS, granted=True,
                granted_at=timezone.now(),
                expires_at=timezone.now() + timedelta(minutes=10),
            )
        agr = AgreementService.seal_agreement(agreement_id=agr.pk)
        entry = VaultService.create_for_agreement(agreement_id=agr.pk)

        from apps.vault.tasks import generate_pdf_export
        fake_pdf = b"%PDF-celery-test"
        fake_url = "https://storage.kotoku/exports/celery-test.pdf"

        with patch("apps.vault.pdf.render_vault_pdf", return_value=fake_pdf), \
             patch("infrastructure.storage.s3.S3StorageClient.upload", return_value=fake_url):
            generate_pdf_export(entry.pk)

        entry.refresh_from_db()
        assert entry.pdf_status == VaultEntry.PdfStatus.READY
        assert entry.pdf_url == fake_url
        assert AuditLog.objects.filter(
            event_type="vault.export_ready", entity_id=str(entry.pk),
        ).exists()
