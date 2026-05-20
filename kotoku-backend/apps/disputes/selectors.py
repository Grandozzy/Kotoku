from django.db.models import QuerySet

from django.db.models import Q

from apps.agreements.domain.enums import AgreementStatus
from apps.disputes.models import Dispute

_PARTICIPANT_VISIBLE_DISPUTE_STATUSES = (
    AgreementStatus.SEALED,
    AgreementStatus.CLOSED,
    AgreementStatus.REOPEN_REQUESTED,
    AgreementStatus.ARCHIVED,
)


class DisputeSelector:
    @staticmethod
    def list_for_agreement(*, agreement_id: int) -> QuerySet:
        return (
            Dispute.objects.filter(agreement_id=agreement_id)
            .select_related("raised_by")
            .order_by("-created_at")
        )

    @staticmethod
    def list_for_account(*, account_id: int, account_phone: str | None = None) -> QuerySet:
        owner_q = Q(agreement__created_by_id=account_id)
        if account_phone:
            party_q = Q(agreement__parties__phone=account_phone) & Q(
                agreement__status__in=_PARTICIPANT_VISIBLE_DISPUTE_STATUSES
            )
            visibility_q = owner_q | party_q
        else:
            visibility_q = owner_q
        return (
            Dispute.objects.filter(visibility_q)
            .select_related("raised_by", "agreement")
            .order_by("-created_at")
            .distinct()
        )

    @staticmethod
    def get(*, dispute_id: int, agreement_id: int) -> Dispute:
        return Dispute.objects.select_related("raised_by", "agreement").get(
            pk=dispute_id, agreement_id=agreement_id
        )
