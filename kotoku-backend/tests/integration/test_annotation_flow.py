"""Integration test: post-seal annotation flow.

Covers issue #10:
  sealed agreement → add annotation → GET annotations → verify ordering
  + non-party 403, non-sealed 400, multiple annotations ordered by created_at
"""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement, Annotation
from apps.agreements.services import AgreementService
from apps.consent.models import ConsentRecord
from apps.evidence.models import EvidenceItem
from apps.parties.models import Party
from apps.parties.services import PartyService
from apps.vault.services import VaultService

_ANNOTATIONS_PATH = "/api/agreements/{id}/annotations/"

_seq = 0


def _make_account(phone_suffix: str) -> tuple[Account, APIClient]:
    global _seq
    _seq += 1
    phone = f"+233A{phone_suffix}"
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(
        user=user, email=f"annot{_seq}@test.com", phone=phone,
    )
    token = AccessToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return account, client


def _sealed_agreement(account, seller_phone, buyer_phone):
    agr = AgreementService.create_draft(
        title="Annotation Test", created_by=account, scenario_template="used_vehicle_sale",
    )
    PartyService.set_parties(
        agreement_id=agr.pk,
        initiator_account=account,
        parties_data=[
            {"role": "seller", "full_name": "Kofi", "phone": seller_phone,
             "id_type": "ghana_card", "id_number": "GHA-AS"},
            {"role": "buyer", "full_name": "Ama", "phone": buyer_phone,
             "id_type": "ghana_card", "id_number": "GHA-AB"},
        ],
    )
    EvidenceItem.objects.create(
        agreement=agr,
        file_type=EvidenceItem.FileType.PHOTO,
        evidence_type="vehicle_photo_front",
        mime_type="image/jpeg",
        upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        storage_url="https://storage.kotoku/fake/annot.jpg",
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
class TestPostSealAnnotationFlow:
    def test_party_adds_annotation_and_get_returns_it(self):
        acct, client = _make_account("00010001")
        agr = _sealed_agreement(acct, acct.phone, "+233A00010002")
        party = agr.parties.first()

        resp = client.post(
            _ANNOTATIONS_PATH.format(id=agr.pk),
            data={"author_party_id": party.pk, "body": "Keys handed over on Monday."},
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()["data"]["annotation"]
        assert data["body"] == "Keys handed over on Monday."
        assert data["author_party_id"] == party.pk

        resp = client.get(_ANNOTATIONS_PATH.format(id=agr.pk))
        assert resp.status_code == 200
        annotations = resp.json()["data"]["annotations"]
        assert len(annotations) == 1
        assert annotations[0]["body"] == "Keys handed over on Monday."

    def test_non_party_cannot_add_annotation(self):
        acct, client = _make_account("00020001")
        agr = _sealed_agreement(acct, acct.phone, "+233A00020002")

        other_acct, _ = _make_account("00020003")
        other_agr = Agreement.objects.create(
            title="Other", created_by=other_acct, status=AgreementStatus.SEALED,
            sealed_at=timezone.now(), seal_hash="abc",
        )
        outsider = Party.objects.create(
            agreement=other_agr, role="seller",
            display_name="Outsider", phone="+233A00020004",
        )

        resp = client.post(
            _ANNOTATIONS_PATH.format(id=agr.pk),
            data={"author_party_id": outsider.pk, "body": "Should fail."},
            format="json",
        )
        assert resp.status_code == 403

    def test_cannot_annotate_non_sealed_agreement(self):
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
            _ANNOTATIONS_PATH.format(id=draft.pk),
            data={"author_party_id": party.pk, "body": "Should fail."},
            format="json",
        )
        assert resp.status_code == 400

    def test_multiple_annotations_ordered_by_created_at(self):
        acct, client = _make_account("00040001")
        agr = _sealed_agreement(acct, acct.phone, "+233A00040002")
        party = agr.parties.first()

        client.post(
            _ANNOTATIONS_PATH.format(id=agr.pk),
            data={"author_party_id": party.pk, "body": "First note."},
            format="json",
        )
        client.post(
            _ANNOTATIONS_PATH.format(id=agr.pk),
            data={"author_party_id": party.pk, "body": "Second note."},
            format="json",
        )
        client.post(
            _ANNOTATIONS_PATH.format(id=agr.pk),
            data={"author_party_id": party.pk, "body": "Third note."},
            format="json",
        )

        resp = client.get(_ANNOTATIONS_PATH.format(id=agr.pk))
        assert resp.status_code == 200
        annotations = resp.json()["data"]["annotations"]
        assert len(annotations) == 3
        assert annotations[0]["body"] == "First note."
        assert annotations[1]["body"] == "Second note."
        assert annotations[2]["body"] == "Third note."

    def test_other_user_cannot_see_annotations(self):
        acct, client = _make_account("00050001")
        agr = _sealed_agreement(acct, acct.phone, "+233A00050002")

        _, other_client = _make_account("00050003")
        resp = other_client.get(_ANNOTATIONS_PATH.format(id=agr.pk))
        assert resp.status_code == 404

    def test_author_can_update_annotation(self):
        acct, client = _make_account("00060001")
        agr = _sealed_agreement(acct, acct.phone, "+233A00060002")
        party = agr.parties.first()

        create_resp = client.post(
            _ANNOTATIONS_PATH.format(id=agr.pk),
            data={"author_party_id": party.pk, "body": "Original body."},
            format="json",
        )
        ann_id = create_resp.json()["data"]["annotation"]["id"]

        update_resp = client.put(
            f"/api/agreements/{agr.pk}/annotations/{ann_id}/?party_id={party.pk}",
            data={"body": "Updated body."},
            format="json",
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["data"]["annotation"]["body"] == "Updated body."

        get_resp = client.get(_ANNOTATIONS_PATH.format(id=agr.pk))
        assert get_resp.json()["data"]["annotations"][0]["body"] == "Updated body."

    def test_non_author_cannot_update_annotation(self):
        acct, client = _make_account("00070001")
        agr = _sealed_agreement(acct, acct.phone, "+233A00070002")
        author_party = agr.parties.first()
        other_party = agr.parties.last()

        create_resp = client.post(
            _ANNOTATIONS_PATH.format(id=agr.pk),
            data={"author_party_id": author_party.pk, "body": "Author only."},
            format="json",
        )
        ann_id = create_resp.json()["data"]["annotation"]["id"]

        update_resp = client.put(
            f"/api/agreements/{agr.pk}/annotations/{ann_id}/?party_id={other_party.pk}",
            data={"body": "Hijacked."},
            format="json",
        )
        assert update_resp.status_code == 400

    def test_author_can_delete_annotation(self):
        acct, client = _make_account("00080001")
        agr = _sealed_agreement(acct, acct.phone, "+233A00080002")
        party = agr.parties.first()

        create_resp = client.post(
            _ANNOTATIONS_PATH.format(id=agr.pk),
            data={"author_party_id": party.pk, "body": "To be deleted."},
            format="json",
        )
        ann_id = create_resp.json()["data"]["annotation"]["id"]

        delete_resp = client.delete(
            f"/api/agreements/{agr.pk}/annotations/{ann_id}/?party_id={party.pk}"
        )
        assert delete_resp.status_code == 200

        get_resp = client.get(_ANNOTATIONS_PATH.format(id=agr.pk))
        assert len(get_resp.json()["data"]["annotations"]) == 0

    def test_non_author_cannot_delete_annotation(self):
        acct, client = _make_account("00090001")
        agr = _sealed_agreement(acct, acct.phone, "+233A00090002")
        author_party = agr.parties.first()
        other_party = agr.parties.last()

        create_resp = client.post(
            _ANNOTATIONS_PATH.format(id=agr.pk),
            data={"author_party_id": author_party.pk, "body": "Not yours."},
            format="json",
        )
        ann_id = create_resp.json()["data"]["annotation"]["id"]

        delete_resp = client.delete(
            f"/api/agreements/{agr.pk}/annotations/{ann_id}/?party_id={other_party.pk}"
        )
        assert delete_resp.status_code == 400
