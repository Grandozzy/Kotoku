from apps.vault.models import VaultEntry


class VaultSelector:
    @staticmethod
    def list_entries(account_id, export_status=None, archived=False):
        qs = (
            VaultEntry.objects.select_related("agreement")
            .filter(agreement__created_by_id=account_id)
            .order_by("-sealed_at")
        )
        if not archived:
            qs = qs.filter(archived=False)
        if export_status:
            qs = qs.filter(export_status=export_status)
        return qs

    @staticmethod
    def get_detail(agreement_id: int, account_id: int) -> VaultEntry:
        return (
            VaultEntry.objects.select_related("agreement")
            .prefetch_related(
                "agreement__parties",
                "agreement__evidence_items",
                "agreement__consent_records",
            )
            .get(agreement_id=agreement_id, agreement__created_by_id=account_id)
        )
