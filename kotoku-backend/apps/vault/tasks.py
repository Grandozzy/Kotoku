import logging
from hashlib import sha256
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=120,
    soft_time_limit=90,
)
def generate_pdf_export(self, vault_entry_id: int) -> None:
    from apps.vault.models import VaultEntry
    from apps.vault.pdf import render_vault_pdf
    from apps.vault.services import VaultService
    from infrastructure.storage.s3 import S3StorageClient

    try:
        entry = VaultEntry.objects.select_related("agreement").get(pk=vault_entry_id)
        agreement_id = entry.agreement_id

        VaultService._push_vault_event(
            agreement_id=agreement_id,
            event_type="vault.pdf_generating",
        )

        pdf_bytes = render_vault_pdf(vault_entry_id)
        pdf_sha256 = sha256(pdf_bytes).hexdigest()
        key = f"exports/agreement-{entry.agreement_id}-vault-{vault_entry_id}.pdf"
        storage = S3StorageClient()
        pdf_url = storage.upload(
            key,
            pdf_bytes,
            content_type="application/pdf",
            checksum_sha256=pdf_sha256,
        )
        object_meta = storage.head_object(key)
        if object_meta.get("content_length") != len(pdf_bytes):
            raise RuntimeError(
                f"Uploaded PDF size mismatch for vault_entry={vault_entry_id}"
            )
        if object_meta.get("content_type") != "application/pdf":
            raise RuntimeError(
                f"Uploaded PDF content type mismatch for vault_entry={vault_entry_id}"
            )
        stored_checksum = object_meta.get("metadata", {}).get("sha256", "")
        if stored_checksum != pdf_sha256:
            raise RuntimeError(
                f"Uploaded PDF checksum mismatch for vault_entry={vault_entry_id}"
            )

        VaultService.mark_pdf_ready(vault_entry_id=vault_entry_id, pdf_key=key, pdf_url=pdf_url)
        VaultService._push_vault_event(
            agreement_id=agreement_id,
            event_type="vault.pdf_ready",
            payload={"agreement_id": agreement_id},
        )
        logger.info("PDF generated for vault_entry=%s key=%s", vault_entry_id, key)
    except Exception as exc:
        # Stay GENERATING while retries remain — on_failure handles the terminal failure.
        logger.warning(
            "PDF generation attempt %d/%d failed for vault_entry=%s: %s",
            self.request.retries + 1,
            self.max_retries + 1,
            vault_entry_id,
            exc,
        )
        raise self.retry(exc=exc) from None


def _on_generate_pdf_failure(exc, task_id, args, kwargs, einfo):
    vault_entry_id = args[0] if args else None
    if vault_entry_id is None:
        return
    try:
        from apps.vault.models import VaultEntry
        from apps.vault.services import VaultService

        VaultService.mark_pdf_failed(vault_entry_id=vault_entry_id)
        entry = VaultEntry.objects.select_related("agreement").get(pk=vault_entry_id)
        VaultService._push_vault_event(
            agreement_id=entry.agreement_id,
            event_type="vault.pdf_failed",
        )
    except Exception:
        logger.exception("on_failure: could not process vault_entry=%s", vault_entry_id)


generate_pdf_export.on_failure = _on_generate_pdf_failure


@shared_task
def recover_stuck_pdf_generating() -> dict:
    from apps.vault.models import VaultEntry
    from apps.vault.services import VaultService

    cutoff = timezone.now() - timedelta(minutes=5)
    stuck = VaultEntry.objects.filter(
        pdf_status=VaultEntry.PdfStatus.GENERATING,
        updated_at__lt=cutoff,
    )
    entry_ids = list(stuck.values_list("pk", flat=True))

    if not entry_ids:
        return {"recovered": 0}

    recovered = 0
    for entry_id in entry_ids:
        if VaultService.recover_stuck_export(vault_entry_id=entry_id):
            recovered += 1

    logger.info("recover_stuck_pdf_generating: re-enqueued %d entries", recovered)
    return {"recovered": recovered}


@shared_task
def archive_expired_vault_entries() -> dict:
    """Archive vault entries whose retain_until date has passed.

    Sets archived=True on VaultEntry rows where retain_until < now and
    archived=False. Returns a summary dict for observability.
    Scheduled daily via CELERY_BEAT_SCHEDULE.
    """
    from apps.audit.services import AuditService  # noqa: PLC0415
    from apps.vault.models import VaultEntry  # noqa: PLC0415

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
