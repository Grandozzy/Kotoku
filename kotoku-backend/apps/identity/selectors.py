class IdentitySelector:
    @staticmethod
    def list_for_account(account_id: int):
        from apps.identity.models import IdentityRecord

        return IdentityRecord.objects.filter(account_id=account_id).order_by("-created_at")

    @staticmethod
    def get_for_account(*, identity_id: int, account_id: int):
        from apps.identity.models import IdentityRecord

        return IdentityRecord.objects.get(pk=identity_id, account_id=account_id)

    @staticmethod
    def get_verified_for_reference(reference: str):
        from apps.identity.models import IdentityRecord

        return IdentityRecord.objects.get(reference=reference, verified_at__isnull=False)
