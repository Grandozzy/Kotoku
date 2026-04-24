import pytest
from django.db import IntegrityError

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.audit.models import AuditLog
from apps.parties.models import Party
from apps.parties.services import PartyService
from common.exceptions import DomainError

_seq = 0


def _account(phone_suffix="00000001"):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=f"+233{_seq:09d}")
    return Account.objects.create(user=user, email=f"u{_seq}@test.com", phone=user.phone)


def _agreement(account, status=AgreementStatus.DRAFT):
    a = Agreement.objects.create(title="Test", created_by=account)
    if status != AgreementStatus.DRAFT:
        a.status = status
        a.save()
    return a


_SELLER = {"role": "seller", "full_name": "Kofi Mensah", "phone": "", "id_type": "ghana_card", "id_number": "GHA-111"}
_BUYER = {"role": "buyer", "full_name": "Ama Owusu", "phone": "+233200000002", "id_type": "ghana_card", "id_number": "GHA-222"}


def _parties(initiator_phone):
    return [
        {**_SELLER, "phone": initiator_phone},
        _BUYER,
    ]


@pytest.mark.django_db
class TestSetParties:
    def test_creates_two_parties(self):
        acct = _account()
        agreement = _agreement(acct)
        parties = PartyService.set_parties(
            agreement_id=agreement.pk,
            initiator_account=acct,
            parties_data=_parties(acct.phone),
        )
        assert len(parties) == 2
        roles = {p.role for p in parties}
        assert roles == {"seller", "buyer"}

    def test_stores_contact_fields(self):
        acct = _account()
        agreement = _agreement(acct)
        PartyService.set_parties(
            agreement_id=agreement.pk,
            initiator_account=acct,
            parties_data=_parties(acct.phone),
        )
        seller = Party.objects.get(agreement=agreement, role="seller")
        assert seller.display_name == "Kofi Mensah"
        assert seller.id_type == "ghana_card"
        assert seller.id_number == "GHA-111"

    def test_replaces_existing_parties(self):
        acct = _account()
        agreement = _agreement(acct)
        PartyService.set_parties(
            agreement_id=agreement.pk,
            initiator_account=acct,
            parties_data=_parties(acct.phone),
        )
        # Second call: update display names
        new_data = [
            {**_SELLER, "phone": acct.phone, "full_name": "Kofi Updated"},
            {**_BUYER, "full_name": "Ama Updated"},
        ]
        parties = PartyService.set_parties(
            agreement_id=agreement.pk,
            initiator_account=acct,
            parties_data=new_data,
        )
        assert len(parties) == 2
        assert Party.objects.filter(agreement=agreement).count() == 2
        assert Party.objects.get(agreement=agreement, role="seller").display_name == "Kofi Updated"

    def test_raises_when_fewer_than_two_parties(self):
        acct = _account()
        agreement = _agreement(acct)
        with pytest.raises(DomainError, match="two parties"):
            PartyService.set_parties(
                agreement_id=agreement.pk,
                initiator_account=acct,
                parties_data=[{**_SELLER, "phone": acct.phone}],
            )

    def test_raises_on_duplicate_roles(self):
        acct = _account()
        agreement = _agreement(acct)
        with pytest.raises(DomainError, match="unique role"):
            PartyService.set_parties(
                agreement_id=agreement.pk,
                initiator_account=acct,
                parties_data=[
                    {**_SELLER, "phone": acct.phone},
                    {**_SELLER, "full_name": "Duplicate Seller"},
                ],
            )

    def test_raises_when_initiator_phone_not_in_parties(self):
        acct = _account()
        agreement = _agreement(acct)
        with pytest.raises(DomainError, match="phone number"):
            PartyService.set_parties(
                agreement_id=agreement.pk,
                initiator_account=acct,
                parties_data=[
                    {**_SELLER, "phone": "+233999999991"},
                    {**_BUYER, "phone": "+233999999992"},
                ],
            )

    def test_raises_when_agreement_sealed(self):
        acct = _account()
        agreement = _agreement(acct, status=AgreementStatus.SEALED)
        with pytest.raises(DomainError, match="sealed"):
            PartyService.set_parties(
                agreement_id=agreement.pk,
                initiator_account=acct,
                parties_data=_parties(acct.phone),
            )

    def test_emits_audit_event(self):
        acct = _account()
        agreement = _agreement(acct)
        PartyService.set_parties(
            agreement_id=agreement.pk,
            initiator_account=acct,
            parties_data=_parties(acct.phone),
        )
        assert AuditLog.objects.filter(
            event_type="agreement.parties_set",
            entity_id=str(agreement.pk),
        ).exists()


@pytest.mark.django_db
class TestPatchParties:
    def _setup(self):
        acct = _account()
        agreement = _agreement(acct)
        PartyService.set_parties(
            agreement_id=agreement.pk,
            initiator_account=acct,
            parties_data=_parties(acct.phone),
        )
        return acct, agreement

    def test_updates_phone(self):
        acct, agreement = self._setup()
        PartyService.patch_parties(
            agreement_id=agreement.pk,
            initiator_account=acct,
            parties_data=[{"role": "buyer", "phone": "+233300000099"}],
        )
        assert Party.objects.get(agreement=agreement, role="buyer").phone == "+233300000099"

    def test_updates_only_supplied_fields(self):
        acct, agreement = self._setup()
        original_name = Party.objects.get(agreement=agreement, role="buyer").display_name
        PartyService.patch_parties(
            agreement_id=agreement.pk,
            initiator_account=acct,
            parties_data=[{"role": "buyer", "id_number": "GHA-UPDATED"}],
        )
        buyer = Party.objects.get(agreement=agreement, role="buyer")
        assert buyer.display_name == original_name  # untouched
        assert buyer.id_number == "GHA-UPDATED"

    def test_raises_for_unknown_role(self):
        acct, agreement = self._setup()
        with pytest.raises(DomainError, match="witness"):
            PartyService.patch_parties(
                agreement_id=agreement.pk,
                initiator_account=acct,
                parties_data=[{"role": "witness", "full_name": "No One"}],
            )

    def test_raises_when_sealed(self):
        acct = _account()
        agreement = _agreement(acct, status=AgreementStatus.SEALED)
        with pytest.raises(DomainError, match="sealed"):
            PartyService.patch_parties(
                agreement_id=agreement.pk,
                initiator_account=acct,
                parties_data=[{"role": "buyer", "phone": "+233300000099"}],
            )

    def test_emits_audit_event(self):
        acct, agreement = self._setup()
        PartyService.patch_parties(
            agreement_id=agreement.pk,
            initiator_account=acct,
            parties_data=[{"role": "buyer", "phone": "+233300000099"}],
        )
        assert AuditLog.objects.filter(
            event_type="agreement.parties_patched",
            entity_id=str(agreement.pk),
        ).exists()
