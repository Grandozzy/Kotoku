"""Sprint 6 integration tests.

Covers:
  - Bilateral reopen flow (service + API)
  - Post-seal annotations (service + API)
  - Disputes (service + API)
  - Archival Celery task
  - Logging middleware (request ID propagation)
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Account, User
from apps.agreements.annotation_services import AnnotationSelector, AnnotationService
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement, Annotation
from apps.agreements.services import AgreementService
from apps.consent.models import ConsentRecord
from apps.consent.services import ConsentService, generate_otp, hash_otp
from apps.disputes.models import Dispute
from apps.disputes.selectors import DisputeSelector
from apps.disputes.services import DisputeService
from apps.evidence.models import EvidenceItem
from apps.parties.models import Party
from apps.parties.services import PartyService
from apps.vault.models import VaultEntry
from apps.vault.services import VaultService
from common.exceptions import DomainError

_seq = 0


# ── Fixtures ──────────────────────────────────────────────────────────────── #


def _make_account(phone_suffix: str) -> tuple[Account, APIClient]:
    global _seq
    _seq += 1
    phone = f"+2337{phone_suffix}"
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(user=user, email=f"u{_seq}@test.com", phone=phone)
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return account, client


def _sealed_agreement(account: Account, initiator_phone: str, second_phone: str) -> Agreement:
    """Create a fully sealed agreement with vault entry."""
    agreement = Agreement.objects.create(
        title="Test Sealed",
        created_by=account,
        scenario_template="used_vehicle_sale",
    )
    PartyService.set_parties(
        agreement_id=agreement.pk,
        initiator_account=account,
        parties_data=[
            {
                "role": "seller",
                "full_name": "Kofi Atta",
                "phone": initiator_phone,
                "id_type": "ghana_card",
                "id_number": "GHA-S-001",
            },
            {
                "role": "buyer",
                "full_name": "Ama Owusu",
                "phone": second_phone,
                "id_type": "ghana_card",
                "id_number": "GHA-B-001",
            },
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
    for p in agreement.parties.all():
        ConsentRecord.objects.create(
            agreement=agreement,
            party=p,
            otp_code_hash="fakehash",
            channel=ConsentRecord.Channel.SMS,
            granted=True,
            granted_at=timezone.now(),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
    agreement = AgreementService.seal_agreement(agreement_id=agreement.pk)
    VaultService.create_for_agreement(agreement_id=agreement.pk)
    return agreement


# ── Bilateral reopen — service layer ─────────────────────────────────────── #


@pytest.mark.django_db
class TestRequestReopen:
    def test_transitions_to_reopen_requested(self):
        acct, _ = _make_account("00100001")
        agreement = _sealed_agreement(acct, "+233700100001", "+233700100002")
        with patch("infrastructure.sms.gateway.SmsGateway.send", return_value=True):
            updated = AgreementService.request_reopen(agreement_id=agreement.pk)
        assert updated.status == AgreementStatus.REOPEN_REQUESTED

    def test_requires_sealed_status(self):
        acct, _ = _make_account("00100003")
        agreement = Agreement.objects.create(
            title="Draft", created_by=acct, status=AgreementStatus.DRAFT
        )
        with pytest.raises(DomainError, match="sealed"):
            AgreementService.request_reopen(agreement_id=agreement.pk)

    def test_complete_bilateral_reopen_transitions_to_active(self):
        acct, _ = _make_account("00100004")
        agreement = _sealed_agreement(acct, "+233700100004", "+233700100005")
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        result = AgreementService.complete_bilateral_reopen(agreement_id=agreement.pk)
        assert result.status == AgreementStatus.ACTIVE
        assert result.sealed_at is None
        assert result.seal_hash == ""

    def test_cancel_reopen_returns_to_sealed(self):
        acct, _ = _make_account("00100006")
        agreement = _sealed_agreement(acct, "+233700100006", "+233700100007")
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        result = AgreementService.cancel_reopen(agreement_id=agreement.pk)
        assert result.status == AgreementStatus.SEALED


@pytest.mark.django_db
class TestReopenOtpFlow:
    def test_request_reopen_otp_creates_records_for_all_parties(self):
        acct, _ = _make_account("00200001")
        agreement = _sealed_agreement(acct, "+233700200001", "+233700200002")
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        with patch("apps.consent.services.send_sms_message.delay", return_value=None):
            records = ConsentService.request_reopen_otp(agreement_id=agreement.pk)
        assert len(records) == 2
        assert all(r.purpose == ConsentRecord.Purpose.REOPEN for r in records)
        assert all(not r.granted for r in records)

    def test_confirm_reopen_by_phone_grants_record(self):
        acct, _ = _make_account("00200003")
        agreement = _sealed_agreement(acct, "+233700200003", "+233700200004")
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        otp = generate_otp()
        party = agreement.parties.first()
        ConsentRecord.objects.create(
            agreement=agreement,
            party=party,
            purpose=ConsentRecord.Purpose.REOPEN,
            otp_code_hash=hash_otp(otp),
            channel=ConsentRecord.Channel.SMS,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        record = ConsentService.confirm_reopen_by_phone(
            agreement_id=agreement.pk,
            party_phone=party.phone,
            otp_code=otp,
        )
        assert record.granted is True

    def test_all_parties_confirm_triggers_bilateral_complete(self):
        acct, _ = _make_account("00200005")
        seller_phone = "+233700200005"
        buyer_phone = "+233700200006"
        agreement = _sealed_agreement(acct, seller_phone, buyer_phone)
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()

        seller_otp = generate_otp()
        buyer_otp = generate_otp()
        parties = list(agreement.parties.order_by("role"))
        for party in parties:
            otp = seller_otp if party.phone == seller_phone else buyer_otp
            ConsentRecord.objects.create(
                agreement=agreement,
                party=party,
                purpose=ConsentRecord.Purpose.REOPEN,
                otp_code_hash=hash_otp(otp),
                channel=ConsentRecord.Channel.SMS,
                expires_at=timezone.now() + timedelta(minutes=10),
            )

        # Confirm seller
        ConsentService.confirm_reopen_by_phone(
            agreement_id=agreement.pk,
            party_phone=seller_phone,
            otp_code=seller_otp,
        )
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.REOPEN_REQUESTED  # not yet

        # Confirm buyer — triggers bilateral completion
        ConsentService.confirm_reopen_by_phone(
            agreement_id=agreement.pk,
            party_phone=buyer_phone,
            otp_code=buyer_otp,
        )
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.ACTIVE


# ── Bilateral reopen — API layer ──────────────────────────────────────────── #

_REOPEN_REQUEST_PATH = "/api/agreements/{id}/reopen-request/"
_REOPEN_OTP_REQUEST_PATH = "/api/agreements/{id}/reopen-consent/request-otp/"
_REOPEN_OTP_CONFIRM_PATH = "/api/agreements/{id}/reopen-consent/confirm/"


@pytest.mark.django_db
class TestReopenAPI:
    def test_reopen_request_returns_200_and_transitions(self):
        acct, client = _make_account("00300001")
        agreement = _sealed_agreement(acct, "+233700300001", "+233700300002")
        with patch("infrastructure.sms.gateway.SmsGateway.send", return_value=True):
            resp = client.post(_REOPEN_REQUEST_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        assert resp.json()["data"]["agreement"]["status"] == AgreementStatus.REOPEN_REQUESTED

    def test_reopen_request_requires_sealed_status(self):
        acct, client = _make_account("00300003")
        agreement = Agreement.objects.create(
            title="Draft", created_by=acct, status=AgreementStatus.DRAFT
        )
        resp = client.post(_REOPEN_REQUEST_PATH.format(id=agreement.pk))
        assert resp.status_code == 400

    def test_reopen_request_404_for_other_users_agreement(self):
        _, client = _make_account("00300005")
        other_acct, _ = _make_account("00300006")
        agreement = _sealed_agreement(other_acct, "+233700300006", "+233700300007")
        resp = client.post(_REOPEN_REQUEST_PATH.format(id=agreement.pk))
        assert resp.status_code == 404

    def test_reopen_otp_request_reissues_otps(self):
        acct, client = _make_account("00300008")
        agreement = _sealed_agreement(acct, "+233700300008", "+233700300009")
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        with patch("infrastructure.sms.gateway.SmsGateway.send", return_value=True):
            resp = client.post(_REOPEN_OTP_REQUEST_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        assert (
            ConsentRecord.objects.filter(
                agreement=agreement, purpose=ConsentRecord.Purpose.REOPEN
            ).count()
            == 2
        )

    def test_reopen_otp_confirm_returns_agreement_status(self):
        acct, client = _make_account("00300010")
        seller_phone = "+233700300010"
        buyer_phone = "+233700300011"
        agreement = _sealed_agreement(acct, seller_phone, buyer_phone)
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        otp = generate_otp()
        party = agreement.parties.get(phone=seller_phone)
        ConsentRecord.objects.create(
            agreement=agreement,
            party=party,
            purpose=ConsentRecord.Purpose.REOPEN,
            otp_code_hash=hash_otp(otp),
            channel=ConsentRecord.Channel.SMS,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        resp = client.post(
            _REOPEN_OTP_CONFIRM_PATH.format(id=agreement.pk),
            data={"phone": seller_phone, "otp_code": otp},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["granted"] is True

    def test_reopen_otp_confirm_cannot_use_another_party_phone(self):
        acct, client = _make_account("00300014")
        seller_phone = "+233700300014"
        buyer_phone = "+233700300015"
        agreement = _sealed_agreement(acct, seller_phone, buyer_phone)
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        otp = generate_otp()
        buyer_party = agreement.parties.get(phone=buyer_phone)
        ConsentRecord.objects.create(
            agreement=agreement,
            party=buyer_party,
            purpose=ConsentRecord.Purpose.REOPEN,
            otp_code_hash=hash_otp(otp),
            channel=ConsentRecord.Channel.SMS,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        resp = client.post(
            _REOPEN_OTP_CONFIRM_PATH.format(id=agreement.pk),
            data={"phone": buyer_phone, "otp_code": otp},
            format="json",
        )
        assert resp.status_code == 403
        assert not ConsentRecord.objects.get(
            agreement=agreement,
            party=buyer_party,
            purpose=ConsentRecord.Purpose.REOPEN,
        ).granted

    def test_reopen_otp_confirm_requires_phone_and_code(self):
        acct, client = _make_account("00300012")
        agreement = _sealed_agreement(acct, "+233700300012", "+233700300013")
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        resp = client.post(
            _REOPEN_OTP_CONFIRM_PATH.format(id=agreement.pk),
            data={},
            format="json",
        )
        assert resp.status_code == 400

    def test_reopen_endpoints_require_authentication(self):
        unauthenticated = APIClient()
        for path in [_REOPEN_REQUEST_PATH, _REOPEN_OTP_REQUEST_PATH, _REOPEN_OTP_CONFIRM_PATH]:
            resp = unauthenticated.post(path.format(id=1))
            assert resp.status_code == 401


# ── Annotations — service layer ───────────────────────────────────────────── #


@pytest.mark.django_db
class TestAnnotationService:
    def test_create_annotation_on_sealed_agreement(self):
        acct, _ = _make_account("00400001")
        agreement = _sealed_agreement(acct, "+233700400001", "+233700400002")
        party = agreement.parties.first()
        annotation = AnnotationService.create(
            agreement_id=agreement.pk,
            author_party_id=party.pk,
            body="Seller confirmed keys handed over.",
        )
        assert annotation.pk is not None
        assert annotation.agreement == agreement
        assert annotation.author_party == party

    def test_cannot_annotate_draft(self):
        acct, _ = _make_account("00400003")
        agreement = Agreement.objects.create(
            title="Draft", created_by=acct, status=AgreementStatus.DRAFT
        )
        Party.objects.create(
            agreement=agreement, role="seller", display_name="Kofi", phone="+233700400003"
        )
        party = agreement.parties.first()
        with pytest.raises(DomainError, match="sealed"):
            AnnotationService.create(
                agreement_id=agreement.pk,
                author_party_id=party.pk,
                body="This should fail.",
            )

    def test_author_must_be_party_on_agreement(self):
        acct, _ = _make_account("00400004")
        agreement = _sealed_agreement(acct, "+233700400004", "+233700400005")
        other_acct, _ = _make_account("00400006")
        other_agreement = Agreement.objects.create(
            title="Other",
            created_by=other_acct,
            status=AgreementStatus.SEALED,
            sealed_at=timezone.now(),
            seal_hash="abc123",
        )
        outsider_party = Party.objects.create(
            agreement=other_agreement, role="seller", display_name="Outsider", phone="+233700400006"
        )
        with pytest.raises(DomainError, match="party"):
            AnnotationService.create(
                agreement_id=agreement.pk,
                author_party_id=outsider_party.pk,
                body="Should fail.",
            )

    def test_list_annotations_returns_in_order(self):
        acct, _ = _make_account("00400007")
        agreement = _sealed_agreement(acct, "+233700400007", "+233700400008")
        party = agreement.parties.first()
        AnnotationService.create(agreement_id=agreement.pk, author_party_id=party.pk, body="First")
        AnnotationService.create(agreement_id=agreement.pk, author_party_id=party.pk, body="Second")
        annotations = list(AnnotationSelector.list_for_agreement(agreement_id=agreement.pk))
        assert len(annotations) == 2
        assert annotations[0].body == "First"
        assert annotations[1].body == "Second"


# ── Annotations — API layer ───────────────────────────────────────────────── #

_ANNOTATIONS_PATH = "/api/agreements/{id}/annotations/"


@pytest.mark.django_db
class TestAnnotationAPI:
    def test_post_creates_annotation_and_returns_201(self):
        acct, client = _make_account("00500001")
        agreement = _sealed_agreement(acct, "+233700500001", "+233700500002")
        party = agreement.parties.first()
        resp = client.post(
            _ANNOTATIONS_PATH.format(id=agreement.pk),
            data={"author_party_id": party.pk, "body": "Noted by seller."},
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()["data"]["annotation"]
        assert data["body"] == "Noted by seller."
        assert data["author_party_id"] == party.pk

    def test_get_lists_annotations(self):
        acct, client = _make_account("00500003")
        agreement = _sealed_agreement(acct, "+233700500003", "+233700500004")
        party = agreement.parties.first()
        Annotation.objects.create(agreement=agreement, author_party=party, body="Note A")
        Annotation.objects.create(agreement=agreement, author_party=party, body="Note B")
        resp = client.get(_ANNOTATIONS_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        assert len(resp.json()["data"]["annotations"]) == 2

    def test_cannot_annotate_draft_via_api(self):
        acct, client = _make_account("00500005")
        agreement = Agreement.objects.create(
            title="Draft", created_by=acct, status=AgreementStatus.DRAFT
        )
        Party.objects.create(
            agreement=agreement, role="seller", display_name="Kofi", phone="+233700500005"
        )
        party = agreement.parties.first()
        resp = client.post(
            _ANNOTATIONS_PATH.format(id=agreement.pk),
            data={"author_party_id": party.pk, "body": "Should fail."},
            format="json",
        )
        assert resp.status_code == 400

    def test_annotation_404_for_other_users_agreement(self):
        _, client = _make_account("00500006")
        other_acct, _ = _make_account("00500007")
        agreement = _sealed_agreement(other_acct, "+233700500007", "+233700500008")
        resp = client.get(_ANNOTATIONS_PATH.format(id=agreement.pk))
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self):
        unauthenticated = APIClient()
        assert unauthenticated.get(_ANNOTATIONS_PATH.format(id=1)).status_code == 401
        assert unauthenticated.post(_ANNOTATIONS_PATH.format(id=1)).status_code == 401

    def test_participant_can_list_and_create_annotations(self):
        owner_acct, owner_client = _make_account("00500008")
        participant_acct, participant_client = _make_account("00500009")
        agreement = _sealed_agreement(
            owner_acct,
            owner_acct.phone,
            participant_acct.phone,
        )
        participant_party = agreement.parties.get(phone=participant_acct.phone)

        create_resp = participant_client.post(
            _ANNOTATIONS_PATH.format(id=agreement.pk),
            data={"author_party_id": participant_party.pk, "body": "Buyer note."},
            format="json",
        )
        assert create_resp.status_code == 201

        list_resp = participant_client.get(_ANNOTATIONS_PATH.format(id=agreement.pk))
        assert list_resp.status_code == 200
        assert len(list_resp.json()["data"]["annotations"]) == 1

    def test_participant_cannot_impersonate_annotation_author(self):
        owner_acct, owner_client = _make_account("00500010")
        participant_acct, participant_client = _make_account("00500011")
        agreement = _sealed_agreement(
            owner_acct,
            owner_acct.phone,
            participant_acct.phone,
        )
        owner_party = agreement.parties.get(phone=owner_acct.phone)

        resp = participant_client.post(
            _ANNOTATIONS_PATH.format(id=agreement.pk),
            data={"author_party_id": owner_party.pk, "body": "Forged note."},
            format="json",
        )
        assert resp.status_code == 403


# ── Disputes — service layer ──────────────────────────────────────────────── #


@pytest.mark.django_db
class TestDisputeService:
    def test_open_dispute_on_sealed_agreement(self):
        acct, _ = _make_account("00600001")
        agreement = _sealed_agreement(acct, "+233700600001", "+233700600002")
        party = agreement.parties.first()
        dispute = DisputeService.open_dispute(
            agreement_id=agreement.pk,
            raised_by_party_id=party.pk,
            reason="The agreed price was not honoured.",
        )
        assert dispute.pk is not None
        assert dispute.status == Dispute.Status.OPEN
        assert dispute.raised_by == party

    def test_cannot_dispute_draft(self):
        acct, _ = _make_account("00600003")
        agreement = Agreement.objects.create(
            title="Draft", created_by=acct, status=AgreementStatus.DRAFT
        )
        Party.objects.create(
            agreement=agreement, role="seller", display_name="Kofi", phone="+233700600003"
        )
        party = agreement.parties.first()
        with pytest.raises(DomainError, match="sealed"):
            DisputeService.open_dispute(
                agreement_id=agreement.pk,
                raised_by_party_id=party.pk,
                reason="Draft dispute.",
            )

    def test_reason_required(self):
        acct, _ = _make_account("00600004")
        agreement = _sealed_agreement(acct, "+233700600004", "+233700600005")
        party = agreement.parties.first()
        with pytest.raises(DomainError, match="reason"):
            DisputeService.open_dispute(
                agreement_id=agreement.pk,
                raised_by_party_id=party.pk,
                reason="   ",
            )

    def test_raising_party_must_be_on_agreement(self):
        acct, _ = _make_account("00600006")
        agreement = _sealed_agreement(acct, "+233700600006", "+233700600007")
        other_acct, _ = _make_account("00600008")
        other_agreement = Agreement.objects.create(
            title="Other",
            created_by=other_acct,
            status=AgreementStatus.SEALED,
            sealed_at=timezone.now(),
            seal_hash="xyz",
        )
        outsider = Party.objects.create(
            agreement=other_agreement,
            role="buyer",
            display_name="Stranger",
            phone="+233700600008",
        )
        with pytest.raises(DomainError, match="party"):
            DisputeService.open_dispute(
                agreement_id=agreement.pk,
                raised_by_party_id=outsider.pk,
                reason="I am not a party here.",
            )

    def test_list_disputes(self):
        acct, _ = _make_account("00600009")
        agreement = _sealed_agreement(acct, "+233700600009", "+233700600010")
        party = agreement.parties.first()
        DisputeService.open_dispute(
            agreement_id=agreement.pk,
            raised_by_party_id=party.pk,
            reason="First complaint about the deal.",
        )
        disputes = list(DisputeSelector.list_for_agreement(agreement_id=agreement.pk))
        assert len(disputes) == 1
        assert disputes[0].raised_by == party


# ── Disputes — API layer ──────────────────────────────────────────────────── #

_DISPUTES_PATH = "/api/agreements/{id}/disputes/"


@pytest.mark.django_db
class TestDisputeAPI:
    def test_post_opens_dispute_and_returns_201(self):
        acct, client = _make_account("00700001")
        agreement = _sealed_agreement(acct, "+233700700001", "+233700700002")
        party = agreement.parties.first()
        resp = client.post(
            _DISPUTES_PATH.format(id=agreement.pk),
            data={"raised_by_party_id": party.pk, "reason": "Price was not honoured as agreed."},
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()["data"]["dispute"]
        assert data["status"] == Dispute.Status.OPEN
        assert data["raised_by_party_id"] == party.pk

    def test_get_lists_disputes(self):
        acct, client = _make_account("00700003")
        agreement = _sealed_agreement(acct, "+233700700003", "+233700700004")
        party = agreement.parties.first()
        Dispute.objects.create(agreement=agreement, raised_by=party, reason="Test dispute.")
        resp = client.get(_DISPUTES_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        assert len(resp.json()["data"]["disputes"]) == 1

    def test_dispute_requires_reason_min_length(self):
        acct, client = _make_account("00700005")
        agreement = _sealed_agreement(acct, "+233700700005", "+233700700006")
        party = agreement.parties.first()
        resp = client.post(
            _DISPUTES_PATH.format(id=agreement.pk),
            data={"raised_by_party_id": party.pk, "reason": "Short"},
            format="json",
        )
        assert resp.status_code == 400

    def test_dispute_404_for_other_users_agreement(self):
        _, client = _make_account("00700007")
        other_acct, _ = _make_account("00700008")
        agreement = _sealed_agreement(other_acct, "+233700700008", "+233700700009")
        resp = client.get(_DISPUTES_PATH.format(id=agreement.pk))
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self):
        unauthenticated = APIClient()
        assert unauthenticated.get(_DISPUTES_PATH.format(id=1)).status_code == 401
        assert unauthenticated.post(_DISPUTES_PATH.format(id=1)).status_code == 401

    def test_participant_can_list_and_open_disputes(self):
        owner_acct, owner_client = _make_account("00700010")
        participant_acct, participant_client = _make_account("00700011")
        agreement = _sealed_agreement(
            owner_acct,
            owner_acct.phone,
            participant_acct.phone,
        )
        participant_party = agreement.parties.get(phone=participant_acct.phone)

        create_resp = participant_client.post(
            _DISPUTES_PATH.format(id=agreement.pk),
            data={
                "raised_by_party_id": participant_party.pk,
                "reason": "Buyer says the delivered item differed from the sealed record.",
            },
            format="json",
        )
        assert create_resp.status_code == 201

        list_resp = participant_client.get(_DISPUTES_PATH.format(id=agreement.pk))
        assert list_resp.status_code == 200
        assert len(list_resp.json()["data"]["disputes"]) == 1


# ── Archival task ─────────────────────────────────────────────────────────── #


@pytest.mark.django_db
class TestArchivalTask:
    def test_archives_entries_past_retention(self):
        from apps.vault.tasks import archive_expired_vault_entries  # noqa: PLC0415

        acct, _ = _make_account("00800001")
        agreement = _sealed_agreement(acct, "+233700800001", "+233700800002")
        entry = VaultEntry.objects.get(agreement=agreement)
        entry.retain_until = timezone.now() - timedelta(days=1)
        entry.save()

        result = archive_expired_vault_entries()
        entry.refresh_from_db()
        assert entry.archived is True
        assert result["archived"] == 1

    def test_does_not_archive_entries_within_retention(self):
        from apps.vault.tasks import archive_expired_vault_entries  # noqa: PLC0415

        acct, _ = _make_account("00800003")
        agreement = _sealed_agreement(acct, "+233700800003", "+233700800004")
        entry = VaultEntry.objects.get(agreement=agreement)
        assert entry.retain_until > timezone.now()

        result = archive_expired_vault_entries()
        entry.refresh_from_db()
        assert entry.archived is False
        assert result["archived"] == 0

    def test_already_archived_entries_are_skipped(self):
        from apps.vault.tasks import archive_expired_vault_entries  # noqa: PLC0415

        acct, _ = _make_account("00800005")
        agreement = _sealed_agreement(acct, "+233700800005", "+233700800006")
        entry = VaultEntry.objects.get(agreement=agreement)
        entry.retain_until = timezone.now() - timedelta(days=1)
        entry.archived = True
        entry.save()

        result = archive_expired_vault_entries()
        assert result["archived"] == 0


# ── Logging middleware ────────────────────────────────────────────────────── #


@pytest.mark.django_db
class TestRequestIdMiddleware:
    def test_response_contains_x_request_id_header(self):
        acct, client = _make_account("00900001")
        resp = client.get("/api/health/")
        assert "X-Request-ID" in resp

    def test_client_supplied_request_id_is_echoed(self):
        acct, client = _make_account("00900002")
        client.credentials(
            HTTP_AUTHORIZATION=client._credentials["HTTP_AUTHORIZATION"],
            HTTP_X_REQUEST_ID="my-trace-id-abc123",
        )
        resp = client.get("/api/health/")
        assert resp["X-Request-ID"] == "my-trace-id-abc123"
