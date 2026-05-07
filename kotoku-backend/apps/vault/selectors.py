from django.db.models import Q, QuerySet

from apps.vault.models import VaultEntry


class VaultSelector:
    @staticmethod
    def get_for_agreement(
        *, agreement_id: int, account_id: int, account_phone: str = None
    ) -> VaultEntry:
        qs = VaultEntry.objects.select_related(
            "agreement", "agreement__created_by"
        ).filter(agreement_id=agreement_id)
        if account_phone:
            qs = qs.filter(
                Q(agreement__created_by__pk=account_id)
                | Q(agreement__parties__phone=account_phone)
            )
        else:
            qs = qs.filter(agreement__created_by__pk=account_id)
        return qs.distinct().get()

    @staticmethod
    def list_for_account(*, account_id: int, account_phone: str = None) -> QuerySet:
        qs = VaultEntry.objects
        if account_phone:
            qs = qs.filter(
                Q(agreement__created_by__pk=account_id)
                | Q(agreement__parties__phone=account_phone)
            )
        else:
            qs = qs.filter(agreement__created_by__pk=account_id)
        return (
            qs.filter(archived=False)
            .select_related("agreement", "agreement__created_by")
            .order_by("-created_at")
            .distinct()
        )
