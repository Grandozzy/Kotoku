from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Account
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.services import AgreementService
from apps.audit.models import AuditLog
from apps.evidence.models import EvidenceItem
from apps.identity.models import IdentityRecord
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


class TestCreateDraft:
    def test_creates_agreement_in_draft_status(self, db):
        account = _account()
        agreement = AgreementService.create_draft(
            title="Sale of Bike",
            created_by=account,
            description="Test agreement",
            scenario_template="cash_sale",
        )
        assert agreement.pk is not None
        assert agreement.status == AgreementStatus.DRAFT
        assert agreement.title == "Sale of Bike"
        assert agreement.created_by == account

    def test_emits_audit_event(self, db):
        account = _account()
        agreement = AgreementService.create_draft(
            title="Test",
            created_by=account,
        )
        assert AuditLog.objects.filter(
            event_type="agreement.created",
            entity_id=str(agreement.pk),
        ).exists()


class TestAddParty:
    def test_adds_party_to_draft_agreement(self, db):
        account = _account("a@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        identity = _identity(account)
        party = AgreementService.add_party(
            agreement_id=agreement.pk,
            identity_id=identity.pk,
            role=Party.Role.BUYER,
            display_name="Alice",
        )
        assert party.agreement == agreement
        assert party.role == Party.Role.BUYER
        assert party.display_name == "Alice"

    def test_emits_audit_event(self, db):
        account = _account("b@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        identity = _identity(account)
        AgreementService.add_party(
            agreement_id=agreement.pk,
            identity_id=identity.pk,
            role=Party.Role.SELLER,
            display_name="Bob",
        )
        assert AuditLog.objects.filter(
            event_type="agreement.party_added",
            entity_id=str(agreement.pk),
        ).exists()

    def test_raises_when_not_draft(self, db):
        account = _account("c@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        identity = _identity(account)
        with pytest.raises(DomainError, match="draft"):
            AgreementService.add_party(
                agreement_id=agreement.pk,
                identity_id=identity.pk,
                role=Party.Role.BUYER,
                display_name="Carol",
            )


class TestRequestConsent:
    def test_transitions_to_pending_consent(self, db):
        account = _account("d@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        id1 = _identity(account, "ref-1")
        id2 = IdentityRecord.objects.create(
            account=account, reference="ref-2", verification_type="phone"
        )
        AgreementService.add_party(
            agreement_id=agreement.pk,
            identity_id=id1.pk,
            role=Party.Role.BUYER,
            display_name="A",
        )
        AgreementService.add_party(
            agreement_id=agreement.pk,
            identity_id=id2.pk,
            role=Party.Role.SELLER,
            display_name="B",
        )
        updated = AgreementService.request_consent(agreement_id=agreement.pk)
        assert updated.status == AgreementStatus.PENDING_CONSENT

    def test_raises_when_fewer_than_two_parties(self, db):
        account = _account("e@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        with pytest.raises(DomainError, match="2 parties"):
            AgreementService.request_consent(agreement_id=agreement.pk)


class TestSealAgreement:
    def test_transitions_to_sealed(self, db):
        account = _account("f@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        id1 = _identity(account)
        party = Party.objects.create(
            agreement=agreement,
            identity=id1,
            role=Party.Role.BUYER,
            display_name="A",
        )
        EvidenceItem.objects.create(
            agreement=agreement,
            uploaded_by=party,
            file_type=EvidenceItem.FileType.PHOTO,
            file_hash="abc123",
        )
        sealed = AgreementService.seal_agreement(agreement_id=agreement.pk)
        assert sealed.status == AgreementStatus.SEALED
        assert sealed.sealed_at is not None

    def test_raises_when_no_evidence(self, db):
        account = _account("g@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        with pytest.raises(DomainError, match="evidence"):
            AgreementService.seal_agreement(agreement_id=agreement.pk)


class TestCloseAgreement:
    def test_transitions_sealed_to_closed(self, db):
        account = _account("h@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        agreement.status = AgreementStatus.SEALED
        agreement.sealed_at = timezone.now()
        agreement.save()
        closed = AgreementService.close_agreement(agreement_id=agreement.pk)
        assert closed.status == AgreementStatus.CLOSED
        assert closed.closed_at is not None

    def test_raises_from_invalid_state(self, db):
        account = _account("i@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        with pytest.raises(DomainError):
            AgreementService.close_agreement(agreement_id=agreement.pk)


class TestReopenAgreement:
    def test_transitions_sealed_to_active_within_24h(self, db):
        account = _account("j@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        agreement.status = AgreementStatus.SEALED
        agreement.sealed_at = timezone.now() - timedelta(hours=12)
        agreement.save()
        reopened = AgreementService.reopen_agreement(agreement_id=agreement.pk)
        assert reopened.status == AgreementStatus.ACTIVE
        assert reopened.sealed_at is None

    def test_raises_after_24h(self, db):
        account = _account("k@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        agreement.status = AgreementStatus.SEALED
        agreement.sealed_at = timezone.now() - timedelta(hours=25)
        agreement.save()
        with pytest.raises(DomainError, match="24 hours"):
            AgreementService.reopen_agreement(agreement_id=agreement.pk)

    def test_emits_audit_event(self, db):
        account = _account("l@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        agreement.status = AgreementStatus.SEALED
        agreement.sealed_at = timezone.now() - timedelta(hours=1)
        agreement.save()
        AgreementService.reopen_agreement(agreement_id=agreement.pk)
        assert AuditLog.objects.filter(
            event_type="agreement.reopened",
            entity_id=str(agreement.pk),
        ).exists()
