from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import AgreementRevision
from apps.agreements.services import AgreementService
from apps.evidence.models import EvidenceItem
from apps.identity.models import IdentityRecord
from apps.parties.models import Party
from common.exceptions import DomainError
from tests.utils import stamp_all_parties_verified

_seq = 0


def _account(email="test@test.com"):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=f"+233{_seq:09d}")
    return Account.objects.create(user=user, email=email, phone=user.phone)


def _identity(account, ref="ref-1"):
    return IdentityRecord.objects.create(
        account=account,
        reference=ref,
        verification_type="ghana_card",
    )


def _make_sealed_agreement():
    account = _account("sealed_edit@test.com")
    agreement = AgreementService.create_draft(
        title="Test Agreement",
        created_by=account,
        description="Original description",
        scenario_template="used_vehicle_sale",
    )
    id1 = _identity(account, "ref-a")
    id2 = IdentityRecord.objects.create(
        account=account, reference="ref-b", verification_type="ghana_card"
    )
    party_a = Party.objects.create(
        agreement=agreement, identity=id1, role="buyer", display_name="Buyer",
        id_type="ghana_card", id_number="GHA-111111111-1",
    )
    Party.objects.create(
        agreement=agreement, identity=id2, role="seller", display_name="Seller",
        id_type="ghana_card", id_number="GHA-222222222-2",
    )
    stamp_all_parties_verified(agreement)
    EvidenceItem.objects.create(
        agreement=agreement,
        uploaded_by=party_a,
        file_type=EvidenceItem.FileType.PHOTO,
        file_hash="abc123",
        evidence_type="vehicle_photo_front",
        upload_status=EvidenceItem.UploadStatus.CONFIRMED,
    )
    agreement.status = AgreementStatus.SEALED
    agreement.sealed_at = timezone.now()
    agreement.seal_hash = "a" * 64
    agreement.save()
    return agreement


class TestUpdateActive:
    def test_update_active_updates_fields(self, db):
        agreement = _make_sealed_agreement()
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        updated = AgreementService.update_active(
            agreement_id=agreement.pk,
            title="Updated Title",
            description="Updated description",
        )
        assert updated.title == "Updated Title"
        assert updated.description == "Updated description"
        assert updated.status == AgreementStatus.ACTIVE

    def test_update_active_raises_if_not_active(self, db):
        account = _account("notactive@test.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        with pytest.raises(DomainError, match="active"):
            AgreementService.update_active(
                agreement_id=agreement.pk, title="Nope"
            )

    def test_update_active_emits_audit_event(self, db):
        agreement = _make_sealed_agreement()
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        AgreementService.update_active(
            agreement_id=agreement.pk, title="Updated"
        )
        from apps.audit.models import AuditLog

        assert AuditLog.objects.filter(
            event_type="agreement.updated_active",
            entity_id=str(agreement.pk),
        ).exists()


class TestAgreementRevision:
    def test_revision_created_on_bilateral_reopen(self, db):
        agreement = _make_sealed_agreement()
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        original_sealed_at = agreement.sealed_at
        original_seal_hash = agreement.seal_hash

        reopened = AgreementService.complete_bilateral_reopen(
            agreement_id=agreement.pk
        )

        assert reopened.status == AgreementStatus.ACTIVE
        assert reopened.sealed_at is None
        assert reopened.seal_hash == ""

        revision = AgreementRevision.objects.get(agreement=agreement)
        assert revision.revision_number == 1
        assert revision.seal_hash == original_seal_hash
        assert revision.sealed_at == original_sealed_at
        assert "parties" in revision.snapshot
        assert "evidence" in revision.snapshot

    def test_multiple_revisions_increment(self, db):
        agreement = _make_sealed_agreement()

        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        AgreementService.complete_bilateral_reopen(agreement_id=agreement.pk)

        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.ACTIVE

        AgreementService.update_active(
            agreement_id=agreement.pk, title="Updated Title"
        )

        agreement.refresh_from_db()
        from apps.consent.services import ConsentService

        records = ConsentService.request_otp(agreement_id=agreement.pk)
        assert len(records) == 2

        for record in records:
            record.granted = True
            record.granted_at = timezone.now()
            record.save(update_fields=["granted", "granted_at"])

        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.PENDING_CONSENT

        from apps.agreements.domain.policies import can_seal

        if can_seal(agreement):
            AgreementService.seal_agreement(agreement_id=agreement.pk)
        else:
            agreement.status = AgreementStatus.SEALED
            agreement.sealed_at = timezone.now()
            agreement.seal_hash = "b" * 64
            agreement.save()

        agreement.refresh_from_db()
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        AgreementService.complete_bilateral_reopen(agreement_id=agreement.pk)

        revisions = AgreementRevision.objects.filter(agreement=agreement).order_by(
            "revision_number"
        )
        assert revisions.count() == 2
        assert revisions[0].revision_number == 1
        assert revisions[1].revision_number == 2


class TestResealConsentFlow:
    @patch("apps.consent.services.send_sms_message.delay", return_value=None)
    def test_active_can_transition_to_pending_consent(self, mock_delay, db):
        agreement = _make_sealed_agreement()
        agreement.status = AgreementStatus.ACTIVE
        agreement.sealed_at = None
        agreement.seal_hash = ""
        agreement.save()
        from apps.agreements.domain.policies import can_request_consent

        assert can_request_consent(agreement) is True

    @patch("apps.consent.services.send_sms_message.delay", return_value=None)
    def test_request_consent_from_active_goes_to_pending(self, mock_delay, db):
        from apps.consent.services import ConsentService

        account = _account("reseal_otp@test.com")
        agreement = AgreementService.create_draft(
            title="Re-Seal Test", created_by=account
        )
        id1 = _identity(account, "ref-r1")
        id2 = IdentityRecord.objects.create(
            account=account, reference="ref-r2", verification_type="phone"
        )
        Party.objects.create(
            agreement=agreement, identity=id1, role="buyer", display_name="Buyer"
        )
        Party.objects.create(
            agreement=agreement, identity=id2, role="seller", display_name="Seller"
        )
        agreement.status = AgreementStatus.ACTIVE
        agreement.sealed_at = None
        agreement.seal_hash = ""
        agreement.save()
        records = ConsentService.request_otp(agreement_id=agreement.pk)
        assert len(records) == 2
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.PENDING_CONSENT


class TestResealSealFlow:
    @patch("apps.consent.services.send_sms_message.delay", return_value=None)
    def test_reseal_seal_after_consent(self, mock_delay, db):
        agreement = _make_sealed_agreement()

        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        AgreementService.complete_bilateral_reopen(agreement_id=agreement.pk)

        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.ACTIVE

        AgreementService.update_active(
            agreement_id=agreement.pk, title="Updated Title"
        )

        agreement.refresh_from_db()
        from apps.consent.services import ConsentService

        records = ConsentService.request_otp(agreement_id=agreement.pk)
        assert len(records) == 2

        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.PENDING_CONSENT

        for record in records:
            record.granted = True
            record.granted_at = timezone.now()
            record.save(update_fields=["granted", "granted_at"])

        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.PENDING_CONSENT

        sealed = AgreementService.seal_agreement(agreement_id=agreement.pk)
        assert sealed.status == AgreementStatus.SEALED
        assert sealed.sealed_at is not None
        assert sealed.seal_hash != ""
