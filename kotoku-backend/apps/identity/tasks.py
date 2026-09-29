import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.identity.services import IdentityService
from common.exceptions import ServiceUnavailableError

logger = logging.getLogger("kotoku")


@shared_task(
    bind=True,
    autoretry_for=(ServiceUnavailableError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
    name="apps.identity.tasks.verify_party_identity",
)
def verify_party_identity(self, party_id: int):
    logger.info("[IDENTITY] verify_party_identity task started party_id=%s", party_id)
    result = IdentityService.verify_party_identity(
        party_id=party_id,
        soft_fail_unavailable=False,
    )
    logger.info(
        "[IDENTITY] verify_party_identity task finished party_id=%s status=%s failure_codes=%s",
        party_id,
        result.status,
        list(result.failure_codes),
    )
    return result


@shared_task(name="apps.identity.tasks.cleanup_expired_liveness_references")
def cleanup_expired_liveness_references() -> dict[str, int]:
    from apps.audit.services import AuditService
    from apps.identity.models import PartyIdentityVerification
    from infrastructure.storage.s3 import S3StorageClient

    expired_ids = PartyIdentityVerification.objects.filter(
        liveness_reference_s3_key__gt="",
        liveness_reference_delete_after__lte=timezone.now(),
    ).values_list("id", flat=True)
    storage = S3StorageClient()
    deleted = 0
    for verification_id in expired_ids.iterator():
        with transaction.atomic():
            verification = PartyIdentityVerification.objects.select_for_update().get(
                pk=verification_id
            )
            if (
                not verification.liveness_reference_s3_key
                or not verification.liveness_reference_delete_after
                or verification.liveness_reference_delete_after > timezone.now()
            ):
                continue
            try:
                storage.delete_object(verification.liveness_reference_s3_key)
            except Exception:
                logger.exception(
                    "[IDENTITY] liveness_reference_cleanup_failed verification_id=%s",
                    verification.pk,
                )
                continue
            verification.liveness_reference_s3_key = ""
            verification.liveness_reference_delete_after = None
            verification.save(
                update_fields=[
                    "liveness_reference_s3_key",
                    "liveness_reference_delete_after",
                    "updated_at",
                ]
            )
            AuditService.record_event(
                event_type="identity.liveness_reference_deleted",
                entity_type="party_identity_verification",
                entity_id=str(verification.pk),
                metadata={"reason": "retention_expired"},
            )
            deleted += 1
    logger.info("[IDENTITY] liveness_reference_cleanup deleted=%s", deleted)
    return {"deleted": deleted}
