import pytest
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.disputes.models import Dispute
from apps.disputes.services import DisputeService
from apps.parties.models import Party
from common.exceptions import DomainError


def _make_sealed_agreement():
    user = User.objects.create_user(phone=f"+23353{Agreement.objects.count():07d}")
    account = Account.objects.create(user=user, email=f"u{user.pk}@test.com", phone=user.phone)
    agreement = Agreement.objects.create(
        title="Test Agreement",
        scenario_template="used_vehicle_sale",
        status=AgreementStatus.SEALED,
        created_by=account,
        sealed_at=timezone.now(),
        seal_hash="abc123",
    )
    party = Party.objects.create(
        agreement=agreement,
        display_name="Seller",
        phone=user.phone,
        role=Party.Role.SELLER,
    )
    return agreement, party


def _make_dispute(agreement, party, reason="Goods not delivered"):
    return Dispute.objects.create(
        agreement=agreement,
        raised_by=party,
        reason=reason,
    )


@pytest.mark.django_db
class TestDisputeServiceOpenDispute:
    def test_opens_dispute_on_sealed_agreement(self):
        agreement, party = _make_sealed_agreement()
        dispute = DisputeService.open_dispute(
            agreement_id=agreement.pk,
            raised_by_party_id=party.pk,
            reason="Not delivered",
        )
        assert dispute.pk is not None
        assert dispute.status == Dispute.Status.OPEN
        assert dispute.reason == "Not delivered"

    def test_raises_on_draft_agreement(self):
        user = User.objects.create_user(phone="+233530100001")
        account = Account.objects.create(user=user, email="d@test.com", phone=user.phone)
        agreement = Agreement.objects.create(
            title="Draft",
            scenario_template="used_vehicle_sale",
            status=AgreementStatus.DRAFT,
            created_by=account,
        )
        party = Party.objects.create(
            agreement=agreement, display_name="X", phone=user.phone, role=Party.Role.SELLER
        )
        with pytest.raises(DomainError, match="sealed"):
            DisputeService.open_dispute(
                agreement_id=agreement.pk,
                raised_by_party_id=party.pk,
                reason="Reason",
            )

    def test_raises_when_party_not_on_agreement(self):
        agreement, _ = _make_sealed_agreement()
        user2 = User.objects.create_user(phone="+233530100002")
        account2 = Account.objects.create(user=user2, email="x@test.com", phone=user2.phone)
        agreement2 = Agreement.objects.create(
            title="Other",
            scenario_template="used_vehicle_sale",
            status=AgreementStatus.SEALED,
            created_by=account2,
            sealed_at=timezone.now(),
            seal_hash="xyz",
        )
        other_party = Party.objects.create(
            agreement=agreement2, display_name="Other", phone=user2.phone, role=Party.Role.BUYER
        )
        with pytest.raises(DomainError, match="party on this agreement"):
            DisputeService.open_dispute(
                agreement_id=agreement.pk,
                raised_by_party_id=other_party.pk,
                reason="Reason",
            )

    def test_raises_on_empty_reason(self):
        agreement, party = _make_sealed_agreement()
        with pytest.raises(DomainError, match="reason"):
            DisputeService.open_dispute(
                agreement_id=agreement.pk,
                raised_by_party_id=party.pk,
                reason="   ",
            )

    def test_trims_reason(self):
        agreement, party = _make_sealed_agreement()
        dispute = DisputeService.open_dispute(
            agreement_id=agreement.pk,
            raised_by_party_id=party.pk,
            reason="  padded reason  ",
        )
        assert dispute.reason == "padded reason"


@pytest.mark.django_db
class TestDisputeServiceResolveDispute:
    def test_resolves_open_dispute(self):
        agreement, party = _make_sealed_agreement()
        dispute = _make_dispute(agreement, party)
        result = DisputeService.resolve_dispute(dispute=dispute, resolution="Refunded.")
        assert result.status == Dispute.Status.RESOLVED
        assert result.resolution == "Refunded."
        assert result.resolved_at is not None

    def test_raises_on_empty_resolution(self):
        agreement, party = _make_sealed_agreement()
        dispute = _make_dispute(agreement, party)
        with pytest.raises(DomainError, match="resolution"):
            DisputeService.resolve_dispute(dispute=dispute, resolution="")

    def test_raises_if_already_resolved(self):
        agreement, party = _make_sealed_agreement()
        dispute = _make_dispute(agreement, party)
        DisputeService.resolve_dispute(dispute=dispute, resolution="Done.")
        with pytest.raises(DomainError, match="already resolved"):
            DisputeService.resolve_dispute(dispute=dispute, resolution="Again.")


@pytest.mark.django_db
class TestDisputeServiceDismissDispute:
    def test_dismisses_open_dispute(self):
        agreement, party = _make_sealed_agreement()
        dispute = _make_dispute(agreement, party)
        result = DisputeService.dismiss_dispute(dispute=dispute, resolution="No merit.")
        assert result.status == Dispute.Status.DISMISSED

    def test_raises_if_already_dismissed(self):
        agreement, party = _make_sealed_agreement()
        dispute = _make_dispute(agreement, party)
        DisputeService.dismiss_dispute(dispute=dispute, resolution="No merit.")
        with pytest.raises(DomainError):
            DisputeService.dismiss_dispute(dispute=dispute, resolution="Again.")

    def test_uses_default_resolution_when_empty(self):
        agreement, party = _make_sealed_agreement()
        dispute = _make_dispute(agreement, party)
        result = DisputeService.dismiss_dispute(dispute=dispute, resolution="")
        assert "Dismissed" in result.resolution


@pytest.mark.django_db
class TestDisputeServiceMarkInvestigating:
    def test_marks_open_dispute_as_investigating(self):
        agreement, party = _make_sealed_agreement()
        dispute = _make_dispute(agreement, party)
        result = DisputeService.mark_investigating(dispute=dispute)
        assert result.status == Dispute.Status.INVESTIGATING

    def test_raises_if_not_open(self):
        agreement, party = _make_sealed_agreement()
        dispute = _make_dispute(agreement, party)
        DisputeService.mark_investigating(dispute=dispute)
        with pytest.raises(DomainError, match="open disputes"):
            DisputeService.mark_investigating(dispute=dispute)


@pytest.mark.django_db
class TestDisputeServiceGenerateCasePack:
    def test_returns_case_pack_dict(self):
        agreement, party = _make_sealed_agreement()
        dispute = _make_dispute(agreement, party)
        case_pack = DisputeService.generate_case_pack(dispute=dispute)
        assert case_pack["dispute_id"] == dispute.pk
        assert case_pack["agreement"]["id"] == agreement.pk
        assert "parties" in case_pack
        assert case_pack["dispute"]["reason"] == "Goods not delivered"
        assert "generated_at" in case_pack
