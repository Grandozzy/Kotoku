from apps.accounts.models import Account


class AccountSelector:
    """Reads for the accounts domain belong here, not in views."""

    @staticmethod
    def list_accounts():
        return Account.objects.order_by("id")
