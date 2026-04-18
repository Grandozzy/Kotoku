from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Account
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.services import AgreementService
from apps.audit.models import AuditLog
from apps.consent.models import ConsentRecord
from apps.consent.selectors import ConsentSelector
from apps.consent.services import (
    ConsentService,
    generate_otp,
    generate_otp_expiry,
    hash_otp,
    verify_otp_hash,
)
from apps.consent.tasks import sync_consent
from apps.identity.models import IdentityRecord
from apps.notifications.models import Notification
from apps.parties.models import Party
from common.exceptions import DomainError


def _account(email="user@test.com"):
    return Account.objects.create(email=email)


def _identity(account, ref="ref-1"):
    return IdentityRecord.objects.create(
        account=account,
        reference=ref,
        verification_type="ghana_card",
    )


def _agreement_with_parties():
    a1 = _account("buyer@test.com")
    a2 = _account("seller@test.com")
    id1 = _identity(a1, "ref-buyer")
    id2 = _identity(a2, "ref-seller")
    agreement = AgreementService.create_draft(title="Test Agreement", created_by=a1)
    AgreementService.add_party(
        agreement_id=agreement.pk,
        identity_id=id1.pk,
        role=Party.Role.BUYER,
        display_name="Buyer",
    )
    AgreementService.add_party(
        agreement_id=agreement.pk,
        identity_id=id2.pk,
        role=Party.Role.SELLER,
        display_name="Seller",
    )
    AgreementService.request_consent(agreement_id=agreement.pk)
    agreement.refresh_from_db()
    return agreement


class TestGenerateOtp:
    def test_returns_numeric_string(self):
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_respects_length(self):
        assert len(generate_otp(4)) == 4


class TestHashOtp:
    def test_known_input(self):
        result = hash_otp("123456")
        assert len(result) == 64

    def test_deterministic(self):
        assert hash_otp("abc") == hash_otp("abc")


class TestVerifyOtpHash:
    def test_correct_otp(self):
        otp = "654321"
        assert verify_otp_hash(otp, hash_otp(otp)) is True

    def test_wrong_otp(self):
        assert verify_otp_hash("000000", hash_otp("111111")) is False


class TestGenerateOtpExpiry:
    def test_in_future(self):
        expires = generate_otp_expiry(minutes=10)
        assert expires > timezone.now()

    def test_custom_minutes(self):
        expires = generate_otp_expiry(minutes=5)
        expected = timezone.now() + timedelta(minutes=5)
        assert abs((expires - expected).total_seconds()) < 2


class TestRequestConsent:
    def test_creates_consent_records_for_all_parties(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        assert len(records) == 2
        assert all(isinstance(r, ConsentRecord) for r in records)

    def test_hashes_otp(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        for record in records:
            assert len(record.otp_code_hash) == 64

    def test_creates_notifications(self, db):
        agreement = _agreement_with_parties()
        ConsentService.request_consent(agreement_id=agreement.pk)
        assert Notification.objects.count() == 2
        for n in Notification.objects.all():
            assert n.status == Notification.Status.PENDING
            assert "verification code" in n.body.lower()

    def test_emits_audit_events(self, db):
        agreement = _agreement_with_parties()
        ConsentService.request_consent(agreement_id=agreement.pk)
        assert AuditLog.objects.filter(event_type="consent.requested").count() == 2

    def test_raises_when_not_pending_consent(self, db):
        account = _account("x@test.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        with pytest.raises(DomainError, match="pending_consent"):
            ConsentService.request_consent(agreement_id=agreement.pk)

    def test_raises_when_no_parties(self, db):
        account = _account("y@test.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        agreement.status = AgreementStatus.PENDING_CONSENT
        agreement.save()
        with pytest.raises(DomainError, match="no parties"):
            ConsentService.request_consent(agreement_id=agreement.pk)


class TestVerifyOtp:
    def test_grants_on_valid_otp(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        record = records[0]
        ConsentRecord.objects.filter(pk=record.pk).update(
            otp_code_hash=hash_otp("111111")
        )
        result = ConsentService.verify_otp(
            consent_record_id=record.pk, otp_code="111111"
        )
        assert result.granted is True
        assert result.granted_at is not None

    def test_emits_audit_on_grant(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        record = records[0]
        ConsentRecord.objects.filter(pk=record.pk).update(
            otp_code_hash=hash_otp("222222")
        )
        ConsentService.verify_otp(consent_record_id=record.pk, otp_code="222222")
        assert AuditLog.objects.filter(event_type="consent.granted").exists()

    def test_raises_on_wrong_otp(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        with pytest.raises(DomainError, match="Invalid OTP"):
            ConsentService.verify_otp(
                consent_record_id=records[0].pk, otp_code="000000"
            )

    def test_raises_on_expired_otp(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        record = records[0]
        ConsentRecord.objects.filter(pk=record.pk).update(
            otp_code_hash=hash_otp("333333"), expires_at=timezone.now() - timedelta(minutes=1)
        )
        with pytest.raises(DomainError, match="expired"):
            ConsentService.verify_otp(
                consent_record_id=record.pk, otp_code="333333"
            )

    def test_raises_on_already_granted(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        record = records[0]
        ConsentRecord.objects.filter(pk=record.pk).update(
            otp_code_hash=hash_otp("444444"), granted=True
        )
        with pytest.raises(DomainError, match="already granted"):
            ConsentService.verify_otp(
                consent_record_id=record.pk, otp_code="444444"
            )

    def test_raises_on_nonexistent_record(self, db):
        with pytest.raises(DomainError, match="not found"):
            ConsentService.verify_otp(consent_record_id=99999, otp_code="123456")

    def test_transitions_agreement_to_active_when_all_consented(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        ConsentRecord.objects.filter(pk=records[0].pk).update(
            otp_code_hash=hash_otp("555555")
        )
        ConsentRecord.objects.filter(pk=records[1].pk).update(
            otp_code_hash=hash_otp("666666")
        )
        ConsentService.verify_otp(
            consent_record_id=records[0].pk, otp_code="555555"
        )
        ConsentService.verify_otp(
            consent_record_id=records[1].pk, otp_code="666666"
        )
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.ACTIVE
        assert AuditLog.objects.filter(
            event_type="agreement.all_consented"
        ).exists()

    def test_does_not_transition_when_only_one_consented(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        ConsentRecord.objects.filter(pk=records[0].pk).update(
            otp_code_hash=hash_otp("777777")
        )
        ConsentService.verify_otp(
            consent_record_id=records[0].pk, otp_code="777777"
        )
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.PENDING_CONSENT


class TestConsentSelector:
    def test_list_consent_for_agreement(self, db):
        agreement = _agreement_with_parties()
        ConsentService.request_consent(agreement_id=agreement.pk)
        qs = ConsentSelector.list_consent_for_agreement(agreement_id=agreement.pk)
        assert qs.count() == 2

    def test_pending_consent_count(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        assert ConsentSelector.pending_consent_count(agreement_id=agreement.pk) == 2
        ConsentRecord.objects.filter(pk=records[0].pk).update(granted=True)
        assert ConsentSelector.pending_consent_count(agreement_id=agreement.pk) == 1

    def test_all_parties_consented_false(self, db):
        agreement = _agreement_with_parties()
        ConsentService.request_consent(agreement_id=agreement.pk)
        assert ConsentSelector.all_parties_consented(agreement_id=agreement.pk) is False

    def test_all_parties_consented_true(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        ConsentRecord.objects.filter(pk__in=[r.pk for r in records]).update(granted=True)
        assert ConsentSelector.all_parties_consented(agreement_id=agreement.pk) is True


class TestSyncConsent:
    def test_transitions_when_all_consented(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        ConsentRecord.objects.filter(pk__in=[r.pk for r in records]).update(granted=True)
        sync_consent(agreement_id=agreement.pk)
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.ACTIVE

    def test_does_nothing_when_not_all_consented(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        ConsentRecord.objects.filter(pk=records[0].pk).update(granted=True)
        sync_consent(agreement_id=agreement.pk)
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.PENDING_CONSENT

    def test_emits_audit_event(self, db):
        agreement = _agreement_with_parties()
        records = ConsentService.request_consent(agreement_id=agreement.pk)
        ConsentRecord.objects.filter(pk__in=[r.pk for r in records]).update(granted=True)
        sync_consent(agreement_id=agreement.pk)
        assert AuditLog.objects.filter(
            event_type="agreement.all_consented",
            entity_id=str(agreement.pk),
        ).exists()
