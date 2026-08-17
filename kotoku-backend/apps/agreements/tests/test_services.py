from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.services import AgreementService
from apps.audit.models import AuditLog
from apps.evidence.models import EvidenceItem
from apps.identity.models import IdentityRecord, PartyIdentityVerification
from apps.parties.models import Party
from common.exceptions import DomainError

_seq = 0


def _account(email="user@test.com"):
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

    def test_raises_on_duplicate_party_role(self, db):
        account = _account("dup@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        identity = _identity(account)
        AgreementService.add_party(
            agreement_id=agreement.pk,
            identity_id=identity.pk,
            role=Party.Role.BUYER,
            display_name="First",
        )
        with pytest.raises(IntegrityError):
            AgreementService.add_party(
                agreement_id=agreement.pk,
                identity_id=identity.pk,
                role=Party.Role.BUYER,
                display_name="Duplicate",
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
    def _verified_identity_bundle(self, agreement, party, *, include_selfie: bool = True):
        EvidenceItem.objects.create(
            agreement=agreement,
            uploaded_by=party,
            file_type=EvidenceItem.FileType.PHOTO,
            evidence_type=f"{party.role}_ghana_card_front",
            mime_type="image/jpeg",
            upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        )
        EvidenceItem.objects.create(
            agreement=agreement,
            uploaded_by=party,
            file_type=EvidenceItem.FileType.PHOTO,
            evidence_type=f"{party.role}_ghana_card_back",
            mime_type="image/jpeg",
            upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        )
        if include_selfie:
            EvidenceItem.objects.create(
                agreement=agreement,
                uploaded_by=party,
                file_type=EvidenceItem.FileType.PHOTO,
                evidence_type=f"{party.role}_selfie",
                mime_type="image/jpeg",
                upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            )
        PartyIdentityVerification.objects.create(
            party=party,
            status=PartyIdentityVerification.Status.VERIFIED,
            entered_pin=party.id_number or "",
            entered_full_name=party.display_name,
            ocr_pin=party.id_number or "",
            ocr_full_name=party.display_name.upper(),
            detail="Verified",
            face_match_score=99.0 if include_selfie else None,
        )

    def test_transitions_to_sealed(self, db):
        account = _account("f@t.com")
        agreement = AgreementService.create_draft(
            title="T", created_by=account, scenario_template="used_vehicle_sale",
        )
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        id1 = _identity(account)
        party = Party.objects.create(
            agreement=agreement,
            identity=id1,
            role=Party.Role.BUYER,
            display_name="A",
            phone=account.phone,
            id_type="ghana_card",
            id_number="GHA-111111111-1",
        )
        id2 = _identity(account, "ref-seller-transitions")
        seller = Party.objects.create(
            agreement=agreement,
            identity=id2,
            role=Party.Role.SELLER,
            display_name="S",
            phone="+233500000001",
            id_type="ghana_card",
            id_number="GHA-999999999-9",
        )
        for vp in ("vehicle_photo_front", "vehicle_photo_side", "vehicle_photo_rear"):
            EvidenceItem.objects.create(
                agreement=agreement, uploaded_by=party,
                file_type=EvidenceItem.FileType.PHOTO, evidence_type=vp,
                mime_type="image/jpeg", upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            )
        self._verified_identity_bundle(agreement, party)
        self._verified_identity_bundle(agreement, seller)
        sealed = AgreementService.seal_agreement(agreement_id=agreement.pk)
        assert sealed.status == AgreementStatus.SEALED
        assert sealed.sealed_at is not None

    def test_seal_hash_stored_on_seal(self, db):
        account = _account("seal_hash1@t.com")
        agreement = AgreementService.create_draft(
            title="Hash Test", created_by=account, scenario_template="used_vehicle_sale",
        )
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        id1 = _identity(account)
        buyer = Party.objects.create(
            agreement=agreement,
            identity=id1,
            role=Party.Role.BUYER,
            display_name="B",
            id_type="ghana_card",
            id_number="GHA-001000000-1",
        )
        id2 = _identity(account, "ref-seller-hash")
        seller = Party.objects.create(
            agreement=agreement,
            identity=id2,
            role=Party.Role.SELLER,
            display_name="S",
            id_type="ghana_card",
            id_number="GHA-002000000-2",
        )
        for vp in ("vehicle_photo_front", "vehicle_photo_side", "vehicle_photo_rear"):
            EvidenceItem.objects.create(
                agreement=agreement, uploaded_by=buyer,
                file_type=EvidenceItem.FileType.PHOTO, evidence_type=vp,
                upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            )
        self._verified_identity_bundle(agreement, buyer)
        self._verified_identity_bundle(agreement, seller)
        sealed = AgreementService.seal_agreement(agreement_id=agreement.pk)
        assert sealed.seal_hash != ""
        assert len(sealed.seal_hash) == 64  # SHA-256 hex digest

    def test_seal_fails_when_identity_not_verified(self, db):
        account = _account("seal_identity@t.com")
        agreement = AgreementService.create_draft(title="Identity Required", created_by=account)
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        identity = _identity(account, "seal-id-check")
        party = Party.objects.create(
            agreement=agreement,
            identity=identity,
            role=Party.Role.BUYER,
            display_name="Buyer",
            phone=account.phone,
            id_type="ghana_card",
            id_number="GHA-222222222-2",
        )
        EvidenceItem.objects.create(
            agreement=agreement,
            uploaded_by=party,
            file_type=EvidenceItem.FileType.PHOTO,
            evidence_type="vehicle_photo_front",
            mime_type="image/jpeg",
            upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        )
        with pytest.raises(DomainError, match="validation failed"):
            AgreementService.seal_agreement(agreement_id=agreement.pk)

    def test_seal_hash_is_deterministic(self, db):
        """Same agreement data always produces the same hash."""
        from apps.agreements.services import _compute_seal_hash

        account = _account("seal_hash2@t.com")
        agreement = AgreementService.create_draft(title="Deterministic", created_by=account)
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        id1 = _identity(account)
        party = Party.objects.create(
            agreement=agreement,
            identity=id1,
            role=Party.Role.BUYER,
            display_name="C",
            id_type="passport",
            id_number="P999",
        )
        EvidenceItem.objects.create(
            agreement=agreement,
            uploaded_by=party,
            file_type=EvidenceItem.FileType.PHOTO,
            file_hash="xyz789",
        )
        hash1 = _compute_seal_hash(agreement)
        hash2 = _compute_seal_hash(agreement)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_raises_when_no_evidence(self, db):
        account = _account("g@t.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        with pytest.raises(DomainError, match="evidence"):
            AgreementService.seal_agreement(agreement_id=agreement.pk)

    def test_sends_receipt_sms_to_all_parties_on_seal(
        self, db, monkeypatch, django_capture_on_commit_callbacks
    ):
        account = _account("seal_receipt@test.com")
        agreement = AgreementService.create_draft(
            title="Receipt", created_by=account, scenario_template="used_vehicle_sale",
        )
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        identity = _identity(account)
        seller = Party.objects.create(
            agreement=agreement,
            identity=identity,
            role=Party.Role.SELLER,
            display_name="Seller",
            phone=account.phone,
            id_type="ghana_card",
            id_number="GHA-111111111-1",
        )
        buyer_identity = IdentityRecord.objects.create(
            account=account,
            reference="ref-buyer",
            verification_type="phone",
        )
        buyer = Party.objects.create(
            agreement=agreement,
            identity=buyer_identity,
            role=Party.Role.BUYER,
            display_name="Buyer",
            phone="+233244000111",
            id_type="ghana_card",
            id_number="GHA-222222222-2",
        )
        self._verified_identity_bundle(agreement, seller)
        self._verified_identity_bundle(agreement, buyer)
        for vp in ("vehicle_photo_front", "vehicle_photo_side", "vehicle_photo_rear"):
            EvidenceItem.objects.create(
                agreement=agreement, uploaded_by=seller,
                file_type=EvidenceItem.FileType.PHOTO, evidence_type=vp,
                file_hash=f"receipt-vp-{vp}", upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            )
        EvidenceItem.objects.create(
            agreement=agreement,
            uploaded_by=seller,
            file_type=EvidenceItem.FileType.DOCUMENT,
            evidence_type="seller_id_photo",
            file_hash="receipt-2",
            upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        )

        push_calls: list[tuple[str, str, dict]] = []
        sms_calls: list[tuple[str, str]] = []

        def _fake_push(phone, event_type, payload):
            push_calls.append((phone, event_type, payload))

        def _fake_sms(*, to, body):
            sms_calls.append((to, body))

        monkeypatch.setattr("apps.agreements.services.send_to_user", _fake_push)
        monkeypatch.setattr("apps.agreements.services.send_sms_message.delay", _fake_sms)

        with django_capture_on_commit_callbacks(execute=True):
            sealed = AgreementService.seal_agreement(agreement_id=agreement.pk)

        assert sealed.status == AgreementStatus.SEALED
        assert len(push_calls) == 2
        assert len(sms_calls) == 2
        sms_numbers = {to for to, _body in sms_calls}
        assert sms_numbers == {account.phone, "+233244000111"}
        for _to, body in sms_calls:
            assert f"Agreement #{agreement.pk}" in body
            assert "vehicle_photo_front" in body
            assert "seller_id_photo" in body
            assert "/vault/receipt/" in body
            assert "download PDF, or raise a dispute" in body

    def test_receipt_sms_summarizes_long_evidence_lists(
        self, db, monkeypatch, django_capture_on_commit_callbacks
    ):
        account = _account("seal_receipt_long@test.com")
        agreement = AgreementService.create_draft(
            title="Receipt", created_by=account, scenario_template="used_vehicle_sale",
        )
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        identity = _identity(account)
        party = Party.objects.create(
            agreement=agreement,
            identity=identity,
            role=Party.Role.SELLER,
            display_name="Seller",
            phone=account.phone,
            id_type="ghana_card",
            id_number="GHA-333333333-3",
        )
        buyer = Party.objects.create(
            agreement=agreement,
            role=Party.Role.BUYER,
            display_name="Buyer",
            phone="+233244000222",
            id_type="ghana_card",
            id_number="GHA-444444444-4",
        )
        self._verified_identity_bundle(agreement, party)
        self._verified_identity_bundle(agreement, buyer)
        evidence_types = [
            "vehicle_photo_front",
            "vehicle_photo_side",
            "vehicle_photo_back",
            "seller_id_photo",
            "buyer_id_photo",
            "condition_photo",
        ]
        for idx, evidence_type in enumerate(evidence_types, start=1):
            EvidenceItem.objects.create(
                agreement=agreement,
                uploaded_by=party,
                file_type=EvidenceItem.FileType.PHOTO,
                evidence_type=evidence_type,
                file_hash=f"receipt-long-{idx}",
                upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            )

        sms_calls: list[tuple[str, str]] = []

        def _fake_sms(*, to, body):
            sms_calls.append((to, body))

        monkeypatch.setattr(
            "apps.agreements.services.send_to_user",
            lambda *_args, **_kwargs: None,
        )
        monkeypatch.setattr("apps.agreements.services.send_sms_message.delay", _fake_sms)

        with django_capture_on_commit_callbacks(execute=True):
            AgreementService.seal_agreement(agreement_id=agreement.pk)

        assert len(sms_calls) == 2
        for _to, body in sms_calls:
            assert "vehicle_photo_front" in body
            assert "vehicle_photo_side" not in body
            assert "+1 more" in body
            assert "/vault/receipt/" in body

    def test_seal_notifications_wait_for_transaction_commit(self, db, monkeypatch):
        account = _account("seal_commit@test.com")
        agreement = AgreementService.create_draft(
            title="Commit Guard", created_by=account, scenario_template="used_vehicle_sale",
        )
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        identity = _identity(account)
        party = Party.objects.create(
            agreement=agreement,
            identity=identity,
            role=Party.Role.SELLER,
            display_name="Seller",
            phone=account.phone,
            id_type="ghana_card",
            id_number="GHA-555555555-5",
        )
        id2 = _identity(account, "ref-buyer-commit")
        buyer = Party.objects.create(
            agreement=agreement,
            identity=id2,
            role=Party.Role.BUYER,
            display_name="Buyer",
            phone="+233500000002",
            id_type="ghana_card",
            id_number="GHA-666666666-6",
        )
        self._verified_identity_bundle(agreement, party)
        self._verified_identity_bundle(agreement, buyer)
        for vp in ("vehicle_photo_front", "vehicle_photo_side", "vehicle_photo_rear"):
            EvidenceItem.objects.create(
                agreement=agreement, uploaded_by=party,
                file_type=EvidenceItem.FileType.PHOTO, evidence_type=vp,
                upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            )

        push_calls: list[tuple] = []
        sms_calls: list[tuple] = []

        def _raise_on_seal_event(**kwargs):
            if kwargs["event_type"] == "agreement.sealed":
                raise RuntimeError("audit failed after seal write")

        monkeypatch.setattr(
            "apps.agreements.services.send_to_user",
            lambda *args, **kwargs: push_calls.append((args, kwargs)),
        )
        monkeypatch.setattr(
            "apps.agreements.services.send_sms_message.delay",
            lambda *args, **kwargs: sms_calls.append((args, kwargs)),
        )
        monkeypatch.setattr(
            "apps.agreements.services.AuditService.record_event",
            _raise_on_seal_event,
        )

        with pytest.raises(RuntimeError, match="audit failed"):
            AgreementService.seal_agreement(agreement_id=agreement.pk)

        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.ACTIVE
        assert agreement.sealed_at is None
        assert push_calls == []
        assert sms_calls == []

    def test_blocks_seal_when_billing_check_errors(self, db, monkeypatch):
        account = _account("seal_billing_block@test.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        identity = _identity(account)
        party = Party.objects.create(
            agreement=agreement,
            identity=identity,
            role=Party.Role.BUYER,
            display_name="Billing Party",
        )
        EvidenceItem.objects.create(
            agreement=agreement,
            uploaded_by=party,
            file_type=EvidenceItem.FileType.PHOTO,
            file_hash="billing-block",
        )

        def _boom(_account):
            raise RuntimeError("billing unavailable")

        monkeypatch.setattr(
            "apps.billing.services.BillingService.check_seal_allowed",
            _boom,
        )

        with pytest.raises(
            DomainError,
            match="Billing enforcement is temporarily unavailable",
        ):
            AgreementService.seal_agreement(agreement_id=agreement.pk)

        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.ACTIVE
        assert agreement.sealed_at is None

    @override_settings(BILLING_ENFORCEMENT_FAIL_OPEN=True)
    def test_fail_open_override_allows_seal_when_billing_check_errors(self, db, monkeypatch):
        account = _account("seal_billing_override@test.com")
        agreement = AgreementService.create_draft(
            title="T", created_by=account, scenario_template="used_vehicle_sale",
        )
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        identity = _identity(account)
        party = Party.objects.create(
            agreement=agreement,
            identity=identity,
            role=Party.Role.BUYER,
            display_name="Billing Override Party",
            id_type="ghana_card",
            id_number="GHA-777777777-7",
        )
        id2 = _identity(account, "ref-seller-override")
        seller = Party.objects.create(
            agreement=agreement,
            identity=id2,
            role=Party.Role.SELLER,
            display_name="Seller Override",
            id_type="ghana_card",
            id_number="GHA-888888888-8",
        )
        self._verified_identity_bundle(agreement, party)
        self._verified_identity_bundle(agreement, seller)
        for vp in ("vehicle_photo_front", "vehicle_photo_side", "vehicle_photo_rear"):
            EvidenceItem.objects.create(
                agreement=agreement, uploaded_by=party,
                file_type=EvidenceItem.FileType.PHOTO, evidence_type=vp,
                upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            )

        def _boom(_account):
            raise RuntimeError("billing unavailable")

        monkeypatch.setattr(
            "apps.billing.services.BillingService.check_seal_allowed",
            _boom,
        )

        sealed = AgreementService.seal_agreement(agreement_id=agreement.pk)
        assert sealed.status == AgreementStatus.SEALED
        assert sealed.sealed_at is not None


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


class TestUpdateDraft:
    def test_update_draft_updates_fields(self, db):
        account = _account("update@test.com")
        agreement = AgreementService.create_draft(
            title="Original", created_by=account, description="old desc"
        )
        updated = AgreementService.update_draft(
            agreement_id=agreement.pk,
            title="Updated",
            description="new desc",
        )
        assert updated.title == "Updated"
        assert updated.description == "new desc"

    def test_update_draft_raises_if_not_draft(self, db):
        account = _account("notdraft@test.com")
        agreement = AgreementService.create_draft(title="Test", created_by=account)
        identity = _identity(account)
        Party.objects.create(agreement=agreement, identity=identity, role="buyer", display_name="A")
        id2 = IdentityRecord.objects.create(
            account=account, reference="ref-b", verification_type="phone"
        )
        Party.objects.create(agreement=agreement, identity=id2, role="seller", display_name="B")
        AgreementService.request_consent(agreement_id=agreement.pk)
        with pytest.raises(DomainError):
            AgreementService.update_draft(agreement_id=agreement.pk, title="Nope")

    def test_update_draft_emits_audit_event(self, db):
        account = _account("audit_update@test.com")
        agreement = AgreementService.create_draft(title="Test", created_by=account)
        AgreementService.update_draft(agreement_id=agreement.pk, title="New Title")
        assert AuditLog.objects.filter(
            event_type="agreement.updated",
            entity_id=str(agreement.pk),
        ).exists()


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
