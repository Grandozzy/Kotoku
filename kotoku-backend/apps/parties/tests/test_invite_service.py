"""Unit tests for PartyInviteService and the PartyInvite model.

Covers: token expiry/claim helpers, create_and_send, get_detail, claim,
get_agreement_for_claimed_invite, and the idempotent re-claim fix.
"""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.agreements.models import Agreement
from apps.parties.models import Party, PartyInvite
from apps.parties.services import PartyService
from common.exceptions import DomainError

_seq = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _account(phone: str) -> Account:
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=phone)
    return Account.objects.create(user=user, email=f"inv{_seq}@test.com", phone=phone)


def _agreement(account: Account) -> Agreement:
    return Agreement.objects.create(title="Invite Test", created_by=account)


def _pin(index: int) -> str:
    return f"GHA-{index:09d}-{index % 10}"


def _set_parties(agreement: Agreement, owner_phone: str, buyer_phone: str) -> tuple[Party, Party]:
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
                "id_number": _pin(100000001),
            },
            {
                "role": "buyer",
                "full_name": "Buyer Name",
                "phone": buyer_phone,
                "id_type": "ghana_card",
                "id_number": _pin(100000002),
            },
        ],
    )
    seller = agreement.parties.get(role="seller")
    buyer = agreement.parties.get(role="buyer")
    return seller, buyer


def _claimed_invite(party: Party) -> PartyInvite:
    """Create a PartyInvite and mark it as claimed."""
    invite = PartyInvite.objects.create(
        party=party,
        expires_at=timezone.now() + timedelta(days=7),
        accepted_at=timezone.now(),
    )
    return invite


# ---------------------------------------------------------------------------
# PartyInvite model helpers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPartyInviteModel:
    def test_is_expired_false_for_future_expiry(self):
        acct = _account("+233501900001")
        ag = _agreement(acct)
        _, buyer = _set_parties(ag, acct.phone, "+233200900001")
        invite = PartyInvite.objects.create(
            party=buyer,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        assert invite.is_expired() is False

    def test_is_expired_true_for_past_expiry(self):
        acct = _account("+233501900002")
        ag = _agreement(acct)
        _, buyer = _set_parties(ag, acct.phone, "+233200900002")
        invite = PartyInvite.objects.create(
            party=buyer,
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        assert invite.is_expired() is True

    def test_is_claimed_false_before_claim(self):
        acct = _account("+233501900003")
        ag = _agreement(acct)
        _, buyer = _set_parties(ag, acct.phone, "+233200900003")
        invite = PartyInvite.objects.create(
            party=buyer,
            expires_at=timezone.now() + timedelta(days=7),
        )
        assert invite.is_claimed() is False

    def test_is_claimed_true_after_accepted_at_set(self):
        acct = _account("+233501900004")
        ag = _agreement(acct)
        _, buyer = _set_parties(ag, acct.phone, "+233200900004")
        invite = PartyInvite.objects.create(
            party=buyer,
            expires_at=timezone.now() + timedelta(days=7),
            accepted_at=timezone.now(),
        )
        assert invite.is_claimed() is True


# ---------------------------------------------------------------------------
# PartyInviteService.create_and_send
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateAndSend:
    @patch("apps.parties.invite_service.transaction.on_commit", lambda fn: fn())
    @patch("apps.notifications.tasks.send_sms_message.delay")
    def test_creates_invite_with_future_expiry(self, mock_sms):
        from apps.parties.invite_service import PartyInviteService

        acct = _account("+233501901001")
        ag = _agreement(acct)
        _, buyer = _set_parties(ag, acct.phone, "+233200901001")

        invite = PartyInviteService.create_and_send(party=buyer)

        assert invite.pk is not None
        assert invite.expires_at > timezone.now()
        assert invite.accepted_at is None

    @patch("apps.parties.invite_service.transaction.on_commit", lambda fn: fn())
    @patch("apps.notifications.tasks.send_sms_message.delay")
    def test_replaces_existing_invite(self, mock_sms):
        from apps.parties.invite_service import PartyInviteService

        acct = _account("+233501901002")
        ag = _agreement(acct)
        _, buyer = _set_parties(ag, acct.phone, "+233200901002")

        first = PartyInviteService.create_and_send(party=buyer)
        second = PartyInviteService.create_and_send(party=buyer)

        assert not PartyInvite.objects.filter(pk=first.pk).exists()
        assert PartyInvite.objects.filter(pk=second.pk).exists()

    @patch("apps.parties.invite_service.transaction.on_commit", lambda fn: fn())
    @patch("apps.notifications.tasks.send_sms_message.delay")
    def test_sms_queued_with_deep_link(self, mock_sms):
        from apps.parties.invite_service import PartyInviteService

        acct = _account("+233501901003")
        ag = _agreement(acct)
        _, buyer = _set_parties(ag, acct.phone, "+233200901003")

        invite = PartyInviteService.create_and_send(party=buyer)

        mock_sms.assert_called_once()
        call_kwargs = mock_sms.call_args
        body_arg = call_kwargs[1].get("body", "") or (call_kwargs[0][1] if call_kwargs[0] else "")
        assert str(invite.token) in body_arg

    def test_party_without_phone_raises(self):
        from apps.parties.invite_service import PartyInviteService

        acct = _account("+233501901004")
        ag = _agreement(acct)
        # Manually create a party with no phone to exercise the guard.
        party = Party.objects.create(
            agreement=ag,
            role="buyer",
            display_name="No Phone",
            phone="",
            id_type="ghana_card",
            id_number=_pin(999000001),
        )
        with pytest.raises(DomainError):
            PartyInviteService.create_and_send(party=party)


# ---------------------------------------------------------------------------
# PartyInviteService.get_detail
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetDetail:
    def test_valid_unclaimed_token_returns_metadata(self):
        from apps.parties.invite_service import PartyInviteService

        acct = _account("+233501902001")
        ag = _agreement(acct)
        _, buyer = _set_parties(ag, acct.phone, "+233200902001")
        invite = PartyInvite.objects.create(
            party=buyer,
            expires_at=timezone.now() + timedelta(days=7),
        )

        detail = PartyInviteService.get_detail(token=str(invite.token))

        assert detail["agreement_id"] == ag.pk
        assert detail["role"] == "buyer"
        assert detail["party_name"] == "Buyer Name"

    def test_invalid_token_raises_domain_error(self):
        from apps.parties.invite_service import PartyInviteService
        import uuid

        with pytest.raises(DomainError):
            PartyInviteService.get_detail(token=str(uuid.uuid4()))

    def test_expired_token_raises_invite_expired(self):
        from apps.parties.invite_service import PartyInviteService

        acct = _account("+233501902002")
        ag = _agreement(acct)
        _, buyer = _set_parties(ag, acct.phone, "+233200902002")
        invite = PartyInvite.objects.create(
            party=buyer,
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        with pytest.raises(DomainError) as exc_info:
            PartyInviteService.get_detail(token=str(invite.token))
        assert exc_info.value.code == "invite_expired"

    def test_claimed_but_incomplete_still_returns_metadata(self):
        """Claimed-but-abandoned invite should NOT block re-entry via get_detail."""
        from apps.parties.invite_service import PartyInviteService

        acct = _account("+233501902003")
        ag = _agreement(acct)
        _, buyer = _set_parties(ag, acct.phone, "+233200902003")
        invite = PartyInvite.objects.create(
            party=buyer,
            expires_at=timezone.now() + timedelta(days=7),
            accepted_at=timezone.now(),
        )

        detail = PartyInviteService.get_detail(token=str(invite.token))
        assert detail["agreement_id"] == ag.pk


# ---------------------------------------------------------------------------
# PartyInviteService.claim
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClaim:
    def test_correct_phone_sets_accepted_at_and_returns_data(self):
        from apps.parties.invite_service import PartyInviteService

        buyer_acct = _account("+233501903001")
        owner_acct = _account("+233501903002")
        ag = _agreement(owner_acct)
        _, buyer_party = _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        invite = PartyInvite.objects.create(
            party=buyer_party,
            expires_at=timezone.now() + timedelta(days=7),
        )

        result = PartyInviteService.claim(token=str(invite.token), account=buyer_acct)

        invite.refresh_from_db()
        assert invite.accepted_at is not None
        assert result["agreement_id"] == ag.pk
        assert result["role"] == "buyer"

    def test_wrong_phone_raises_phone_mismatch(self):
        from apps.parties.invite_service import PartyInviteService

        owner_acct = _account("+233501903003")
        intruder_acct = _account("+233501903004")
        ag = _agreement(owner_acct)
        _, buyer_party = _set_parties(ag, owner_acct.phone, "+233200903003")
        invite = PartyInvite.objects.create(
            party=buyer_party,
            expires_at=timezone.now() + timedelta(days=7),
        )

        with pytest.raises(DomainError) as exc_info:
            PartyInviteService.claim(token=str(invite.token), account=intruder_acct)
        assert exc_info.value.code == "phone_mismatch"

    def test_expired_invite_raises_invite_expired(self):
        from apps.parties.invite_service import PartyInviteService

        buyer_acct = _account("+233501903005")
        owner_acct = _account("+233501903006")
        ag = _agreement(owner_acct)
        _, buyer_party = _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        invite = PartyInvite.objects.create(
            party=buyer_party,
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        with pytest.raises(DomainError) as exc_info:
            PartyInviteService.claim(token=str(invite.token), account=buyer_acct)
        assert exc_info.value.code == "invite_expired"

    def test_invalid_token_raises_domain_error(self):
        from apps.parties.invite_service import PartyInviteService
        import uuid

        acct = _account("+233501903007")
        with pytest.raises(DomainError):
            PartyInviteService.claim(token=str(uuid.uuid4()), account=acct)

    def test_idempotent_same_phone_returns_data_without_error(self):
        """Re-claiming after abandoning must succeed, not raise invite_claimed."""
        from apps.parties.invite_service import PartyInviteService

        buyer_acct = _account("+233501903008")
        owner_acct = _account("+233501903009")
        ag = _agreement(owner_acct)
        _, buyer_party = _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        invite = PartyInvite.objects.create(
            party=buyer_party,
            expires_at=timezone.now() + timedelta(days=7),
            accepted_at=timezone.now(),  # already claimed
        )

        result = PartyInviteService.claim(token=str(invite.token), account=buyer_acct)

        assert result["agreement_id"] == ag.pk
        assert result["role"] == "buyer"

    def test_claimed_by_different_phone_raises_phone_mismatch(self):
        """A claimed invite must not let a different phone re-claim it."""
        from apps.parties.invite_service import PartyInviteService

        owner_acct = _account("+233501903010")
        intruder_acct = _account("+233501903011")
        ag = _agreement(owner_acct)
        _, buyer_party = _set_parties(ag, owner_acct.phone, "+233200903010")
        invite = PartyInvite.objects.create(
            party=buyer_party,
            expires_at=timezone.now() + timedelta(days=7),
            accepted_at=timezone.now(),
        )

        with pytest.raises(DomainError) as exc_info:
            PartyInviteService.claim(token=str(invite.token), account=intruder_acct)
        assert exc_info.value.code == "phone_mismatch"


# ---------------------------------------------------------------------------
# PartyInviteService.get_agreement_for_claimed_invite
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetAgreementForClaimedInvite:
    def test_claimed_invite_grants_access(self):
        from apps.parties.invite_service import PartyInviteService

        buyer_acct = _account("+233501904001")
        owner_acct = _account("+233501904002")
        ag = _agreement(owner_acct)
        _, buyer_party = _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        _claimed_invite(buyer_party)

        result = PartyInviteService.get_agreement_for_claimed_invite(
            ag.pk, account_phone=buyer_acct.phone
        )
        assert result.pk == ag.pk

    def test_unclaimed_invite_raises_does_not_exist(self):
        from apps.parties.invite_service import PartyInviteService
        from apps.agreements.models import Agreement

        buyer_acct = _account("+233501904003")
        owner_acct = _account("+233501904004")
        ag = _agreement(owner_acct)
        _, buyer_party = _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        # Invite exists but is NOT claimed (accepted_at is null).
        PartyInvite.objects.create(
            party=buyer_party,
            expires_at=timezone.now() + timedelta(days=7),
        )

        with pytest.raises(Agreement.DoesNotExist):
            PartyInviteService.get_agreement_for_claimed_invite(
                ag.pk, account_phone=buyer_acct.phone
            )

    def test_no_invite_raises_does_not_exist(self):
        from apps.parties.invite_service import PartyInviteService
        from apps.agreements.models import Agreement

        buyer_acct = _account("+233501904005")
        owner_acct = _account("+233501904006")
        ag = _agreement(owner_acct)
        _set_parties(ag, owner_acct.phone, "+233200904006")

        with pytest.raises(Agreement.DoesNotExist):
            PartyInviteService.get_agreement_for_claimed_invite(
                ag.pk, account_phone=buyer_acct.phone
            )

    def test_wrong_phone_raises_does_not_exist(self):
        """Phone in the query must match the party phone on the claimed invite."""
        from apps.parties.invite_service import PartyInviteService
        from apps.agreements.models import Agreement

        owner_acct = _account("+233501904007")
        buyer_acct = _account("+233501904008")
        intruder_acct = _account("+233501904009")
        ag = _agreement(owner_acct)
        _, buyer_party = _set_parties(ag, owner_acct.phone, buyer_acct.phone)
        _claimed_invite(buyer_party)

        with pytest.raises(Agreement.DoesNotExist):
            PartyInviteService.get_agreement_for_claimed_invite(
                ag.pk, account_phone=intruder_acct.phone
            )
