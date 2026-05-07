from django.db.models import Q

from apps.agreements.models import Agreement


class AgreementSelector:
    @staticmethod
    def list_agreements(*, account_id=None, account_phone=None, status=None):
        qs = Agreement.objects.select_related("created_by").order_by("-created_at")
        if account_id is not None and account_phone is not None:
            qs = qs.filter(
                Q(created_by_id=account_id) | Q(parties__phone=account_phone)
            ).distinct()
        elif account_id is not None:
            qs = qs.filter(created_by_id=account_id)
        if status is not None:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_agreement_detail(
        agreement_id: int, *, account_id: int = None, account_phone: str = None
    ) -> Agreement:
        qs = Agreement.objects.prefetch_related(
            "parties__identity",
            "evidence_items",
            "consent_records",
        ).select_related("created_by")
        if account_id is not None and account_phone is not None:
            qs = qs.filter(
                Q(created_by_id=account_id) | Q(parties__phone=account_phone)
            )
        elif account_id is not None:
            qs = qs.filter(created_by_id=account_id)
        return qs.distinct().get(pk=agreement_id)

    @staticmethod
    def list_party_agreements(party_id: int):
        return (
            Agreement.objects.filter(parties__pk=party_id)
            .select_related("created_by")
            .order_by("-created_at")
            .distinct()
        )
