"""Tests for apps.agreements.domain.validators.

Unit tests drive the pure validator logic; API tests drive the HTTP layer.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Account, User
from apps.agreements.domain.validators import (
    SCENARIO_ROOM_RENTAL,
    SCENARIO_USED_VEHICLE_SALE,
    validate_agreement,
)
from apps.agreements.models import Agreement
from apps.evidence.models import EvidenceItem
from apps.parties.models import Party

_VALIDATE_PATH = "/api/agreements/{id}/validate/"

_seq = 0


# ── Helpers ───────────────────────────────────────────────────────────────── #


def _user_and_account(phone):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(user=user, email=f"val{_seq}@test.com", phone=phone)
    return user, account


def _agreement(account, scenario="", title="Test Agreement"):
    return Agreement.objects.create(title=title, created_by=account, scenario_template=scenario)


def _pin(index: int) -> str:
    return f"GHA-{index:09d}-{index % 10}"


def _party(agreement, role, id_type="ghana_card", id_number=None):
    return Party.objects.create(
        agreement=agreement,
        role=role,
        display_name=role.title(),
        phone="",
        id_type=id_type,
        id_number=id_number if id_number is not None else _pin(abs(hash(role)) % 1_000_000_000),
    )


def _evidence(agreement, evidence_type, status=EvidenceItem.UploadStatus.CONFIRMED):
    return EvidenceItem.objects.create(
        agreement=agreement,
        file_type=EvidenceItem.FileType.PHOTO,
        evidence_type=evidence_type,
        mime_type="image/jpeg",
        upload_status=status,
    )


def _identity_evidence(agreement, role):
    _evidence(agreement, f"{role}_ghana_card_front")
    _evidence(agreement, f"{role}_ghana_card_back")


def _api_client(phone):
    user, account = _user_and_account(phone)
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, account


# ── Unit tests: core field checks ─────────────────────────────────────────── #


@pytest.mark.django_db
class TestCoreFieldValidation:
    def test_missing_title_raises_error(self):
        _, acct = _user_and_account("+233600100001")
        a = Agreement.objects.create(title="", created_by=acct, scenario_template="")
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "MISSING_TITLE" in codes

    def test_missing_scenario_template_raises_error(self):
        _, acct = _user_and_account("+233600100002")
        a = _agreement(acct, scenario="")
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "MISSING_SCENARIO_TEMPLATE" in codes

    def test_valid_core_fields_produce_no_core_errors(self):
        _, acct = _user_and_account("+233600100003")
        a = _agreement(acct, scenario=SCENARIO_USED_VEHICLE_SALE)
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "MISSING_TITLE" not in codes
        assert "MISSING_SCENARIO_TEMPLATE" not in codes


# ── Unit tests: party checks ──────────────────────────────────────────────── #


@pytest.mark.django_db
class TestPartyValidation:
    def test_fewer_than_two_parties_returns_error(self):
        _, acct = _user_and_account("+233600200001")
        a = _agreement(acct, scenario=SCENARIO_USED_VEHICLE_SALE)
        _party(a, "buyer")
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "INSUFFICIENT_PARTIES" in codes

    def test_no_parties_returns_error(self):
        _, acct = _user_and_account("+233600200002")
        a = _agreement(acct, scenario=SCENARIO_USED_VEHICLE_SALE)
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "INSUFFICIENT_PARTIES" in codes

    def test_wrong_role_pair_for_vehicle_sale(self):
        _, acct = _user_and_account("+233600200003")
        a = _agreement(acct, scenario=SCENARIO_USED_VEHICLE_SALE)
        _party(a, "landlord")
        _party(a, "tenant")
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "MISSING_REQUIRED_ROLES" in codes

    def test_correct_role_pair_for_vehicle_sale(self):
        _, acct = _user_and_account("+233600200004")
        a = _agreement(acct, scenario=SCENARIO_USED_VEHICLE_SALE)
        _party(a, "buyer")
        _party(a, "seller")
        # Evidence errors will remain, but no party role error
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "MISSING_REQUIRED_ROLES" not in codes

    def test_correct_role_pair_for_room_rental(self):
        _, acct = _user_and_account("+233600200005")
        a = _agreement(acct, scenario=SCENARIO_ROOM_RENTAL)
        _party(a, "landlord")
        _party(a, "tenant")
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "MISSING_REQUIRED_ROLES" not in codes


# ── Unit tests: used_vehicle_sale evidence ────────────────────────────────── #


@pytest.mark.django_db
class TestUsedVehicleSaleValidation:
    def _base(self):
        _, acct = _user_and_account(f"+233600{_seq:06d}")
        a = _agreement(acct, scenario=SCENARIO_USED_VEHICLE_SALE)
        _party(a, "buyer")
        _party(a, "seller")
        return a

    def test_insufficient_vehicle_photos(self):
        a = self._base()
        _evidence(a, "vehicle_photo_front")
        _evidence(a, "vehicle_photo_rear")
        # Only 2 — need 3
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "INSUFFICIENT_VEHICLE_PHOTOS" in codes

    def test_three_vehicle_photos_clears_error(self):
        a = self._base()
        _evidence(a, "vehicle_photo_front")
        _evidence(a, "vehicle_photo_rear")
        _evidence(a, "vehicle_photo_side")
        _identity_evidence(a, "buyer")
        _identity_evidence(a, "seller")
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "INSUFFICIENT_VEHICLE_PHOTOS" not in codes

    def test_missing_buyer_ghana_card_front(self):
        a = self._base()
        for t in ("vehicle_photo_front", "vehicle_photo_rear", "vehicle_photo_side"):
            _evidence(a, t)
        _identity_evidence(a, "seller")
        _evidence(a, "buyer_ghana_card_back")
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "MISSING_GHANA_CARD_FRONT" in codes
        id_errors = [e for e in result.errors if e.code == "MISSING_GHANA_CARD_FRONT"]
        assert len(id_errors) == 1
        assert "buyer" in id_errors[0].message

    def test_pending_evidence_not_counted(self):
        a = self._base()
        # Three pending vehicle photos — should NOT count toward the minimum
        for t in ("vehicle_photo_front", "vehicle_photo_rear", "vehicle_photo_side"):
            _evidence(a, t, status=EvidenceItem.UploadStatus.PENDING)
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "INSUFFICIENT_VEHICLE_PHOTOS" in codes

    def test_fully_valid_vehicle_sale(self):
        a = self._base()
        for t in ("vehicle_photo_front", "vehicle_photo_rear", "vehicle_photo_side"):
            _evidence(a, t)
        _identity_evidence(a, "buyer")
        _identity_evidence(a, "seller")
        result = validate_agreement(a)
        assert result.valid is True


# ── Unit tests: room_rental evidence ─────────────────────────────────────── #


@pytest.mark.django_db
class TestRoomRentalValidation:
    def _base(self):
        _, acct = _user_and_account(f"+233600{_seq:06d}")
        a = _agreement(acct, scenario=SCENARIO_ROOM_RENTAL)
        _party(a, "landlord")
        _party(a, "tenant")
        return a

    def test_insufficient_property_photos(self):
        a = self._base()
        _evidence(a, "property_photo_front")
        # Only 1 — need 2
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "INSUFFICIENT_PROPERTY_PHOTOS" in codes

    def test_two_property_photos_clears_error(self):
        a = self._base()
        _evidence(a, "property_photo_front")
        _evidence(a, "property_photo_interior")
        _identity_evidence(a, "landlord")
        _identity_evidence(a, "tenant")
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "INSUFFICIENT_PROPERTY_PHOTOS" not in codes

    def test_fully_valid_room_rental_no_deposit(self):
        a = self._base()
        _evidence(a, "property_photo_front")
        _evidence(a, "property_photo_interior")
        _identity_evidence(a, "landlord")
        _identity_evidence(a, "tenant")
        result = validate_agreement(a)
        assert result.valid is True

    def test_unknown_scenario_skips_scenario_checks(self):
        _, acct = _user_and_account("+233600300001")
        a = _agreement(acct, scenario="custom_deal")
        _party(a, "buyer")
        _party(a, "seller")
        _identity_evidence(a, "buyer")
        _identity_evidence(a, "seller")
        # No scenario-specific checker → vehicle/property checks are skipped
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "INSUFFICIENT_VEHICLE_PHOTOS" not in codes
        assert "INSUFFICIENT_PROPERTY_PHOTOS" not in codes

    def test_unknown_scenario_still_requires_party_ghana_card_uploads(self):
        _, acct = _user_and_account("+233600300002")
        a = _agreement(acct, scenario="custom_deal")
        _party(a, "buyer")
        _party(a, "seller")
        _identity_evidence(a, "buyer")
        _evidence(a, "seller_ghana_card_front")
        result = validate_agreement(a)
        id_errors = [e for e in result.errors if e.code == "MISSING_GHANA_CARD_BACK"]
        assert len(id_errors) == 1
        assert "seller" in id_errors[0].message


# ── API tests ─────────────────────────────────────────────────────────────── #


@pytest.mark.django_db
class TestValidateApi:
    def test_returns_200_with_valid_false_when_errors(self):
        client, acct = _api_client("+233600400001")
        a = _agreement(acct)  # No scenario, no parties
        resp = client.post(_VALIDATE_PATH.format(id=a.pk))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_errors_have_required_keys(self):
        client, acct = _api_client("+233600400002")
        a = _agreement(acct)
        resp = client.post(_VALIDATE_PATH.format(id=a.pk))
        for err in resp.json()["data"]["errors"]:
            assert "code" in err
            assert "message" in err
            assert "field" in err

    def test_returns_valid_true_for_complete_vehicle_sale(self):
        client, acct = _api_client("+233600400003")
        a = _agreement(acct, scenario=SCENARIO_USED_VEHICLE_SALE)
        _party(a, "buyer")
        _party(a, "seller")
        for t in ("vehicle_photo_front", "vehicle_photo_rear", "vehicle_photo_side"):
            _evidence(a, t)
        _identity_evidence(a, "buyer")
        _identity_evidence(a, "seller")
        resp = client.post(_VALIDATE_PATH.format(id=a.pk))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["valid"] is True
        assert data["errors"] == []

    def test_specific_error_codes_present(self):
        client, acct = _api_client("+233600400004")
        a = _agreement(acct, scenario=SCENARIO_USED_VEHICLE_SALE)
        _party(a, "buyer")
        _party(a, "seller")
        # No evidence at all
        resp = client.post(_VALIDATE_PATH.format(id=a.pk))
        codes = {e["code"] for e in resp.json()["data"]["errors"]}
        assert "INSUFFICIENT_VEHICLE_PHOTOS" in codes
        assert "MISSING_GHANA_CARD_FRONT" in codes
        assert "MISSING_GHANA_CARD_BACK" in codes

    def test_other_users_agreement_returns_404(self):
        client, acct = _api_client("+233600400005")
        _, other_acct = _api_client("+233600400006")
        a = _agreement(other_acct)
        resp = client.post(_VALIDATE_PATH.format(id=a.pk))
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self):
        _, acct = _api_client("+233600400007")
        a = _agreement(acct)
        resp = APIClient().post(_VALIDATE_PATH.format(id=a.pk))
        assert resp.status_code == 401

    def test_nonexistent_agreement_returns_404(self):
        client, acct = _api_client("+233600400008")
        resp = client.post(_VALIDATE_PATH.format(id=99999))
        assert resp.status_code == 404


# ── Unit tests: identity baseline ────────────────────────────────────────── #


@pytest.mark.django_db
class TestIdentityBaselineValidation:
    def test_party_without_id_type_fails(self):
        _, acct = _user_and_account("+233600500001")
        a = _agreement(acct, scenario=SCENARIO_USED_VEHICLE_SALE)
        _party(a, "buyer", id_type="", id_number=_pin(111111111))
        _party(a, "seller")
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "MISSING_GHANA_CARD_PIN" in codes

    def test_party_without_id_number_fails(self):
        _, acct = _user_and_account("+233600500002")
        a = _agreement(acct, scenario=SCENARIO_USED_VEHICLE_SALE)
        _party(a, "buyer", id_type="ghana_card", id_number="")
        _party(a, "seller")
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "MISSING_GHANA_CARD_PIN" in codes

    def test_witness_role_skips_identity_check(self):
        _, acct = _user_and_account("+233600500003")
        a = _agreement(acct, scenario="custom_deal")
        _party(a, "buyer")
        _party(a, "seller")
        # Witness with no identity data — should NOT trigger Ghana Card PIN errors
        Party.objects.create(
            agreement=a,
            role="witness",
            display_name="Witness",
            phone="",
            id_type="",
            id_number="",
        )
        result = validate_agreement(a)
        id_errors = [e for e in result.errors if e.code == "MISSING_GHANA_CARD_PIN"]
        assert len(id_errors) == 0

    def test_duplicate_ghana_card_pin_fails(self):
        _, acct = _user_and_account("+233600500004")
        a = _agreement(acct, scenario=SCENARIO_USED_VEHICLE_SALE)
        duplicate_pin = _pin(444444444)
        _party(a, "buyer", id_type="ghana_card", id_number=duplicate_pin)
        _party(a, "seller", id_type="ghana_card", id_number=duplicate_pin)
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "DUPLICATE_GHANA_CARD_PIN" in codes

    def test_all_parties_with_valid_ghana_card_identity_no_error(self):
        _, acct = _user_and_account("+233600500005")
        a = _agreement(acct, scenario=SCENARIO_USED_VEHICLE_SALE)
        _party(a, "buyer", id_type="ghana_card", id_number=_pin(555555555))
        _party(a, "seller", id_type="ghana_card", id_number=_pin(666666666))
        for t in ("vehicle_photo_front", "vehicle_photo_rear", "vehicle_photo_side"):
            _evidence(a, t)
        _identity_evidence(a, "buyer")
        _identity_evidence(a, "seller")
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "INVALID_GHANA_CARD_PIN" not in codes
        assert "MISSING_GHANA_CARD_FRONT" not in codes
        assert "MISSING_GHANA_CARD_BACK" not in codes

    def test_party_with_non_ghana_card_type_fails(self):
        _, acct = _user_and_account("+233600500006")
        a = _agreement(acct, scenario="custom_deal")
        _party(a, "buyer", id_type="national_id", id_number=_pin(777777777))
        _party(a, "seller", id_type="ghana_card", id_number=_pin(888888888))
        _identity_evidence(a, "buyer")
        _identity_evidence(a, "seller")
        result = validate_agreement(a)
        codes = {e.code for e in result.errors}
        assert "INVALID_GHANA_CARD_PIN" in codes
