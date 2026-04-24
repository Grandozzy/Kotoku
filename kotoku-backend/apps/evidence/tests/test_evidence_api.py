"""Integration tests for the presigned upload flow.

S3 calls are patched at the S3StorageClient boundary so tests never hit
real object storage.
"""
from unittest.mock import patch

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.evidence.models import EvidenceItem
from apps.parties.services import PartyService

_UPLOAD_URL_PATH = "/api/agreements/{id}/evidence/upload-url/"
_EVIDENCE_PATH = "/api/agreements/{id}/evidence/"

_FAKE_PRESIGNED_URL = "https://storage.kotoku/bucket/key?X-Amz-Signature=fake"
_FAKE_HEADERS = {"Content-Type": "image/jpeg"}
_FAKE_STORAGE_URL = "https://storage.kotoku/bucket/agreements/1/evidence/photo.jpg"

_seq = 0


def _make_client(phone):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(user=user, email=f"ev{_seq}@api.com", phone=phone)
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client, account


def _agreement(account, status=AgreementStatus.DRAFT):
    a = Agreement.objects.create(title="Ev Test", created_by=account)
    if status != AgreementStatus.DRAFT:
        a.status = status
        a.save()
    return a


def _set_parties(agreement, initiator_phone):
    from apps.accounts.models import Account
    acct = Account.objects.get(phone=initiator_phone)
    PartyService.set_parties(
        agreement_id=agreement.pk,
        initiator_account=acct,
        parties_data=[
            {"role": "seller", "full_name": "Kofi", "phone": initiator_phone,
             "id_type": "ghana_card", "id_number": "GHA-S"},
            {"role": "buyer", "full_name": "Ama", "phone": "+233200000070",
             "id_type": "ghana_card", "id_number": "GHA-B"},
        ],
    )


@patch(
    "apps.evidence.services.S3StorageClient.generate_presigned_upload_url",
    return_value=(_FAKE_PRESIGNED_URL, _FAKE_HEADERS),
)
@pytest.mark.django_db
class TestUploadUrlApi:
    def test_returns_201_with_url_and_key(self, mock_presign):
        client, acct = _make_client("+233501400001")
        agreement = _agreement(acct)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {"evidence_type": "vehicle_photo_front", "mime_type": "image/jpeg", "size_bytes": 524288},
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["upload_url"] == _FAKE_PRESIGNED_URL
        assert "file_key" in data
        assert data["headers"] == _FAKE_HEADERS
        assert "evidence_id" in data

    def test_creates_pending_evidence_item(self, mock_presign):
        client, acct = _make_client("+233501400002")
        agreement = _agreement(acct)
        client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {"evidence_type": "vehicle_photo_front", "mime_type": "image/jpeg", "size_bytes": 100},
            format="json",
        )
        assert EvidenceItem.objects.filter(
            agreement=agreement,
            upload_status=EvidenceItem.UploadStatus.PENDING,
        ).exists()

    def test_file_key_contains_evidence_type(self, mock_presign):
        client, acct = _make_client("+233501400003")
        agreement = _agreement(acct)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {"evidence_type": "seller_id_photo", "mime_type": "image/png", "size_bytes": 200},
            format="json",
        )
        assert "seller_id_photo" in resp.json()["data"]["file_key"]

    def test_sealed_agreement_returns_400(self, mock_presign):
        client, acct = _make_client("+233501400004")
        agreement = _agreement(acct, status=AgreementStatus.SEALED)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {"evidence_type": "vehicle_photo_front", "mime_type": "image/jpeg", "size_bytes": 100},
            format="json",
        )
        assert resp.status_code == 400

    def test_unsupported_mime_type_returns_400(self, mock_presign):
        client, acct = _make_client("+233501400005")
        agreement = _agreement(acct)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {"evidence_type": "doc", "mime_type": "text/html", "size_bytes": 100},
            format="json",
        )
        assert resp.status_code == 400

    def test_invalid_evidence_type_format_returns_400(self, mock_presign):
        client, acct = _make_client("+233501400006")
        agreement = _agreement(acct)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {"evidence_type": "Bad Name!", "mime_type": "image/jpeg", "size_bytes": 100},
            format="json",
        )
        assert resp.status_code == 400

    def test_zero_size_returns_400(self, mock_presign):
        client, acct = _make_client("+233501400007")
        agreement = _agreement(acct)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {"evidence_type": "vehicle_photo_front", "mime_type": "image/jpeg", "size_bytes": 0},
            format="json",
        )
        assert resp.status_code == 400

    def test_other_users_agreement_returns_404(self, mock_presign):
        client, acct = _make_client("+233501400008")
        _, other_acct = _make_client("+233501400009")
        agreement = _agreement(other_acct)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {"evidence_type": "vehicle_photo_front", "mime_type": "image/jpeg", "size_bytes": 100},
            format="json",
        )
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, mock_presign):
        _, acct = _make_client("+233501400010")
        agreement = _agreement(acct)
        resp = APIClient().post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {"evidence_type": "vehicle_photo_front", "mime_type": "image/jpeg", "size_bytes": 100},
            format="json",
        )
        assert resp.status_code == 401

    def test_links_uploaded_by_when_party_exists(self, mock_presign):
        client, acct = _make_client("+233501400011")
        agreement = _agreement(acct)
        _set_parties(agreement, acct.phone)
        client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {"evidence_type": "seller_id_photo", "mime_type": "image/jpeg", "size_bytes": 500},
            format="json",
        )
        item = EvidenceItem.objects.get(agreement=agreement, evidence_type="seller_id_photo")
        assert item.uploaded_by is not None
        assert item.uploaded_by.phone == acct.phone


@patch(
    "apps.evidence.services.S3StorageClient.build_object_url",
    return_value=_FAKE_STORAGE_URL,
)
@patch(
    "apps.evidence.services.S3StorageClient.generate_presigned_upload_url",
    return_value=(_FAKE_PRESIGNED_URL, _FAKE_HEADERS),
)
@pytest.mark.django_db
class TestConfirmUploadApi:
    def _request_url(self, client, agreement_id, evidence_type="vehicle_photo_front",
                     mime_type="image/jpeg"):
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement_id),
            {"evidence_type": evidence_type, "mime_type": mime_type, "size_bytes": 500},
            format="json",
        )
        return resp.json()["data"]["file_key"]

    def test_confirm_returns_201(self, mock_presign, mock_url):
        client, acct = _make_client("+233501500001")
        agreement = _agreement(acct)
        file_key = self._request_url(client, agreement.pk)
        resp = client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {"file_key": file_key, "evidence_type": "vehicle_photo_front", "mime_type": "image/jpeg"},
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()["data"]["evidence"]
        assert data["upload_status"] == "confirmed"
        assert data["storage_url"] == _FAKE_STORAGE_URL

    def test_confirmed_item_appears_in_list(self, mock_presign, mock_url):
        client, acct = _make_client("+233501500002")
        agreement = _agreement(acct)
        file_key = self._request_url(client, agreement.pk)
        client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {"file_key": file_key, "evidence_type": "vehicle_photo_front", "mime_type": "image/jpeg"},
            format="json",
        )
        resp = client.get(_EVIDENCE_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        items = resp.json()["data"]["evidence"]
        assert len(items) == 1
        assert items[0]["upload_status"] == "confirmed"

    def test_pending_items_excluded_from_list(self, mock_presign, mock_url):
        client, acct = _make_client("+233501500003")
        agreement = _agreement(acct)
        self._request_url(client, agreement.pk)  # creates pending item, no confirm
        resp = client.get(_EVIDENCE_PATH.format(id=agreement.pk))
        assert resp.json()["data"]["evidence"] == []

    def test_wrong_evidence_type_returns_400(self, mock_presign, mock_url):
        client, acct = _make_client("+233501500004")
        agreement = _agreement(acct)
        file_key = self._request_url(client, agreement.pk, evidence_type="vehicle_photo_front")
        resp = client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {"file_key": file_key, "evidence_type": "seller_id_photo", "mime_type": "image/jpeg"},
            format="json",
        )
        assert resp.status_code == 400

    def test_wrong_mime_type_returns_400(self, mock_presign, mock_url):
        client, acct = _make_client("+233501500005")
        agreement = _agreement(acct)
        file_key = self._request_url(client, agreement.pk, mime_type="image/jpeg")
        resp = client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {"file_key": file_key, "evidence_type": "vehicle_photo_front", "mime_type": "image/png"},
            format="json",
        )
        assert resp.status_code == 400

    def test_unknown_file_key_returns_400(self, mock_presign, mock_url):
        client, acct = _make_client("+233501500006")
        agreement = _agreement(acct)
        resp = client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {"file_key": "agreements/99/evidence/ghost.jpg",
             "evidence_type": "vehicle_photo_front", "mime_type": "image/jpeg"},
            format="json",
        )
        assert resp.status_code == 400

    def test_cannot_confirm_twice(self, mock_presign, mock_url):
        client, acct = _make_client("+233501500007")
        agreement = _agreement(acct)
        file_key = self._request_url(client, agreement.pk)
        payload = {"file_key": file_key, "evidence_type": "vehicle_photo_front", "mime_type": "image/jpeg"}
        client.post(_EVIDENCE_PATH.format(id=agreement.pk), payload, format="json")
        # Second confirm — item is now CONFIRMED, not PENDING → 400
        resp = client.post(_EVIDENCE_PATH.format(id=agreement.pk), payload, format="json")
        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self, mock_presign, mock_url):
        _, acct = _make_client("+233501500008")
        agreement = _agreement(acct)
        resp = APIClient().post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {"file_key": "k", "evidence_type": "x_y", "mime_type": "image/jpeg"},
            format="json",
        )
        assert resp.status_code == 401


@patch(
    "apps.evidence.services.S3StorageClient.build_object_url",
    return_value=_FAKE_STORAGE_URL,
)
@patch(
    "apps.evidence.services.S3StorageClient.generate_presigned_upload_url",
    return_value=(_FAKE_PRESIGNED_URL, _FAKE_HEADERS),
)
@pytest.mark.django_db
class TestEvidenceListApi:
    def test_list_empty_agreement(self, mock_presign, mock_url):
        client, acct = _make_client("+233501600001")
        agreement = _agreement(acct)
        resp = client.get(_EVIDENCE_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        assert resp.json()["data"]["evidence"] == []

    def test_list_other_users_agreement_returns_404(self, mock_presign, mock_url):
        client, acct = _make_client("+233501600002")
        _, other_acct = _make_client("+233501600003")
        agreement = _agreement(other_acct)
        resp = client.get(_EVIDENCE_PATH.format(id=agreement.pk))
        assert resp.status_code == 404
