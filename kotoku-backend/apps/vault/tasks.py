import logging
import uuid

from celery import shared_task

from apps.audit.services import AuditService
from apps.vault.models import VaultEntry
from apps.vault.pdf import render_vault_pdf
from apps.vault.snapshot import build_export_snapshot
from infrastructure.storage.s3 import S3StorageClient

logger = logging.getLogger(__name__)


@shared_task
def generate_vault_pdf(vault_entry_id: int) -> None:
    try:
        vault_entry = VaultEntry.objects.select_related("agreement").get(
            pk=vault_entry_id
        )
    except VaultEntry.DoesNotExist:
        logger.warning("VaultEntry %s not found", vault_entry_id)
        return

    vault_entry.export_status = VaultEntry.ExportStatus.PROCESSING
    vault_entry.save(update_fields=["export_status"])

    try:
        snapshot = build_export_snapshot(vault_entry.agreement_id)
        pdf_bytes = render_vault_pdf(snapshot)
        storage_key = f"vault/{vault_entry.agreement_id}/{uuid.uuid4()}.pdf"
        storage = S3StorageClient()
        storage.upload(storage_key, pdf_bytes, content_type="application/pdf")
        vault_entry.export_status = VaultEntry.ExportStatus.COMPLETED
        vault_entry.pdf_storage_key = storage_key
        vault_entry.save(update_fields=["export_status", "pdf_storage_key"])
        AuditService.record_event(
            event_type="vault.export_generated",
            entity_type="vault_entry",
            entity_id=str(vault_entry.pk),
            metadata={
                "pdf_storage_key": storage_key,
                "snapshot_hash": snapshot.get("snapshot_hash", ""),
            },
        )
    except Exception:
        logger.exception("Failed to generate PDF for VaultEntry %s", vault_entry_id)
        vault_entry.export_status = VaultEntry.ExportStatus.FAILED
        vault_entry.save(update_fields=["export_status"])
        AuditService.record_event(
            event_type="vault.export_failed",
            entity_type="vault_entry",
            entity_id=str(vault_entry.pk),
            metadata={"error": "PDF generation failed"},
        )
        raise
