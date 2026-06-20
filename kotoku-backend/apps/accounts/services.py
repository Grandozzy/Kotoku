from apps.accounts.models import Account, User
from apps.audit.services import AuditService
from common.exceptions import DomainError
from common.phone_numbers import normalize_phone_to_e164


class AccountService:
    """Writes for the accounts domain belong here, not in views."""

    @staticmethod
    def update_profile(
        *,
        account: Account,
        full_name: str | None = None,
        email: str | None = None,
    ) -> Account:
        changed = {}
        if full_name is not None:
            full_name = full_name.strip()
            if len(full_name) > 255:
                raise DomainError("Full name must be 255 characters or fewer.")
            account.full_name = full_name
            changed["full_name"] = full_name
        if email is not None:
            email = email.strip().lower()
            if email and Account.objects.exclude(pk=account.pk).filter(email=email).exists():
                raise DomainError("That email address is already in use.")
            account.email = email
            changed["email"] = email
        if changed:
            account.save(update_fields=list(changed.keys()) + ["updated_at"])
            AuditService.record_event(
                event_type="account.profile_updated",
                entity_type="account",
                entity_id=str(account.pk),
                metadata=changed,
            )
        return account

    @staticmethod
    def create_account(
        *,
        email: str,
        full_name: str = "",
        phone: str = "",
        actor: str = "system",
    ) -> Account:
        phone = normalize_phone_to_e164(phone)
        user = User.objects.create_user(phone=phone or email)
        account = Account.objects.create(
            user=user,
            email=email,
            full_name=full_name,
            phone=phone,
        )
        AuditService.record_event(
            event_type="account.created",
            entity_type="account",
            entity_id=str(account.pk),
            actor=actor,
            metadata={"email": email, "full_name": full_name, "phone": phone},
        )
        return account
