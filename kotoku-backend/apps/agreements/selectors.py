from apps.agreements.models import Agreement


class AgreementSelector:
    @staticmethod
    def list_agreements(*, account_id=None, status=None):
        qs = Agreement.objects.select_related("created_by").order_by("-created_at")
        if account_id is not None:
            qs = qs.filter(created_by_id=account_id)
        if status is not None:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_agreement_detail(agreement_id: int) -> Agreement:
        return Agreement.objects.prefetch_related(
            "parties__identity",
            "evidence_items",
            "consent_records",
        ).select_related("created_by").get(pk=agreement_id)

    @staticmethod
    def list_party_agreements(party_id: int):
        return (
            Agreement.objects.filter(parties__pk=party_id)
            .select_related("created_by")
            .order_by("-created_at")
            .distinct()
        )
