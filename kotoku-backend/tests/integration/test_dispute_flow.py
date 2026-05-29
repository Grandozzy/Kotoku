"""Integration test: dispute on sealed agreement.

Covers issue #11:
  sealed agreement → party creates dispute → GET disputes returns it
  + non-party 403, non-sealed 400, correct fields
"""
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
from apps.consent.models import ConsentRecord
from apps.evidence.models import EvidenceItem
from apps.parties.models import Party
from apps.parties.services import PartyService
from apps.vault.services import VaultService

_DISPUTES_PATH = "/api/agreements/{id}/disputes/"

_seq = 0


def _make_account(phone_suffix: str) -> tuple[Account, APIClient]:
    global _seq
    _seq += 1
    phone = f"+233B{phone_suffix}"
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(
        user=user, email=f"dispute{_seq}@test.com", phone=phone,
    )
    token = AccessToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return account, client


def _sealed_agreement(account, seller_phone, buyer_phone):
    agr = AgreementService.create_draft(
        title="Dispute Test", created_by=account, scenario_template="used_vehicle_sale",
    )
    PartyService.set_parties(
        agreement_id=agr.pk,
        initiator_account=account,
        parties_data=[
            {"role": "seller", "full_name": "Kofi", "phone": seller_phone,
             "id_type": "ghana_card", "id_number": "GHA-DS"},
            {"role": "buyer", "full_name": "Ama", "phone": buyer_phone,
             "id_type": "ghana_card", "id_number": "GHA-DB"},
        ],
    )
    EvidenceItem.objects.create(
        agreement=agr,
        file_type=EvidenceItem.FileType.PHOTO,
        evidence_type="vehicle_photo_front",
        mime_type="image/jpeg",
        upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        storage_url="https://storage.kotoku/fake/dispute.jpg",
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


@pytest.mark.django_db
class TestDisputeOnSealedAgreement:
    def test_party_creates_dispute_and_get_returns_it(self):
        acct, client = _make_account("00010001")
        agr = _sealed_agreement(acct, acct.phone, "+233B00010002")
        party = agr.parties.first()

        resp = client.post(
            _DISPUTES_PATH.format(id=agr.pk),
            data={
                "raised_by_party_id": party.pk,
                "reason": "The agreed price was not honoured by the buyer.",
            },
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()["data"]["dispute"]
        assert data["status"] == "open"
        assert data["raised_by_party_id"] == party.pk
        assert data["reason"] == "The agreed price was not honoured by the buyer."
        assert data["id"] is not None

        resp = client.get(_DISPUTES_PATH.format(id=agr.pk))
        assert resp.status_code == 200
        disputes = resp.json()["data"]["disputes"]
        assert len(disputes) == 1
        assert disputes[0]["reason"] == "The agreed price was not honoured by the buyer."

    def test_non_party_cannot_create_dispute(self):
        acct, client = _make_account("00020001")
        agr = _sealed_agreement(acct, acct.phone, "+233B00020002")

        other_acct, _ = _make_account("00020003")
        other_agr = Agreement.objects.create(
            title="Other", created_by=other_acct, status=AgreementStatus.SEALED,
            sealed_at=timezone.now(), seal_hash="xyz",
        )
        outsider = Party.objects.create(
            agreement=other_agr, role="buyer",
            display_name="Stranger", phone="+233B00020004",
        )

        resp = client.post(
            _DISPUTES_PATH.format(id=agr.pk),
            data={"raised_by_party_id": outsider.pk, "reason": "I am not a party here at all."},
            format="json",
        )
        assert resp.status_code == 403

    def test_cannot_dispute_non_sealed_agreement(self):
        acct, client = _make_account("00030001")
        draft = Agreement.objects.create(
            title="Draft", created_by=acct, status=AgreementStatus.DRAFT,
        )
        Party.objects.create(
            agreement=draft, role="seller",
            display_name="Kofi", phone=acct.phone,
        )
        party = draft.parties.first()

        resp = client.post(
            _DISPUTES_PATH.format(id=draft.pk),
            data={"raised_by_party_id": party.pk, "reason": "Dispute on a draft agreement."},
            format="json",
        )
        assert resp.status_code == 400

    def test_dispute_has_correct_fields(self):
        acct, client = _make_account("00040001")
        buyer_acct, buyer_client = _make_account("00040002")
        agr = _sealed_agreement(acct, acct.phone, buyer_acct.phone)
        buyer = agr.parties.get(role="buyer")

        resp = buyer_client.post(
            _DISPUTES_PATH.format(id=agr.pk),
            data={
                "raised_by_party_id": buyer.pk,
                "reason": "Vehicle condition does not match description in agreement.",
            },
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()["data"]["dispute"]
        assert data["raised_by_party_id"] == buyer.pk
        assert data["raised_by_display_name"] == "Ama"
        assert data["status"] == "open"
        assert data["resolution"] in ("", None)
        assert data["resolved_at"] is None
        assert data["created_at"] is not None

    def test_other_user_cannot_see_disputes(self):
        acct, client = _make_account("00050001")
        agr = _sealed_agreement(acct, acct.phone, "+233B00050002")

        _, other_client = _make_account("00050003")
        resp = other_client.get(_DISPUTES_PATH.format(id=agr.pk))
        assert resp.status_code == 404

    def test_case_pack_returns_all_required_fields(self):
        from apps.disputes.models import Dispute

        acct, client = _make_account("00060001")
        agr = _sealed_agreement(acct, acct.phone, "+233B00060002")
        party = agr.parties.first()
        dispute = Dispute.objects.create(
            agreement=agr,
            raised_by=party,
            reason="Vehicle condition does not match agreed specification.",
        )

        resp = client.post(f"/api/agreements/{agr.pk}/disputes/{dispute.pk}/case_pack/")
        assert resp.status_code == 200
        pack = resp.json()["data"]["case_pack"]
        assert pack["dispute"]["reason"] == "Vehicle condition does not match agreed specification."
        assert pack["agreement"]["seal_hash"] is not None
        assert pack["agreement"]["scenario"] == "used_vehicle_sale"
        assert len(pack["parties"]) == 2
        assert pack["dispute"]["status"] == "open"
        assert pack["dispute"]["resolved_at"] is None

    def test_case_pack_inaccessible_to_other_user(self):
        from apps.disputes.models import Dispute

        acct, client = _make_account("00070001")
        agr = _sealed_agreement(acct, acct.phone, "+233B00070002")
        party = agr.parties.first()
        dispute = Dispute.objects.create(
            agreement=agr, raised_by=party, reason="Test reason for access check."
        )

        _, other_client = _make_account("00070003")
        resp = other_client.post(f"/api/agreements/{agr.pk}/disputes/{dispute.pk}/case_pack/")
        assert resp.status_code == 404

    def test_root_disputes_list_returns_only_own_agreements(self):
        from apps.disputes.models import Dispute

        acct, client = _make_account("00080001")
        other_acct, _ = _make_account("00080002")
        agr = _sealed_agreement(acct, acct.phone, "+233B00080003")
        other_agr = _sealed_agreement(other_acct, other_acct.phone, "+233B00080004")
        Dispute.objects.create(
            agreement=agr, raised_by=agr.parties.first(), reason="My own dispute."
        )
        Dispute.objects.create(
            agreement=other_agr, raised_by=other_agr.parties.first(), reason="Not my dispute."
        )

        resp = client.get("/api/disputes/")
        assert resp.status_code == 200
        disputes = resp.json()["data"]["disputes"]
        assert len(disputes) == 1
        assert disputes[0]["reason"] == "My own dispute."

    def test_root_dispute_detail_returns_correct_dispute(self):
        from apps.disputes.models import Dispute

        acct, client = _make_account("00090001")
        agr = _sealed_agreement(acct, acct.phone, "+233B00090002")
        dispute = Dispute.objects.create(
            agreement=agr, raised_by=agr.parties.first(), reason="Detail lookup test."
        )

        resp = client.get(f"/api/disputes/{dispute.pk}/")
        assert resp.status_code == 200
        data = resp.json()["data"]["dispute"]
        assert data["id"] == dispute.pk
        assert data["reason"] == "Detail lookup test."
        assert data["agreement_id"] == agr.pk
