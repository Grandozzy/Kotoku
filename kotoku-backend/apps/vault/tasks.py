import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_pdf_export(self, vault_entry_id: int) -> None:
    """Generate a PDF for a sealed agreement and store it in object storage.

    On success  → calls VaultService.mark_pdf_ready with the storage URL.
    On failure  → calls VaultService.mark_pdf_failed, then retries up to 3 times.
    """
    from apps.vault.models import VaultEntry  # noqa: PLC0415
    from apps.vault.pdf import render_vault_pdf  # noqa: PLC0415
    from apps.vault.services import VaultService  # noqa: PLC0415
    from infrastructure.storage.s3 import S3StorageClient  # noqa: PLC0415

    try:
        entry = VaultEntry.objects.select_related("agreement").get(pk=vault_entry_id)
        pdf_bytes = render_vault_pdf(vault_entry_id)
        key = f"exports/agreement-{entry.agreement_id}-vault-{vault_entry_id}.pdf"
        pdf_url = S3StorageClient().upload(key, pdf_bytes, content_type="application/pdf")
        VaultService.mark_pdf_ready(vault_entry_id=vault_entry_id, pdf_url=pdf_url)
        logger.info("PDF generated for vault_entry=%s → %s", vault_entry_id, pdf_url)
    except Exception as exc:
        logger.exception("PDF generation failed for vault_entry=%s", vault_entry_id)
        try:
            VaultService.mark_pdf_failed(vault_entry_id=vault_entry_id)
        except Exception:
            logger.exception(
                "Could not mark vault_entry=%s as failed", vault_entry_id
            )
        raise self.retry(exc=exc)


@shared_task
def archive_expired_vault_entries() -> dict:
    """Archive vault entries whose retain_until date has passed.

    Sets archived=True on VaultEntry rows where retain_until < now and
    archived=False. Returns a summary dict for observability.
    Scheduled daily via CELERY_BEAT_SCHEDULE.
    """
    from apps.vault.models import VaultEntry  # noqa: PLC0415
    from apps.audit.services import AuditService  # noqa: PLC0415

    now = timezone.now()
    expired_qs = VaultEntry.objects.filter(retain_until__lt=now, archived=False)
    entry_ids = list(expired_qs.values_list("pk", flat=True))

    if not entry_ids:
        logger.info("archive_expired_vault_entries: nothing to archive")
        return {"archived": 0}

    expired_qs.update(archived=True)

    for entry_id in entry_ids:
        AuditService.record_event(
            event_type="vault.entry_archived",
            entity_type="vault_entry",
            entity_id=str(entry_id),
            metadata={"reason": "retention_expired"},
        )

    logger.info("archive_expired_vault_entries: archived %d entries", len(entry_ids))
    return {"archived": len(entry_ids)}
