from unittest.mock import patch

import pytest

from apps.accounts.models import Account, User
from apps.agreements.services import AgreementService
from apps.audit.models import AuditLog
from apps.evidence.models import EvidenceItem
from apps.evidence.selectors import EvidenceSelector
from apps.evidence.services import EvidenceService
from apps.identity.models import IdentityRecord
from apps.parties.models import Party
from common.exceptions import DomainError

_seq = 0


def _account(email="evidence@test.com"):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=f"+233{_seq:09d}")
    return Account.objects.create(user=user, email=email, phone=user.phone)


def _identity(account, ref="ev-ref-1"):
    return IdentityRecord.objects.create(
        account=account, reference=ref, verification_type="ghana_card"
    )


def _setup_agreement_with_party():
    account = _account()
    agreement = AgreementService.create_draft(title="Evidence Test", created_by=account)
    identity = _identity(account)
    party = Party.objects.create(
        agreement=agreement, identity=identity, role=Party.Role.BUYER, display_name="Test"
    )
    return agreement, party


class TestUploadEvidence:
    @patch("apps.evidence.services.store_evidence")
    def test_creates_evidence_item(self, mock_store, db):
        mock_store.return_value = ("abc123hash", "https://bucket.s3.amazonaws.com/evidence/abc")
        agreement, party = _setup_agreement_with_party()

        item = EvidenceService.upload_evidence(
            agreement_id=agreement.pk,
            party_id=party.pk,
            file_type=EvidenceItem.FileType.PHOTO,
            file_data=b"photo bytes",
            original_name="receipt.jpg",
        )

        assert item.pk is not None
        assert item.agreement == agreement
        assert item.uploaded_by == party
        assert item.file_type == EvidenceItem.FileType.PHOTO
        assert item.file_hash == "abc123hash"
        assert item.storage_url == "https://bucket.s3.amazonaws.com/evidence/abc"
        assert item.original_name == "receipt.jpg"

    @patch("apps.evidence.services.store_evidence")
    def test_emits_audit_event(self, mock_store, db):
        mock_store.return_value = ("hash123", "https://example.com/file")
        agreement, party = _setup_agreement_with_party()

        item = EvidenceService.upload_evidence(
            agreement_id=agreement.pk,
            party_id=party.pk,
            file_type=EvidenceItem.FileType.DOCUMENT,
            file_data=b"doc",
            original_name="contract.pdf",
        )

        assert AuditLog.objects.filter(
            event_type="evidence.uploaded",
            entity_id=str(item.pk),
        ).exists()

    @patch("apps.evidence.services.store_evidence")
    def test_raises_when_party_not_in_agreement(self, mock_store, db):
        mock_store.return_value = ("hash", "https://example.com/file")
        agreement, party = _setup_agreement_with_party()
        other_account = _account("other@test.com")
        other_agreement = AgreementService.create_draft(title="Other", created_by=other_account)

        with pytest.raises(DomainError, match="does not belong"):
            EvidenceService.upload_evidence(
                agreement_id=other_agreement.pk,
                party_id=party.pk,
                file_type=EvidenceItem.FileType.PHOTO,
                file_data=b"data",
            )


class TestEvidenceSelectors:
    @patch("apps.evidence.services.store_evidence")
    def test_list_evidence_for_agreement(self, mock_store, db):
        mock_store.return_value = ("hash", "https://example.com/f")
        agreement, party = _setup_agreement_with_party()

        EvidenceService.upload_evidence(
            agreement_id=agreement.pk,
            party_id=party.pk,
            file_type=EvidenceItem.FileType.PHOTO,
            file_data=b"a",
        )
        EvidenceService.upload_evidence(
            agreement_id=agreement.pk,
            party_id=party.pk,
            file_type=EvidenceItem.FileType.DOCUMENT,
            file_data=b"b",
        )

        items = EvidenceSelector.list_evidence_for_agreement(agreement.pk)
        assert items.count() == 2

    @patch("apps.evidence.services.store_evidence")
    def test_list_excludes_other_agreements(self, mock_store, db):
        mock_store.return_value = ("hash", "https://example.com/f")
        agreement, party = _setup_agreement_with_party()
        other_account = _account("other2@test.com")
        other_agreement = AgreementService.create_draft(title="Other", created_by=other_account)
        other_identity = _identity(other_account, ref="other-ref")
        other_party = Party.objects.create(
            agreement=other_agreement,
            identity=other_identity,
            role=Party.Role.BUYER,
            display_name="Other",
        )

        EvidenceService.upload_evidence(
            agreement_id=agreement.pk,
            party_id=party.pk,
            file_type=EvidenceItem.FileType.PHOTO,
            file_data=b"a",
        )
        EvidenceService.upload_evidence(
            agreement_id=other_agreement.pk,
            party_id=other_party.pk,
            file_type=EvidenceItem.FileType.PHOTO,
            file_data=b"b",
        )

        items = EvidenceSelector.list_evidence_for_agreement(agreement.pk)
        assert items.count() == 1

    @patch("apps.evidence.services.store_evidence")
    def test_get_evidence_detail(self, mock_store, db):
        mock_store.return_value = ("hash", "https://example.com/f")
        agreement, party = _setup_agreement_with_party()

        item = EvidenceService.upload_evidence(
            agreement_id=agreement.pk,
            party_id=party.pk,
            file_type=EvidenceItem.FileType.SIGNATURE,
            file_data=b"sig",
            original_name="sig.png",
        )

        detail = EvidenceSelector.get_evidence_detail(item.pk)
        assert detail.original_name == "sig.png"
        assert detail.agreement == agreement
