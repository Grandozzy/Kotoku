from apps.audit.services import AuditService
from apps.accounts.models import Account


class AccountService:
    """Writes for the accounts domain belong here, not in views."""

    @staticmethod
    def create_account(
        *,
        email: str,
        full_name: str = "",
        phone: str = "",
        actor: str = "system",
    ) -> Account:
        account = Account.objects.create(email=email, full_name=full_name, phone=phone)
        AuditService.record_event(
            event_type="account.created",
            entity_type="account",
            entity_id=str(account.pk),
            actor=actor,
            metadata={"email": email, "full_name": full_name, "phone": phone},
        )
        return account
