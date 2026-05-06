"""Integration test: bilateral reopen flow.

Covers issue #9:
  sealed agreement → reopen request → both parties OTP confirm → ACTIVE
  + cancel_reopen → back to SEALED
"""
import re
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.agreements.services import AgreementService
from apps.audit.models import AuditLog
from apps.consent.models import ConsentRecord
from apps.consent.services import generate_otp, hash_otp
from apps.evidence.models import EvidenceItem
from apps.parties.services import PartyService
from apps.vault.models import VaultEntry
from apps.vault.services import VaultService

_REOPEN_REQUEST = "/api/agreements/{id}/reopen-request/"
_REOPEN_OTP_REQ = "/api/agreements/{id}/reopen-consent/request-otp/"
_REOPEN_OTP_CONFIRM = "/api/agreements/{id}/reopen-consent/confirm/"

_seq = 0


def _make_account(phone_suffix: str) -> tuple[Account, APIClient]:
    global _seq
    _seq += 1
    phone = f"+2339{phone_suffix}"
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(
        user=user, email=f"reopen{_seq}@test.com", phone=phone,
    )
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return account, client


def _sealed_agreement(account, seller_phone, buyer_phone):
    agr = AgreementService.create_draft(
        title="Reopen Test", created_by=account, scenario_template="used_vehicle_sale",
    )
    PartyService.set_parties(
        agreement_id=agr.pk,
        initiator_account=account,
        parties_data=[
            {"role": "seller", "full_name": "Kofi", "phone": seller_phone,
             "id_type": "ghana_card", "id_number": "GHA-RS"},
            {"role": "buyer", "full_name": "Ama", "phone": buyer_phone,
             "id_type": "ghana_card", "id_number": "GHA-RB"},
        ],
    )
    EvidenceItem.objects.create(
        agreement=agr,
        file_type=EvidenceItem.FileType.PHOTO,
        evidence_type="vehicle_photo_front",
        mime_type="image/jpeg",
        upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        storage_url="https://storage.kotoku/fake/reopen.jpg",
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
    VaultService.create_for_agreement(agreement_id=agr.pk)
    return agr


def _otp_capture(to, body):
    match = re.search(r"\b(\d{6,8})\b", body)
    return match.group(1) if match else None


@pytest.mark.django_db
class TestBilateralReopenFlow:
    def test_full_reopen_both_parties_confirm_returns_active(self):
        acct, client = _make_account("00010001")
        seller_phone = acct.phone
        buyer_phone = "+233900010002"
        agr = _sealed_agreement(acct, seller_phone, buyer_phone)

        otp_map = {}

        def _capture(to, body):
            otp = _otp_capture(to, body)
            if otp:
                otp_map[to] = otp
            return True

        with patch("infrastructure.sms.gateway.SmsGateway.send", side_effect=_capture):
            resp = client.post(_REOPEN_REQUEST.format(id=agr.pk))
        assert resp.status_code == 200
        assert resp.json()["data"]["agreement"]["status"] == AgreementStatus.REOPEN_REQUESTED
        assert len(otp_map) == 2

        agr.refresh_from_db()
        assert agr.status == AgreementStatus.REOPEN_REQUESTED

        assert AuditLog.objects.filter(
            event_type="agreement.reopen_requested",
            entity_type="agreement",
            entity_id=str(agr.pk),
        ).exists()

        for phone, otp in otp_map.items():
            resp = client.post(
                _REOPEN_OTP_CONFIRM.format(id=agr.pk),
                data={"phone": phone, "otp_code": otp},
                format="json",
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["granted"] is True

        agr.refresh_from_db()
        assert agr.status == AgreementStatus.ACTIVE
        assert agr.sealed_at is None
        assert agr.seal_hash == ""

        assert AuditLog.objects.filter(
            event_type="agreement.reopened_bilateral",
            entity_type="agreement",
            entity_id=str(agr.pk),
        ).exists()

        reopen_audit = AuditLog.objects.filter(
            event_type="consent.reopen_granted",
            entity_type="consent_record",
        )
        assert reopen_audit.count() == 2

    def test_first_confirm_keeps_reopen_requested(self):
        acct, client = _make_account("00020001")
        seller_phone = acct.phone
        buyer_phone = "+233900020002"
        agr = _sealed_agreement(acct, seller_phone, buyer_phone)

        otp_map = {}

        def _capture(to, body):
            otp = _otp_capture(to, body)
            if otp:
                otp_map[to] = otp
            return True

        with patch("infrastructure.sms.gateway.SmsGateway.send", side_effect=_capture):
            client.post(_REOPEN_REQUEST.format(id=agr.pk))

        first_phone = seller_phone
        first_otp = otp_map[first_phone]
        resp = client.post(
            _REOPEN_OTP_CONFIRM.format(id=agr.pk),
            data={"phone": first_phone, "otp_code": first_otp},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["granted"] is True

        agr.refresh_from_db()
        assert agr.status == AgreementStatus.REOPEN_REQUESTED

    def test_cancel_reopen_returns_to_sealed(self):
        acct, client = _make_account("00030001")
        seller_phone = acct.phone
        buyer_phone = "+233900030002"
        agr = _sealed_agreement(acct, seller_phone, buyer_phone)

        with patch("infrastructure.sms.gateway.SmsGateway.send", return_value=True):
            client.post(_REOPEN_REQUEST.format(id=agr.pk))

        result = AgreementService.cancel_reopen(agreement_id=agr.pk)
        assert result.status == AgreementStatus.SEALED

        assert AuditLog.objects.filter(
            event_type="agreement.reopen_cancelled",
            entity_type="agreement",
            entity_id=str(agr.pk),
        ).exists()

    def test_reopen_otp_reissue(self):
        acct, client = _make_account("00040001")
        seller_phone = acct.phone
        buyer_phone = "+233900040002"
        agr = _sealed_agreement(acct, seller_phone, buyer_phone)

        with patch("infrastructure.sms.gateway.SmsGateway.send", return_value=True):
            client.post(_REOPEN_REQUEST.format(id=agr.pk))

        first_count = ConsentRecord.objects.filter(
            agreement=agr, purpose=ConsentRecord.Purpose.REOPEN,
        ).count()
        assert first_count == 2

        with patch("infrastructure.sms.gateway.SmsGateway.send", return_value=True):
            resp = client.post(_REOPEN_OTP_REQ.format(id=agr.pk))
        assert resp.status_code == 200

        second_count = ConsentRecord.objects.filter(
            agreement=agr, purpose=ConsentRecord.Purpose.REOPEN,
        ).count()
        assert second_count == 2

    def test_reopen_request_audit_events(self):
        acct, client = _make_account("00050001")
        seller_phone = acct.phone
        buyer_phone = "+233900050002"
        agr = _sealed_agreement(acct, seller_phone, buyer_phone)

        with patch("infrastructure.sms.gateway.SmsGateway.send", return_value=True):
            client.post(_REOPEN_REQUEST.format(id=agr.pk))

        reopen_otp_audit = AuditLog.objects.filter(
            event_type="consent.reopen_otp_issued",
            entity_type="consent_record",
        )
        assert reopen_otp_audit.count() == 2
