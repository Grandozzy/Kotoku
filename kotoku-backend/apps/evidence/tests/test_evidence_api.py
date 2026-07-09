"""Integration tests for the presigned upload flow.

S3 calls are patched at the S3StorageClient boundary so tests never hit
real object storage.
"""
from unittest.mock import patch

import pytest
from botocore.exceptions import EndpointConnectionError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.evidence.models import EvidenceItem
from apps.parties.services import PartyService

_UPLOAD_URL_PATH = "/api/agreements/{id}/evidence/upload-url/"
_EVIDENCE_PATH = "/api/agreements/{id}/evidence/"

_FAKE_PRESIGNED_URL = "https://storage.kotoku/bucket/key?X-Amz-Signature=fake"
_FAKE_VIEW_URL = "https://storage.kotoku/bucket/key?response-content-disposition=inline"
_FAKE_CHECKSUM = "a" * 64
_FAKE_HEADERS = {"Content-Type": "image/jpeg"}
_FAKE_STORAGE_URL = "https://storage.kotoku/bucket/agreements/1/evidence/photo.jpg"
# In production, x-amz-meta-sha256 is not included in the presigned PUT headers,
# so S3 stores no sha256 metadata and the checksum check is skipped in confirm_upload.
# The head mock deliberately omits metadata to reflect this production behavior.
_FAKE_HEAD = {
    "content_length": 500,
    "content_type": "image/jpeg",
    "etag": "abc123etag",
    "metadata": {},
}

_seq = 0


def _pin(index: int) -> str:
    return f"GHA-{index:09d}-{index % 10}"


def _make_client(phone):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(user=user, email=f"ev{_seq}@api.com", phone=phone)
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
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
             "id_type": "ghana_card", "id_number": _pin(111111111)},
            {"role": "buyer", "full_name": "Ama", "phone": "+233200000070",
             "id_type": "ghana_card", "id_number": _pin(222222222)},
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
            {
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "size_bytes": 524288,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
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
            {
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "size_bytes": 100,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert EvidenceItem.objects.filter(
            agreement=agreement,
            upload_status=EvidenceItem.UploadStatus.PENDING,
        ).exists()

    def test_file_key_contains_evidence_type(self, mock_presign):
        client, acct = _make_client("+233501400003")
        agreement = _agreement(acct)
        _set_parties(agreement, "+233501400003")
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {
                "evidence_type": "seller_ghana_card_front",
                "mime_type": "image/png",
                "size_bytes": 200,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert "seller_ghana_card_front" in resp.json()["data"]["file_key"]

    def test_sealed_agreement_returns_400(self, mock_presign):
        client, acct = _make_client("+233501400004")
        agreement = _agreement(acct, status=AgreementStatus.SEALED)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "size_bytes": 100,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_unsupported_mime_type_returns_400(self, mock_presign):
        client, acct = _make_client("+233501400005")
        agreement = _agreement(acct)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {"evidence_type": "doc", "mime_type": "text/html", "size_bytes": 100, "checksum_sha256": _FAKE_CHECKSUM},
            format="json",
        )
        assert resp.status_code == 400

    def test_invalid_evidence_type_format_returns_400(self, mock_presign):
        client, acct = _make_client("+233501400006")
        agreement = _agreement(acct)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {"evidence_type": "Bad Name!", "mime_type": "image/jpeg", "size_bytes": 100, "checksum_sha256": _FAKE_CHECKSUM},
            format="json",
        )
        assert resp.status_code == 400

    def test_zero_size_returns_400(self, mock_presign):
        client, acct = _make_client("+233501400007")
        agreement = _agreement(acct)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "size_bytes": 0,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_other_users_agreement_returns_404(self, mock_presign):
        client, acct = _make_client("+233501400008")
        _, other_acct = _make_client("+233501400009")
        agreement = _agreement(other_acct)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "size_bytes": 100,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, mock_presign):
        _, acct = _make_client("+233501400010")
        agreement = _agreement(acct)
        resp = APIClient().post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "size_bytes": 100,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 401

    def test_links_uploaded_by_when_party_exists(self, mock_presign):
        client, acct = _make_client("+233501400011")
        agreement = _agreement(acct)
        _set_parties(agreement, acct.phone)
        client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {
                "evidence_type": "seller_ghana_card_front",
                "mime_type": "image/jpeg",
                "size_bytes": 500,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        item = EvidenceItem.objects.get(agreement=agreement, evidence_type="seller_ghana_card_front")
        assert item.uploaded_by is not None
        assert item.uploaded_by.phone == acct.phone

    def test_reserved_identity_slot_requires_matching_party_role(self, mock_presign):
        client, acct = _make_client("+233501400013")
        agreement = _agreement(acct)
        _set_parties(agreement, acct.phone)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {
                "evidence_type": "tenant_ghana_card_front",
                "mime_type": "image/jpeg",
                "size_bytes": 500,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_selfie_slot_requires_matching_party_role(self, mock_presign):
        client, acct = _make_client("+233501400014")
        agreement = _agreement(acct)
        _set_parties(agreement, acct.phone)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {
                "evidence_type": "tenant_selfie",
                "mime_type": "image/jpeg",
                "size_bytes": 500,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_identity_slot_rejects_pdf(self, mock_presign):
        client, acct = _make_client("+233501400015")
        agreement = _agreement(acct)
        _set_parties(agreement, acct.phone)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {
                "evidence_type": "seller_ghana_card_front",
                "mime_type": "application/pdf",
                "size_bytes": 500,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_storage_presign_failure_returns_503(self, mock_presign):
        mock_presign.side_effect = EndpointConnectionError(endpoint_url="http://storage.local")
        client, acct = _make_client("+233501400012")
        agreement = _agreement(acct)
        resp = client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "size_bytes": 500,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 503
        assert resp.json()["message"] == "Evidence storage is temporarily unavailable. Please try again."


@patch(
    "apps.evidence.api.serializers.S3StorageClient.generate_presigned_view_url",
    return_value=_FAKE_VIEW_URL,
)
@patch(
    "apps.evidence.services.S3StorageClient.head_object",
    return_value=_FAKE_HEAD,
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
            {
                "evidence_type": evidence_type,
                "mime_type": mime_type,
                "size_bytes": 500,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        return resp.json()["data"]

    def test_confirm_returns_201(self, mock_presign, mock_head, mock_view_url):
        client, acct = _make_client("+233501500001")
        agreement = _agreement(acct)
        upload = self._request_url(client, agreement.pk)
        resp = client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {
                "evidence_id": upload["evidence_id"],
                "file_key": upload["file_key"],
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()["data"]["evidence"]
        assert data["upload_status"] == "confirmed"
        assert data["view_url"] == _FAKE_VIEW_URL
        assert "storage_url" not in data
        assert "download_url" not in data
        assert "file_key" not in data
        assert EvidenceItem.objects.get(file_key=upload["file_key"]).storage_url == ""

    def test_confirmed_item_appears_in_list(self, mock_presign, mock_head, mock_view_url):
        client, acct = _make_client("+233501500002")
        agreement = _agreement(acct)
        upload = self._request_url(client, agreement.pk)
        client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {
                "file_key": upload["file_key"],
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        resp = client.get(_EVIDENCE_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        items = resp.json()["data"]["evidence"]
        assert len(items) == 1
        assert items[0]["upload_status"] == "confirmed"
        assert items[0]["view_url"] == _FAKE_VIEW_URL
        assert "storage_url" not in items[0]
        assert "download_url" not in items[0]
        assert "file_key" not in items[0]

    def test_pending_items_excluded_from_list(self, mock_presign, mock_head, mock_view_url):
        client, acct = _make_client("+233501500003")
        agreement = _agreement(acct)
        self._request_url(client, agreement.pk)  # creates pending item, no confirm
        resp = client.get(_EVIDENCE_PATH.format(id=agreement.pk))
        assert resp.json()["data"]["evidence"] == []

    def test_wrong_evidence_type_returns_400(self, mock_presign, mock_head, mock_view_url):
        client, acct = _make_client("+233501500004")
        agreement = _agreement(acct)
        _set_parties(agreement, "+233501500004")
        upload = self._request_url(client, agreement.pk, evidence_type="vehicle_photo_front")
        resp = client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {
                "file_key": upload["file_key"],
                "evidence_type": "seller_ghana_card_front",
                "mime_type": "image/jpeg",
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "evidence_type_mismatch"

    def test_wrong_mime_type_returns_400(self, mock_presign, mock_head, mock_view_url):
        client, acct = _make_client("+233501500005")
        agreement = _agreement(acct)
        upload = self._request_url(client, agreement.pk, mime_type="image/jpeg")
        resp = client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {
                "file_key": upload["file_key"],
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/png",
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "evidence_mime_mismatch"

    def test_unknown_file_key_returns_400(self, mock_presign, mock_head, mock_view_url):
        client, acct = _make_client("+233501500006")
        agreement = _agreement(acct)
        resp = client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {"file_key": "agreements/99/evidence/ghost.jpg",
             "evidence_type": "vehicle_photo_front", "mime_type": "image/jpeg", "checksum_sha256": _FAKE_CHECKSUM},
            format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "evidence_upload_not_pending"

    def test_confirm_twice_is_idempotent(self, mock_presign, mock_head, mock_view_url):
        client, acct = _make_client("+233501500007")
        agreement = _agreement(acct)
        upload = self._request_url(client, agreement.pk)
        payload = {
            "evidence_id": upload["evidence_id"],
            "file_key": upload["file_key"],
            "evidence_type": "vehicle_photo_front",
            "mime_type": "image/jpeg",
            "checksum_sha256": _FAKE_CHECKSUM,
        }
        first = client.post(_EVIDENCE_PATH.format(id=agreement.pk), payload, format="json")
        resp = client.post(_EVIDENCE_PATH.format(id=agreement.pk), payload, format="json")
        assert first.status_code == 201
        assert resp.status_code == 201
        assert resp.json()["data"]["evidence"]["id"] == first.json()["data"]["evidence"]["id"]

    def test_unauthenticated_returns_401(self, mock_presign, mock_head, mock_view_url):
        _, acct = _make_client("+233501500008")
        agreement = _agreement(acct)
        resp = APIClient().post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {"file_key": "k", "evidence_type": "x_y", "mime_type": "image/jpeg", "checksum_sha256": _FAKE_CHECKSUM},
            format="json",
        )
        assert resp.status_code == 401

    def test_storage_size_mismatch_returns_400(self, mock_presign, mock_head, mock_view_url):
        mock_head.return_value = {**_FAKE_HEAD, "content_length": 499}
        client, acct = _make_client("+233501500009")
        agreement = _agreement(acct)
        upload = self._request_url(client, agreement.pk)
        resp = client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {
                "file_key": upload["file_key"],
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "evidence_file_size_mismatch"

    def test_storage_mime_mismatch_returns_400(self, mock_presign, mock_head, mock_view_url):
        mock_head.return_value = {**_FAKE_HEAD, "content_type": "image/png"}
        client, acct = _make_client("+233501500010")
        agreement = _agreement(acct)
        upload = self._request_url(client, agreement.pk)
        resp = client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {
                "file_key": upload["file_key"],
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "evidence_mime_mismatch"

    def test_checksum_mismatch_returns_400(self, mock_presign, mock_head, mock_view_url):
        client, acct = _make_client("+233501500011")
        agreement = _agreement(acct)
        upload = self._request_url(client, agreement.pk)
        resp = client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {
                "file_key": upload["file_key"],
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "checksum_sha256": "b" * 64,
            },
            format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "evidence_checksum_mismatch"

    def test_storage_checksum_mismatch_returns_400(self, mock_presign, mock_head, mock_view_url):
        mock_head.return_value = {**_FAKE_HEAD, "metadata": {"sha256": "b" * 64}}
        client, acct = _make_client("+233501500012")
        agreement = _agreement(acct)
        upload = self._request_url(client, agreement.pk)
        resp = client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {
                "file_key": upload["file_key"],
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "evidence_checksum_mismatch"

    def test_storage_verify_failure_returns_503(self, mock_presign, mock_head, mock_view_url):
        mock_head.side_effect = EndpointConnectionError(endpoint_url="http://storage.local")
        client, acct = _make_client("+233501500013")
        agreement = _agreement(acct)
        upload = self._request_url(client, agreement.pk)
        resp = client.post(
            _EVIDENCE_PATH.format(id=agreement.pk),
            {
                "file_key": upload["file_key"],
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 503
        assert resp.json()["message"] == "Uploaded file could not be verified in storage. Please try again."


@patch(
    "apps.evidence.api.serializers.S3StorageClient.generate_presigned_view_url",
    return_value=_FAKE_VIEW_URL,
)
@patch(
    "apps.evidence.services.S3StorageClient.generate_presigned_upload_url",
    return_value=(_FAKE_PRESIGNED_URL, _FAKE_HEADERS),
)
@pytest.mark.django_db
class TestEvidenceListApi:
    def test_list_empty_agreement(self, mock_presign, mock_view_url):
        client, acct = _make_client("+233501600001")
        agreement = _agreement(acct)
        resp = client.get(_EVIDENCE_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        assert resp.json()["data"]["evidence"] == []

    def test_list_other_users_agreement_returns_404(self, mock_presign, mock_view_url):
        client, acct = _make_client("+233501600002")
        _, other_acct = _make_client("+233501600003")
        agreement = _agreement(other_acct)
        resp = client.get(_EVIDENCE_PATH.format(id=agreement.pk))
        assert resp.status_code == 404

    def test_participant_can_list_confirmed_evidence(self, mock_presign, mock_view_url):
        owner_client, owner_acct = _make_client("+233501600004")
        participant_client, participant_acct = _make_client("+233501600005")
        agreement = _agreement(owner_acct)
        PartyService.set_parties(
            agreement_id=agreement.pk,
            initiator_account=owner_acct,
            parties_data=[
                {
                    "role": "seller",
                    "full_name": "Owner",
                    "phone": owner_acct.phone,
                    "id_type": "ghana_card",
                    "id_number": _pin(100000001),
                },
                {
                    "role": "buyer",
                    "full_name": "Participant",
                    "phone": participant_acct.phone,
                    "id_type": "ghana_card",
                    "id_number": _pin(200000002),
                },
            ],
        )
        agreement.status = AgreementStatus.SEALED
        agreement.save(update_fields=["status"])
        EvidenceItem.objects.create(
            agreement=agreement,
            file_type=EvidenceItem.FileType.PHOTO,
            evidence_type="vehicle_photo_front",
            mime_type="image/jpeg",
            file_hash=_FAKE_CHECKSUM,
            file_key="agreements/1/evidence/vehicle_photo_front.jpg",
            storage_url=_FAKE_STORAGE_URL,
            upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        )

        with patch(
            "apps.evidence.services.S3StorageClient.head_object",
            return_value=_FAKE_HEAD,
        ):
            resp = participant_client.get(_EVIDENCE_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        item = resp.json()["data"]["evidence"][0]
        assert item["view_url"] == _FAKE_VIEW_URL
        assert "storage_url" not in item
        assert "download_url" not in item
        assert "file_key" not in item

    def test_participant_cannot_request_upload_url(self, mock_presign, mock_view_url):
        owner_client, owner_acct = _make_client("+233501600006")
        participant_client, participant_acct = _make_client("+233501600007")
        agreement = _agreement(owner_acct)
        PartyService.set_parties(
            agreement_id=agreement.pk,
            initiator_account=owner_acct,
            parties_data=[
                {
                    "role": "seller",
                    "full_name": "Owner",
                    "phone": owner_acct.phone,
                    "id_type": "ghana_card",
                    "id_number": _pin(300000003),
                },
                {
                    "role": "buyer",
                    "full_name": "Participant",
                    "phone": participant_acct.phone,
                    "id_type": "ghana_card",
                    "id_number": _pin(400000004),
                },
            ],
        )
        agreement.status = AgreementStatus.SEALED
        agreement.save(update_fields=["status"])

        resp = participant_client.post(
            _UPLOAD_URL_PATH.format(id=agreement.pk),
            {
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "size_bytes": 500,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )
        assert resp.status_code == 404
