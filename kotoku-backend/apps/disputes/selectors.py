from django.db.models import QuerySet

from apps.disputes.models import Dispute


class DisputeSelector:
    @staticmethod
    def list_for_agreement(*, agreement_id: int) -> QuerySet:
        return (
            Dispute.objects.filter(agreement_id=agreement_id)
            .select_related("raised_by")
            .order_by("-created_at")
        )

    @staticmethod
    def list_for_account(*, account_id: int) -> QuerySet:
        return (
            Dispute.objects.filter(agreement__created_by_id=account_id)
            .select_related("raised_by", "agreement")
            .order_by("-created_at")
        )

    @staticmethod
    def get(*, dispute_id: int, agreement_id: int) -> Dispute:
        return Dispute.objects.select_related("raised_by", "agreement").get(
            pk=dispute_id, agreement_id=agreement_id
        )
