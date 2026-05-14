from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Revoke all active device sessions for a given phone number."

    def add_arguments(self, parser):
        parser.add_argument("phone", type=str, help="E.164 phone number, e.g. +233XXXXXXXXX")
        parser.add_argument(
            "--reason",
            type=str,
            default="admin",
            help="Revocation reason stored on each session (default: admin)",
        )

    def handle(self, *args, **options):
        from apps.accounts.models import DeviceSession, User  # noqa: PLC0415

        phone = options["phone"]
        reason = options["reason"]

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            raise CommandError(f"No user found with phone {phone!r}.")

        updated = DeviceSession.objects.filter(user=user, is_revoked=False).update(
            is_revoked=True,
            revoked_at=timezone.now(),
            revoked_reason=reason,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Revoked {updated} session(s) for {phone} (reason: {reason!r})."
            )
        )
