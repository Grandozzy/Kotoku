from django.db.models import QuerySet

from apps.vault.models import VaultEntry


class VaultSelector:
    @staticmethod
    def get_for_agreement(*, agreement_id: int, account_id: int) -> VaultEntry:
        """Fetch a vault entry, scoped to the requesting user's agreements."""
        return VaultEntry.objects.select_related(
            "agreement", "agreement__created_by"
        ).get(
            agreement_id=agreement_id,
            agreement__created_by__pk=account_id,
        )

    @staticmethod
    def list_for_account(*, account_id: int) -> QuerySet:
        return (
            VaultEntry.objects.filter(
                agreement__created_by__pk=account_id,
                archived=False,
            )
            .select_related("agreement")
            .order_by("-created_at")
        )
