"""Integration tests for the consent and seal API endpoints.

Endpoints under test:
  POST /api/agreements/{id}/consent/request-otp/
  POST /api/agreements/{id}/consent/confirm/
  GET  /api/agreements/{id}/consent/status/
  POST /api/agreements/{id}/seal/
"""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.consent.models import ConsentRecord
from apps.consent.services import hash_otp
from apps.evidence.models import EvidenceItem
from apps.parties.services import PartyService

_REQUEST_OTP_PATH = "/api/agreements/{id}/consent/request-otp/"
_CONFIRM_PATH = "/api/agreements/{id}/consent/confirm/"
_STATUS_PATH = "/api/agreements/{id}/consent/status/"
_SEAL_PATH = "/api/agreements/{id}/seal/"

_seq = 0


def _make_client(phone):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(user=user, email=f"consent{_seq}@api.com", phone=phone)
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, account


def _draft_agreement(account):
    return Agreement.objects.create(title="Consent Test", created_by=account)


def _set_two_parties(agreement, initiator_phone, second_phone):
    acct = Account.objects.get(phone=initiator_phone)
    PartyService.set_parties(
        agreement_id=agreement.pk,
        initiator_account=acct,
        parties_data=[
            {
                "role": "seller",
                "full_name": "Kofi",
                "phone": initiator_phone,
                "id_type": "ghana_card",
                "id_number": "GHA-S",
            },
            {
                "role": "buyer",
                "full_name": "Ama",
                "phone": second_phone,
                "id_type": "ghana_card",
                "id_number": "GHA-B",
            },
        ],
    )


def _add_confirmed_evidence(agreement):
    EvidenceItem.objects.create(
        agreement=agreement,
        file_type=EvidenceItem.FileType.PHOTO,
        evidence_type="vehicle_photo_front",
        mime_type="image/jpeg",
        upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        storage_url="https://storage.kotoku/fake/photo.jpg",
    )


# ────────────────────────────────────────────────────────────────────────────
# POST /consent/request-otp/
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@patch("apps.consent.services.send_sms_message.delay", return_value=None)
class TestRequestOtpApi:
    def test_returns_201_with_consent_records(self, mock_delay):
        client, acct = _make_client("+233500100001")
        agreement = _draft_agreement(acct)
        _set_two_parties(agreement, acct.phone, "+233500100002")
        resp = client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["parties_count"] == 2
        assert len(data["consent_records"]) == 2

    def test_transitions_agreement_to_pending_consent(self, mock_delay):
        client, acct = _make_client("+233500100003")
        agreement = _draft_agreement(acct)
        _set_two_parties(agreement, acct.phone, "+233500100004")
        client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.PENDING_CONSENT

    def test_creates_consent_records_in_db(self, mock_delay):
        client, acct = _make_client("+233500100005")
        agreement = _draft_agreement(acct)
        _set_two_parties(agreement, acct.phone, "+233500100006")
        client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        assert ConsentRecord.objects.filter(agreement=agreement).count() == 2

    def test_reissue_from_pending_consent(self, mock_delay):
        client, acct = _make_client("+233500100007")
        agreement = _draft_agreement(acct)
        _set_two_parties(agreement, acct.phone, "+233500100008")
        # First issue → PENDING_CONSENT
        client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        first_ids = set(
            ConsentRecord.objects.filter(agreement=agreement).values_list("pk", flat=True)
        )
        # Re-issue → wipes old records, creates fresh set
        resp = client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        assert resp.status_code == 201
        second_ids = set(
            ConsentRecord.objects.filter(agreement=agreement).values_list("pk", flat=True)
        )
        assert first_ids.isdisjoint(second_ids)

    def test_reissue_blocked_when_all_consented(self, mock_delay):
        client, acct = _make_client("+233500100009")
        agreement = _draft_agreement(acct)
        _set_two_parties(agreement, acct.phone, "+233500100010")
        client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        ConsentRecord.objects.filter(agreement=agreement).update(granted=True)
        resp = client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        assert resp.status_code == 400

    def test_fails_with_fewer_than_two_parties(self, mock_delay):
        client, acct = _make_client("+233500100011")
        agreement = _draft_agreement(acct)
        resp = client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        assert resp.status_code == 400

    def test_other_users_agreement_returns_404(self, mock_delay):
        client, acct = _make_client("+233500100012")
        _, other_acct = _make_client("+233500100013")
        agreement = _draft_agreement(other_acct)
        resp = client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, mock_delay):
        _, acct = _make_client("+233500100014")
        agreement = _draft_agreement(acct)
        resp = APIClient().post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        assert resp.status_code == 401

    def test_sms_enqueue_failure_returns_503(self, mock_delay):
        mock_delay.side_effect = RuntimeError("SMS_API_KEY is not configured")
        client, acct = _make_client("+233500100015")
        agreement = _draft_agreement(acct)
        _set_two_parties(agreement, acct.phone, "+233500100016")
        resp = client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        assert resp.status_code == 503
        assert resp.json()["message"] == (
            "Consent codes could not be sent right now. Please try again."
        )
        assert ConsentRecord.objects.filter(agreement=agreement).count() == 0


# ────────────────────────────────────────────────────────────────────────────
# POST /consent/confirm/
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@patch("apps.consent.services.send_sms_message.delay", return_value=None)
class TestConfirmConsentApi:
    def _setup(self, initiator_phone, second_phone):
        client, acct = _make_client(initiator_phone)
        agreement = _draft_agreement(acct)
        _set_two_parties(agreement, acct.phone, second_phone)
        client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        return client, acct, agreement

    def _force_otp(self, agreement, phone, code):
        record = ConsentRecord.objects.get(
            agreement=agreement,
            party__phone=phone,
            granted=False,
        )
        ConsentRecord.objects.filter(pk=record.pk).update(otp_code_hash=hash_otp(code))
        return record

    def test_valid_otp_returns_200(self, mock_delay):
        client, acct, agreement = self._setup("+233500200001", "+233500200002")
        self._force_otp(agreement, acct.phone, "11111111")
        resp = client.post(
            _CONFIRM_PATH.format(id=agreement.pk),
            {"party_phone": acct.phone, "otp_code": "11111111"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["consent_record"]["granted"] is True

    def test_wrong_otp_returns_400(self, mock_delay):
        client, acct, agreement = self._setup("+233500200003", "+233500200004")
        resp = client.post(
            _CONFIRM_PATH.format(id=agreement.pk),
            {"party_phone": acct.phone, "otp_code": "00000000"},
            format="json",
        )
        assert resp.status_code == 400

    def test_unknown_phone_returns_400(self, mock_delay):
        client, acct, agreement = self._setup("+233500200005", "+233500200006")
        resp = client.post(
            _CONFIRM_PATH.format(id=agreement.pk),
            {"party_phone": "+233999999999", "otp_code": "12345678"},
            format="json",
        )
        assert resp.status_code == 403

    def test_cannot_confirm_another_party_phone(self, mock_delay):
        second_phone = "+233500200099"
        client, acct, agreement = self._setup("+233500200098", second_phone)
        self._force_otp(agreement, second_phone, "22222222")
        resp = client.post(
            _CONFIRM_PATH.format(id=agreement.pk),
            {"party_phone": second_phone, "otp_code": "22222222"},
            format="json",
        )
        assert resp.status_code == 403
        assert not ConsentRecord.objects.get(
            agreement=agreement,
            party__phone=second_phone,
        ).granted

    def test_invalid_phone_format_returns_400(self, mock_delay):
        client, acct, agreement = self._setup("+233500200007", "+233500200008")
        resp = client.post(
            _CONFIRM_PATH.format(id=agreement.pk),
            {"party_phone": "not-a-phone", "otp_code": "12345678"},
            format="json",
        )
        assert resp.status_code == 400

    def test_rate_limit_blocks_after_three_attempts(self, mock_delay):
        client, acct, agreement = self._setup("+233500200009", "+233500200010")
        for _ in range(3):
            client.post(
                _CONFIRM_PATH.format(id=agreement.pk),
                {"party_phone": acct.phone, "otp_code": "00000000"},
                format="json",
            )
        resp = client.post(
            _CONFIRM_PATH.format(id=agreement.pk),
            {"party_phone": acct.phone, "otp_code": "00000000"},
            format="json",
        )
        assert resp.status_code == 400
        assert "Too many" in resp.json()["message"]

    def test_unauthenticated_returns_401(self, mock_delay):
        _, acct = _make_client("+233500200011")
        agreement = _draft_agreement(acct)
        resp = APIClient().post(
            _CONFIRM_PATH.format(id=agreement.pk),
            {"party_phone": acct.phone, "otp_code": "12345678"},
            format="json",
        )
        assert resp.status_code == 401

    def test_other_users_agreement_returns_404(self, mock_delay):
        client, acct = _make_client("+233500200012")
        _, other_acct = _make_client("+233500200013")
        agreement = _draft_agreement(other_acct)
        resp = client.post(
            _CONFIRM_PATH.format(id=agreement.pk),
            {"party_phone": other_acct.phone, "otp_code": "12345678"},
            format="json",
        )
        assert resp.status_code == 404


# ────────────────────────────────────────────────────────────────────────────
# GET /consent/status/
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@patch("apps.consent.services.send_sms_message.delay", return_value=None)
class TestConsentStatusApi:
    def test_returns_status_with_records(self, mock_delay):
        client, acct = _make_client("+233500300001")
        agreement = _draft_agreement(acct)
        _set_two_parties(agreement, acct.phone, "+233500300002")
        client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        resp = client.get(_STATUS_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["all_consented"] is False
        assert len(data["records"]) == 2

    def test_all_consented_true_when_all_granted(self, mock_delay):
        client, acct = _make_client("+233500300003")
        agreement = _draft_agreement(acct)
        _set_two_parties(agreement, acct.phone, "+233500300004")
        client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        ConsentRecord.objects.filter(agreement=agreement).update(granted=True)
        resp = client.get(_STATUS_PATH.format(id=agreement.pk))
        assert resp.json()["data"]["all_consented"] is True

    def test_other_users_agreement_returns_404(self, mock_delay):
        client, acct = _make_client("+233500300005")
        _, other_acct = _make_client("+233500300006")
        agreement = _draft_agreement(other_acct)
        resp = client.get(_STATUS_PATH.format(id=agreement.pk))
        assert resp.status_code == 404


# ────────────────────────────────────────────────────────────────────────────
# POST /seal/
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@patch("apps.consent.services.send_sms_message.delay", return_value=None)
class TestSealApi:
    def _ready_to_seal(self, initiator_phone, second_phone):
        """Create an agreement that is ready to seal (all consented + evidence)."""
        client, acct = _make_client(initiator_phone)
        agreement = _draft_agreement(acct)
        _set_two_parties(agreement, acct.phone, second_phone)
        _add_confirmed_evidence(agreement)
        # Request OTPs
        client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        # Grant all consent records directly
        ConsentRecord.objects.filter(agreement=agreement).update(granted=True)
        return client, acct, agreement

    def test_seal_returns_200_with_sealed_status(self, mock_delay):
        client, acct, agreement = self._ready_to_seal("+233500400001", "+233500400002")
        resp = client.post(_SEAL_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        assert resp.json()["data"]["agreement"]["status"] == AgreementStatus.SEALED

    def test_agreement_is_sealed_in_db(self, mock_delay):
        client, acct, agreement = self._ready_to_seal("+233500400003", "+233500400004")
        client.post(_SEAL_PATH.format(id=agreement.pk))
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.SEALED
        assert agreement.sealed_at is not None

    def test_seal_fails_without_evidence(self, mock_delay):
        client, acct = _make_client("+233500400005")
        agreement = _draft_agreement(acct)
        _set_two_parties(agreement, acct.phone, "+233500400006")
        client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        ConsentRecord.objects.filter(agreement=agreement).update(granted=True)
        # No evidence added
        resp = client.post(_SEAL_PATH.format(id=agreement.pk))
        assert resp.status_code == 400

    def test_seal_fails_without_all_consent(self, mock_delay):
        client, acct = _make_client("+233500400007")
        agreement = _draft_agreement(acct)
        _set_two_parties(agreement, acct.phone, "+233500400008")
        _add_confirmed_evidence(agreement)
        client.post(_REQUEST_OTP_PATH.format(id=agreement.pk))
        # Only grant one party
        first_record = ConsentRecord.objects.filter(agreement=agreement).first()
        ConsentRecord.objects.filter(pk=first_record.pk).update(granted=True)
        resp = client.post(_SEAL_PATH.format(id=agreement.pk))
        assert resp.status_code == 400

    def test_seal_fails_when_already_sealed(self, mock_delay):
        client, acct, agreement = self._ready_to_seal("+233500400009", "+233500400010")
        client.post(_SEAL_PATH.format(id=agreement.pk))
        # Second seal attempt
        resp = client.post(_SEAL_PATH.format(id=agreement.pk))
        assert resp.status_code == 400

    def test_other_users_agreement_returns_404(self, mock_delay):
        client, acct = _make_client("+233500400011")
        _, other_acct = _make_client("+233500400012")
        agreement = _draft_agreement(other_acct)
        resp = client.post(_SEAL_PATH.format(id=agreement.pk))
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, mock_delay):
        _, acct = _make_client("+233500400013")
        agreement = _draft_agreement(acct)
        resp = APIClient().post(_SEAL_PATH.format(id=agreement.pk))
        assert resp.status_code == 401
