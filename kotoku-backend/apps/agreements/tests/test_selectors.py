import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import Account
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.agreements.selectors import AgreementSelector
from apps.evidence.models import EvidenceItem
from apps.identity.models import IdentityRecord
from apps.parties.models import Party

_counter = 0


def _unique_email():
    global _counter
    _counter += 1
    return f"sel{_counter}@test.com"


def _account():
    return Account.objects.create(email=_unique_email())


def _agreement(title="T", created_by=None, status=AgreementStatus.DRAFT):
    return Agreement.objects.create(
        title=title,
        created_by=created_by or _account(),
        status=status,
    )


def _identity(account, ref="ref-sel"):
    return IdentityRecord.objects.create(
        account=account,
        reference=ref,
        verification_type="ghana_card",
    )


class TestListAgreements:
    def test_returns_all_agreements(self, db):
        _agreement("A1")
        _agreement("A2")
        result = AgreementSelector.list_agreements()
        assert result.count() == 2

    def test_filters_by_account(self, db):
        owner = _account()
        _agreement("Mine", created_by=owner)
        _agreement("Other")
        result = AgreementSelector.list_agreements(account_id=owner.pk)
        assert result.count() == 1
        assert result.first().title == "Mine"

    def test_filters_by_status(self, db):
        _agreement("Draft", status=AgreementStatus.DRAFT)
        _agreement("Active", status=AgreementStatus.ACTIVE)
        result = AgreementSelector.list_agreements(status=AgreementStatus.ACTIVE)
        assert result.count() == 1
        assert result.first().title == "Active"

    def test_filters_by_account_and_status(self, db):
        owner = _account()
        _agreement("T1", created_by=owner, status=AgreementStatus.DRAFT)
        _agreement("T2", created_by=owner, status=AgreementStatus.ACTIVE)
        result = AgreementSelector.list_agreements(
            account_id=owner.pk, status=AgreementStatus.ACTIVE
        )
        assert result.count() == 1

    def test_selects_related_created_by(self, db):
        _agreement("T")
        with CaptureQueriesContext(connection) as ctx:
            list(AgreementSelector.list_agreements())
        assert len(ctx.captured_queries) == 1


class TestGetAgreementDetail:
    def test_returns_agreement_with_prefetched_relations(self, db):
        owner = _account()
        agreement = _agreement("Detail", created_by=owner)
        identity = _identity(owner)
        party = Party.objects.create(
            agreement=agreement,
            identity=identity,
            role=Party.Role.BUYER,
            display_name="Buyer",
        )
        EvidenceItem.objects.create(
            agreement=agreement,
            uploaded_by=party,
            file_type=EvidenceItem.FileType.PHOTO,
            file_hash="hash123",
        )
        with CaptureQueriesContext(connection) as ctx:
            detail = AgreementSelector.get_agreement_detail(agreement.pk)
            list(detail.parties.all())
            list(detail.evidence_items.all())
        assert len(ctx.captured_queries) == 5

    def test_raises_does_not_exist_for_missing(self, db):
        with pytest.raises(Agreement.DoesNotExist):
            AgreementSelector.get_agreement_detail(999999)


class TestListPartyAgreements:
    def test_returns_agreements_where_party_exists(self, db):
        owner = _account()
        a1 = _agreement("A1", created_by=owner)
        _agreement("A2", created_by=owner)
        identity = _identity(owner)
        party = Party.objects.create(
            agreement=a1,
            identity=identity,
            role=Party.Role.BUYER,
            display_name="Buyer",
        )
        result = AgreementSelector.list_party_agreements(party.pk)
        assert result.count() == 1
        assert result.first().title == "A1"

    def test_returns_distinct_for_multiple_parties(self, db):
        owner = _account()
        agreement = _agreement("Multi", created_by=owner)
        id1 = _identity(owner, "r1")
        id2 = IdentityRecord.objects.create(
            account=owner, reference="r2", verification_type="phone"
        )
        p1 = Party.objects.create(
            agreement=agreement, identity=id1, role=Party.Role.BUYER, display_name="B"
        )
        Party.objects.create(
            agreement=agreement, identity=id2, role=Party.Role.SELLER, display_name="S"
        )
        result = AgreementSelector.list_party_agreements(p1.pk)
        assert result.count() == 1
