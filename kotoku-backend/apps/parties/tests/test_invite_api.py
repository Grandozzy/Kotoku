"""API integration tests for the Party B identity invite flow.

Covers:
  - POST /api/agreements/{id}/parties/invite/{role}/   (PartyInviteSendView)
  - GET  /api/invites/{token}/                         (InviteDetailView)
  - POST /api/invites/{token}/claim/                   (InviteClaimView)
  - GET  /api/agreements/{id}/                         DRAFT access via claimed invite
  - POST /api/agreements/{id}/evidence/upload-url/     Party B identity evidence on DRAFT
  - POST /api/agreements/{id}/identity/{role}/liveness-session/  liveness on DRAFT
"""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.parties.models import Party, PartyInvite
from apps.parties.services import PartyService

_SEND_URL = "/api/agreements/{id}/parties/invite/{role}/"
_DETAIL_URL = "/api/invites/{token}/"
_CLAIM_URL = "/api/invites/{token}/claim/"
_AGREEMENT_URL = "/api/agreements/{id}/"
_UPLOAD_URL = "/api/agreements/{id}/evidence/upload-url/"
_LIVENESS_SESSION_URL = "/api/agreements/{id}/identity/{role}/liveness-session/"

_FAKE_PRESIGNED_URL = "https://storage.kotoku/bucket/key?X-Amz-Signature=fake"
_FAKE_HEADERS = {"Content-Type": "image/jpeg"}
_FAKE_CHECKSUM = "a" * 64

_seq = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(phone: str):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(user=user, email=f"inv_api{_seq}@test.com", phone=phone)
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, account


def _agreement(account: Account) -> Agreement:
    return Agreement.objects.create(title="API Invite Test", created_by=account)


def _pin(index: int) -> str:
    return f"GHA-{index:09d}-{index % 10}"


def _set_parties(agreement: Agreement, owner_phone: str, buyer_phone: str):
    from apps.accounts.models import Account as Acct

    owner_acct = Acct.objects.get(phone=owner_phone)
    PartyService.set_parties(
        agreement_id=agreement.pk,
        initiator_account=owner_acct,
        parties_data=[
            {
                "role": "seller",
                "full_name": "Seller Name",
                "phone": owner_phone,
                "id_type": "ghana_card",
                "id_number": _pin(200000001 + _seq),
            },
            {
                "role": "buyer",
                "full_name": "Buyer Name",
                "phone": buyer_phone,
                "id_type": "ghana_card",
                "id_number": _pin(300000001 + _seq),
            },
        ],
    )


def _claimed_invite_for_role(agreement: Agreement, role: str) -> PartyInvite:
    party = agreement.parties.get(role=role)
    return PartyInvite.objects.create(
        party=party,
        expires_at=timezone.now() + timedelta(days=7),
        accepted_at=timezone.now(),
    )


def _unclaimed_invite_for_role(agreement: Agreement, role: str) -> PartyInvite:
    party = agreement.parties.get(role=role)
    return PartyInvite.objects.create(
        party=party,
        expires_at=timezone.now() + timedelta(days=7),
    )


# ---------------------------------------------------------------------------
# PartyInviteSendView  POST /api/agreements/{id}/parties/invite/{role}/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPartyInviteSendView:
    @patch("apps.parties.invite_service.transaction.on_commit", lambda fn: fn())
    @patch("apps.notifications.tasks.send_sms_message.delay")
    def test_owner_can_send_invite_returns_201(self, mock_sms):
        client, acct = _make_client("+233502100001")
        ag = _agreement(acct)
        _set_parties(ag, acct.phone, "+233200100001")

        resp = client.post(_SEND_URL.format(id=ag.pk, role="buyer"))

        assert resp.status_code == 201

    @patch("apps.parties.invite_service.transaction.on_commit", lambda fn: fn())
    @patch("apps.notifications.tasks.send_sms_message.delay")
    def test_non_owner_cannot_send_invite_returns_404(self, mock_sms):
        owner_client, owner_acct = _make_client("+233502100002")
        other_client, _ = _make_client("+233502100003")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, "+233200100002")

        resp = other_client.post(_SEND_URL.format(id=ag.pk, role="buyer"))

        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self):
        owner_client, owner_acct = _make_client("+233502100004")
        ag = _agreement(owner_acct)

        resp = APIClient().post(_SEND_URL.format(id=ag.pk, role="buyer"))

        assert resp.status_code == 401

    @patch("apps.parties.invite_service.transaction.on_commit", lambda fn: fn())
    @patch("apps.notifications.tasks.send_sms_message.delay")
    def test_unknown_role_returns_404(self, mock_sms):
        client, acct = _make_client("+233502100005")
        ag = _agreement(acct)
        _set_parties(ag, acct.phone, "+233200100005")

        resp = client.post(_SEND_URL.format(id=ag.pk, role="witness"))

        assert resp.status_code == 404

    @patch("apps.parties.invite_service.transaction.on_commit", lambda fn: fn())
    @patch("apps.notifications.tasks.send_sms_message.delay")
    def test_party_without_phone_returns_400(self, mock_sms):
        client, acct = _make_client("+233502100006")
        ag = _agreement(acct)
        _set_parties(ag, acct.phone, "+233200100006")
        # Remove the phone from the buyer party to exercise the guard.
        ag.parties.filter(role="buyer").update(phone="")

        resp = client.post(_SEND_URL.format(id=ag.pk, role="buyer"))

        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# InviteDetailView  GET /api/invites/{token}/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInviteDetailView:
    def test_valid_unclaimed_token_returns_200_with_metadata(self):
        _, owner_acct = _make_client("+233502101001")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, "+233200101001")
        invite = _unclaimed_invite_for_role(ag, "buyer")

        resp = APIClient().get(_DETAIL_URL.format(token=str(invite.token)))

        assert resp.status_code == 200
        data = resp.json()["data"]["invite"]
        assert data["agreement_id"] == ag.pk
        assert data["role"] == "buyer"

    def test_invalid_token_returns_404(self):
        import uuid

        resp = APIClient().get(_DETAIL_URL.format(token=str(uuid.uuid4())))

        assert resp.status_code == 404

    def test_expired_token_returns_410(self):
        _, owner_acct = _make_client("+233502101002")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, "+233200101002")
        party = ag.parties.get(role="buyer")
        invite = PartyInvite.objects.create(
            party=party,
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        resp = APIClient().get(_DETAIL_URL.format(token=str(invite.token)))

        assert resp.status_code == 410
        assert resp.json()["code"] == "invite_expired"

    def test_claimed_but_incomplete_still_returns_200(self):
        """A claimed-but-abandoned invite must not return 410 — Party B needs re-entry."""
        _, owner_acct = _make_client("+233502101003")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, "+233200101003")
        invite = _claimed_invite_for_role(ag, "buyer")

        resp = APIClient().get(_DETAIL_URL.format(token=str(invite.token)))

        assert resp.status_code == 200
        assert resp.json()["data"]["invite"]["agreement_id"] == ag.pk

    def test_no_auth_header_required(self):
        """InviteDetailView is AllowAny — unauthenticated request must succeed."""
        _, owner_acct = _make_client("+233502101004")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, "+233200101004")
        invite = _unclaimed_invite_for_role(ag, "buyer")

        resp = APIClient().get(_DETAIL_URL.format(token=str(invite.token)))

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# InviteClaimView  POST /api/invites/{token}/claim/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInviteClaimView:
    def test_correct_phone_returns_200_with_agreement_id_and_role(self):
        buyer_client, buyer_acct = _make_client("+233502102001")
        _, owner_acct = _make_client("+233502102002")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        invite = _unclaimed_invite_for_role(ag, "buyer")

        resp = buyer_client.post(_CLAIM_URL.format(token=str(invite.token)))

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["agreement_id"] == ag.pk
        assert data["role"] == "buyer"

    def test_wrong_phone_returns_403(self):
        intruder_client, _ = _make_client("+233502102003")
        _, owner_acct = _make_client("+233502102004")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, "+233200102003")
        invite = _unclaimed_invite_for_role(ag, "buyer")

        resp = intruder_client.post(_CLAIM_URL.format(token=str(invite.token)))

        assert resp.status_code == 403
        assert resp.json()["code"] == "phone_mismatch"

    def test_expired_invite_returns_410(self):
        buyer_client, buyer_acct = _make_client("+233502102005")
        _, owner_acct = _make_client("+233502102006")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        party = ag.parties.get(role="buyer")
        invite = PartyInvite.objects.create(
            party=party,
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        resp = buyer_client.post(_CLAIM_URL.format(token=str(invite.token)))

        assert resp.status_code == 410

    def test_invalid_token_returns_410(self):
        import uuid

        buyer_client, _ = _make_client("+233502102007")
        resp = buyer_client.post(_CLAIM_URL.format(token=str(uuid.uuid4())))
        assert resp.status_code == 410

    def test_unauthenticated_returns_401(self):
        _, owner_acct = _make_client("+233502102008")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, "+233200102008")
        invite = _unclaimed_invite_for_role(ag, "buyer")

        resp = APIClient().post(_CLAIM_URL.format(token=str(invite.token)))

        assert resp.status_code == 401

    def test_idempotent_reclaim_same_phone_returns_200(self):
        """Party B re-opening the invite after abandoning must succeed, not 410."""
        buyer_client, buyer_acct = _make_client("+233502102009")
        _, owner_acct = _make_client("+233502102010")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        invite = _claimed_invite_for_role(ag, "buyer")

        resp = buyer_client.post(_CLAIM_URL.format(token=str(invite.token)))

        assert resp.status_code == 200
        assert resp.json()["data"]["agreement_id"] == ag.pk


# ---------------------------------------------------------------------------
# DRAFT agreement GET access for claimed invite holders
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDraftAgreementAccess:
    def test_claimed_invite_grants_get_on_draft_agreement(self):
        """GET /api/agreements/{id}/ must return 200 for Party B on a DRAFT agreement."""
        buyer_client, buyer_acct = _make_client("+233502103001")
        _, owner_acct = _make_client("+233502103002")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        assert ag.status == AgreementStatus.DRAFT
        _claimed_invite_for_role(ag, "buyer")

        resp = buyer_client.get(_AGREEMENT_URL.format(id=ag.pk))

        assert resp.status_code == 200
        data = resp.json()["data"]["agreement"]
        assert data["id"] == ag.pk

    def test_unclaimed_invite_does_not_grant_draft_access(self):
        """An unclaimed invite must not open DRAFT visibility."""
        buyer_client, buyer_acct = _make_client("+233502103003")
        _, owner_acct = _make_client("+233502103004")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        _unclaimed_invite_for_role(ag, "buyer")  # not claimed

        resp = buyer_client.get(_AGREEMENT_URL.format(id=ag.pk))

        assert resp.status_code == 404

    def test_stranger_cannot_access_draft_even_if_invite_exists(self):
        """A third party with no invite cannot access the DRAFT agreement."""
        stranger_client, _ = _make_client("+233502103005")
        _, owner_acct = _make_client("+233502103006")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, "+233200103006")
        _claimed_invite_for_role(ag, "buyer")  # belongs to a different phone

        resp = stranger_client.get(_AGREEMENT_URL.format(id=ag.pk))

        assert resp.status_code == 404

    def test_owner_can_always_get_draft_agreement(self):
        client, acct = _make_client("+233502103007")
        ag = _agreement(acct)
        assert ag.status == AgreementStatus.DRAFT

        resp = client.get(_AGREEMENT_URL.format(id=ag.pk))

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Party B evidence upload on DRAFT agreement
# ---------------------------------------------------------------------------


@patch(
    "apps.evidence.services.S3StorageClient.generate_presigned_upload_url",
    return_value=(_FAKE_PRESIGNED_URL, _FAKE_HEADERS),
)
@pytest.mark.django_db
class TestPartyBEvidenceUpload:
    def test_invited_party_can_upload_own_identity_evidence(self, mock_presign):
        buyer_client, buyer_acct = _make_client("+233502104001")
        _, owner_acct = _make_client("+233502104002")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        assert ag.status == AgreementStatus.DRAFT

        resp = buyer_client.post(
            _UPLOAD_URL.format(id=ag.pk),
            {
                "evidence_type": "buyer_ghana_card_front",
                "mime_type": "image/jpeg",
                "size_bytes": 300000,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )

        assert resp.status_code == 201

    def test_invited_party_cannot_upload_other_role_identity_evidence(self, mock_presign):
        """Party B must not upload evidence for the seller slot."""
        buyer_client, buyer_acct = _make_client("+233502104003")
        _, owner_acct = _make_client("+233502104004")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, buyer_acct.phone)

        resp = buyer_client.post(
            _UPLOAD_URL.format(id=ag.pk),
            {
                "evidence_type": "seller_ghana_card_front",
                "mime_type": "image/jpeg",
                "size_bytes": 300000,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )

        assert resp.status_code == 404

    def test_invited_party_cannot_upload_non_identity_evidence(self, mock_presign):
        """Non-identity evidence types are owner-only."""
        buyer_client, buyer_acct = _make_client("+233502104005")
        _, owner_acct = _make_client("+233502104006")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, buyer_acct.phone)

        resp = buyer_client.post(
            _UPLOAD_URL.format(id=ag.pk),
            {
                "evidence_type": "vehicle_photo_front",
                "mime_type": "image/jpeg",
                "size_bytes": 300000,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )

        assert resp.status_code == 404

    def test_stranger_cannot_upload_identity_evidence(self, mock_presign):
        stranger_client, _ = _make_client("+233502104007")
        _, owner_acct = _make_client("+233502104008")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, "+233200104008")

        resp = stranger_client.post(
            _UPLOAD_URL.format(id=ag.pk),
            {
                "evidence_type": "buyer_ghana_card_front",
                "mime_type": "image/jpeg",
                "size_bytes": 300000,
                "checksum_sha256": _FAKE_CHECKSUM,
            },
            format="json",
        )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Liveness session on DRAFT agreement via claimed invite
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLivenessOnDraftViaInvite:
    @patch("apps.identity.services.IdentityService.create_liveness_session", return_value="fake-session-id")
    def test_claimed_invite_holder_can_start_liveness_on_draft(self, mock_liveness):
        buyer_client, buyer_acct = _make_client("+233502105001")
        _, owner_acct = _make_client("+233502105002")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        assert ag.status == AgreementStatus.DRAFT
        _claimed_invite_for_role(ag, "buyer")

        resp = buyer_client.post(
            _LIVENESS_SESSION_URL.format(id=ag.pk, role="buyer")
        )

        assert resp.status_code == 201
        assert resp.json()["data"]["session_id"] == "fake-session-id"

    def test_no_claimed_invite_blocks_liveness_on_draft(self):
        buyer_client, buyer_acct = _make_client("+233502105003")
        _, owner_acct = _make_client("+233502105004")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        assert ag.status == AgreementStatus.DRAFT
        # No invite created at all.

        resp = buyer_client.post(
            _LIVENESS_SESSION_URL.format(id=ag.pk, role="buyer")
        )

        assert resp.status_code == 404

    @patch("apps.identity.services.IdentityService.create_liveness_session", return_value="fake-session-id")
    def test_unclaimed_invite_blocks_liveness_on_draft(self, mock_liveness):
        """Invite must be claimed (phone verified) to access liveness endpoint."""
        buyer_client, buyer_acct = _make_client("+233502105005")
        _, owner_acct = _make_client("+233502105006")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        _unclaimed_invite_for_role(ag, "buyer")  # not claimed

        resp = buyer_client.post(
            _LIVENESS_SESSION_URL.format(id=ag.pk, role="buyer")
        )

        assert resp.status_code == 404
