import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.parties.services import PartyService

_URL = "/api/agreements/{id}/parties/"

_seq = 0


def _make_client(phone):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(user=user, email=f"u{_seq}@api.com", phone=phone)
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, account


def _agreement(account, status=AgreementStatus.DRAFT):
    a = Agreement.objects.create(title="API Test", created_by=account)
    if status != AgreementStatus.DRAFT:
        a.status = status
        a.save()
    return a


def _pin(index: int) -> str:
    return f"GHA-{index:09d}-{index % 10}"


def _valid_body(initiator_phone):
    return {
        "parties": [
            {
                "role": "seller",
                "full_name": "Kofi Mensah",
                "phone": initiator_phone,
                "id_type": "ghana_card",
                "id_number": _pin(111111111),
            },
            {
                "role": "buyer",
                "full_name": "Ama Owusu",
                "phone": "+233200000099",
                "id_type": "ghana_card",
                "id_number": _pin(222222222),
            },
        ]
    }


@pytest.mark.django_db
class TestPartiesPostApi:
    def test_set_parties_returns_200(self):
        client, acct = _make_client("+233501111001")
        agreement = _agreement(acct)
        resp = client.post(
            _URL.format(id=agreement.pk),
            _valid_body(acct.phone),
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]["parties"]
        assert len(data) == 2
        roles = {p["role"] for p in data}
        assert roles == {"seller", "buyer"}

    def test_returns_full_party_fields(self):
        client, acct = _make_client("+233501111002")
        agreement = _agreement(acct)
        resp = client.post(
            _URL.format(id=agreement.pk),
            _valid_body(acct.phone),
            format="json",
        )
        seller = next(p for p in resp.json()["data"]["parties"] if p["role"] == "seller")
        assert seller["full_name"] == "Kofi Mensah"
        assert seller["phone"] == acct.phone
        assert seller["id_type"] == "ghana_card"
        assert seller["id_number"] == _pin(111111111)

    def test_fewer_than_two_parties_returns_400(self):
        client, acct = _make_client("+233501111003")
        agreement = _agreement(acct)
        resp = client.post(
            _URL.format(id=agreement.pk),
            {"parties": [_valid_body(acct.phone)["parties"][0]]},
            format="json",
        )
        assert resp.status_code == 400

    def test_duplicate_roles_returns_400(self):
        client, acct = _make_client("+233501111004")
        agreement = _agreement(acct)
        body = {
            "parties": [
                {
                    "role": "seller",
                    "full_name": "A",
                    "phone": acct.phone,
                    "id_type": "ghana_card",
                    "id_number": _pin(111111112),
                },
                {
                    "role": "seller",
                    "full_name": "B",
                    "phone": "+233200000001",
                    "id_type": "ghana_card",
                    "id_number": _pin(111111113),
                },
            ]
        }
        resp = client.post(_URL.format(id=agreement.pk), body, format="json")
        assert resp.status_code == 400

    def test_initiator_phone_not_in_parties_returns_400(self):
        client, acct = _make_client("+233501111005")
        agreement = _agreement(acct)
        body = {
            "parties": [
                {
                    "role": "seller",
                    "full_name": "X",
                    "phone": "+233999000001",
                    "id_type": "ghana_card",
                    "id_number": _pin(111111114),
                },
                {
                    "role": "buyer",
                    "full_name": "Y",
                    "phone": "+233999000002",
                    "id_type": "ghana_card",
                    "id_number": _pin(111111115),
                },
            ]
        }
        resp = client.post(_URL.format(id=agreement.pk), body, format="json")
        assert resp.status_code == 400

    def test_sealed_agreement_returns_400(self):
        client, acct = _make_client("+233501111006")
        agreement = _agreement(acct, status=AgreementStatus.SEALED)
        resp = client.post(
            _URL.format(id=agreement.pk),
            _valid_body(acct.phone),
            format="json",
        )
        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self):
        client, acct = _make_client("+233501111007")
        agreement = _agreement(acct)
        resp = APIClient().post(
            _URL.format(id=agreement.pk),
            _valid_body(acct.phone),
            format="json",
        )
        assert resp.status_code == 401

    def test_other_users_agreement_returns_404(self):
        client, acct = _make_client("+233501111008")
        _, other_acct = _make_client("+233501111009")
        agreement = _agreement(other_acct)
        resp = client.post(
            _URL.format(id=agreement.pk),
            _valid_body(acct.phone),
            format="json",
        )
        assert resp.status_code == 404

    def test_local_phone_format_is_normalized(self):
        client, acct = _make_client("+233501111010")
        agreement = _agreement(acct)
        body = _valid_body(acct.phone)
        body["parties"][0]["phone"] = "0501234567"
        resp = client.post(_URL.format(id=agreement.pk), body, format="json")
        assert resp.status_code == 200
        seller = next(p for p in resp.json()["data"]["parties"] if p["role"] == "seller")
        assert seller["phone"] == "+233501234567"

    def test_other_id_type_returns_400(self):
        client, acct = _make_client("+233501111012")
        agreement = _agreement(acct)
        body = _valid_body(acct.phone)
        body["parties"][1]["id_type"] = "other"
        resp = client.post(_URL.format(id=agreement.pk), body, format="json")
        assert resp.status_code == 400

    def test_non_ghana_card_type_returns_400(self):
        client, acct = _make_client("+233501111013")
        agreement = _agreement(acct)
        body = _valid_body(acct.phone)
        body["parties"][1]["id_type"] = "national_id"
        body["parties"][1]["id_number"] = _pin(111111116)
        resp = client.post(_URL.format(id=agreement.pk), body, format="json")
        assert resp.status_code == 400

    def test_blank_id_number_returns_400(self):
        client, acct = _make_client("+233501111014")
        agreement = _agreement(acct)
        body = _valid_body(acct.phone)
        body["parties"][1]["id_number"] = ""
        resp = client.post(_URL.format(id=agreement.pk), body, format="json")
        assert resp.status_code == 400

    def test_invalid_ghana_card_pin_returns_400(self):
        client, acct = _make_client("+233501111015")
        agreement = _agreement(acct)
        body = _valid_body(acct.phone)
        body["parties"][1]["id_number"] = "BAD-PIN"
        resp = client.post(_URL.format(id=agreement.pk), body, format="json")
        assert resp.status_code == 400

    def test_duplicate_ghana_card_pin_returns_400(self):
        client, acct = _make_client("+233501111016")
        agreement = _agreement(acct)
        body = _valid_body(acct.phone)
        body["parties"][1]["id_number"] = body["parties"][0]["id_number"]
        resp = client.post(_URL.format(id=agreement.pk), body, format="json")
        assert resp.status_code == 400

    def test_replaces_existing_parties(self):
        client, acct = _make_client("+233501111011")
        agreement = _agreement(acct)
        client.post(_URL.format(id=agreement.pk), _valid_body(acct.phone), format="json")
        # Second POST with different names
        body = _valid_body(acct.phone)
        body["parties"][1]["full_name"] = "Ama Replaced"
        resp = client.post(_URL.format(id=agreement.pk), body, format="json")
        assert resp.status_code == 200
        buyer = next(p for p in resp.json()["data"]["parties"] if p["role"] == "buyer")
        assert buyer["full_name"] == "Ama Replaced"


@pytest.mark.django_db
class TestPartiesPatchApi:
    def _setup(self, phone):
        client, acct = _make_client(phone)
        agreement = _agreement(acct)
        PartyService.set_parties(
            agreement_id=agreement.pk,
            initiator_account=acct,
            parties_data=[
                {
                    "role": "seller",
                    "full_name": "Kofi",
                    "phone": acct.phone,
                    "id_type": "ghana_card",
                    "id_number": _pin(111111117),
                },
                {
                    "role": "buyer",
                    "full_name": "Ama",
                    "phone": "+233200000050",
                    "id_type": "ghana_card",
                    "id_number": _pin(111111118),
                },
            ],
        )
        return client, acct, agreement

    def test_patch_phone_returns_200(self):
        client, acct, agreement = self._setup("+233501222001")
        resp = client.patch(
            _URL.format(id=agreement.pk),
            {"parties": [{"role": "buyer", "phone": "+233200000099"}]},
            format="json",
        )
        assert resp.status_code == 200
        buyer = next(p for p in resp.json()["data"]["parties"] if p["role"] == "buyer")
        assert buyer["phone"] == "+233200000099"

    def test_patch_does_not_overwrite_untouched_fields(self):
        client, acct, agreement = self._setup("+233501222002")
        resp = client.patch(
            _URL.format(id=agreement.pk),
            {"parties": [{"role": "buyer", "id_number": _pin(111111119)}]},
            format="json",
        )
        buyer = next(p for p in resp.json()["data"]["parties"] if p["role"] == "buyer")
        assert buyer["full_name"] == "Ama"  # unchanged
        assert buyer["id_number"] == _pin(111111119)

    def test_patch_unknown_role_returns_400(self):
        client, acct, agreement = self._setup("+233501222003")
        resp = client.patch(
            _URL.format(id=agreement.pk),
            {"parties": [{"role": "witness", "full_name": "Ghost"}]},
            format="json",
        )
        assert resp.status_code == 400

    def test_patch_sealed_agreement_returns_400(self):
        client, acct = _make_client("+233501222004")
        agreement = _agreement(acct, status=AgreementStatus.SEALED)
        resp = client.patch(
            _URL.format(id=agreement.pk),
            {"parties": [{"role": "buyer", "phone": "+233200000099"}]},
            format="json",
        )
        assert resp.status_code == 400

    def test_patch_unauthenticated_returns_401(self):
        _, acct = _make_client("+233501222005")
        agreement = _agreement(acct)
        resp = APIClient().patch(
            _URL.format(id=agreement.pk),
            {"parties": [{"role": "buyer", "phone": "+233200000099"}]},
            format="json",
        )
        assert resp.status_code == 401


@pytest.mark.django_db
class TestPartiesGetApi:
    def test_get_returns_parties_list(self):
        client, acct = _make_client("+233501333001")
        agreement = _agreement(acct)
        PartyService.set_parties(
            agreement_id=agreement.pk,
            initiator_account=acct,
            parties_data=[
                {
                    "role": "seller",
                    "full_name": "Kofi",
                    "phone": acct.phone,
                    "id_type": "ghana_card",
                    "id_number": _pin(111111120),
                },
                {
                    "role": "buyer",
                    "full_name": "Ama",
                    "phone": "+233200000030",
                    "id_type": "ghana_card",
                    "id_number": _pin(111111121),
                },
            ],
        )
        resp = client.get(_URL.format(id=agreement.pk))
        assert resp.status_code == 200
        assert len(resp.json()["data"]["parties"]) == 2

    def test_get_empty_agreement_returns_empty_list(self):
        client, acct = _make_client("+233501333002")
        agreement = _agreement(acct)
        resp = client.get(_URL.format(id=agreement.pk))
        assert resp.status_code == 200
        assert resp.json()["data"]["parties"] == []

    def test_participant_can_view_parties_after_consent_stage(self):
        owner_client, owner_acct = _make_client("+233501333003")
        participant_client, participant_acct = _make_client("+233501333004")
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
                    "id_number": _pin(111111122),
                },
                {
                    "role": "buyer",
                    "full_name": "Participant",
                    "phone": participant_acct.phone,
                    "id_type": "ghana_card",
                    "id_number": _pin(111111123),
                },
            ],
        )
        agreement.status = AgreementStatus.PENDING_CONSENT
        agreement.save(update_fields=["status"])

        resp = participant_client.get(_URL.format(id=agreement.pk))
        assert resp.status_code == 200
        assert len(resp.json()["data"]["parties"]) == 2

    def test_participant_cannot_set_or_patch_parties(self):
        owner_client, owner_acct = _make_client("+233501333005")
        participant_client, participant_acct = _make_client("+233501333006")
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
                    "id_number": _pin(111111124),
                },
                {
                    "role": "buyer",
                    "full_name": "Participant",
                    "phone": participant_acct.phone,
                    "id_type": "ghana_card",
                    "id_number": _pin(111111125),
                },
            ],
        )

        set_resp = participant_client.post(
            _URL.format(id=agreement.pk),
            _valid_body(participant_acct.phone),
            format="json",
        )
        patch_resp = participant_client.patch(
            _URL.format(id=agreement.pk),
            {"parties": [{"role": "buyer", "phone": "+233200000199"}]},
            format="json",
        )
        assert set_resp.status_code == 404
        assert patch_resp.status_code == 404
