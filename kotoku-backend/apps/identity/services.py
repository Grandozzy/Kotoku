class IdentityService:
    @staticmethod
    def create_identity_record(*, account, reference: str, verification_type: str):
        from apps.identity.models import IdentityRecord

        reference = reference.strip()
        if not reference:
            raise ValueError("Identity reference cannot be empty.")
        return IdentityRecord.objects.create(
            account=account,
            reference=reference,
            verification_type=verification_type,
        )

    @staticmethod
    def mark_verified(*, identity_record):
        from django.utils import timezone

        identity_record.verified_at = timezone.now()
        identity_record.save(update_fields=["verified_at"])
        return identity_record
