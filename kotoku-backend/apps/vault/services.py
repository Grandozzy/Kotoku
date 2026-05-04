from datetime import timedelta

from django.conf import settings

from apps.audit.services import AuditService
from apps.vault.models import VaultEntry
from apps.vault.tasks import generate_vault_pdf


class VaultService:
    @staticmethod
    def create_entry(agreement, actor) -> VaultEntry:
        vault_entry, created = VaultEntry.objects.get_or_create(
            agreement=agreement,
            defaults={
                "export_status": VaultEntry.ExportStatus.PENDING,
                "sealed_at": agreement.sealed_at,
                "retention_until": agreement.sealed_at
                + timedelta(days=settings.VAULT_FREE_RETENTION_DAYS),
                "is_free_retention": True,
            },
        )
        if created:
            AuditService.record_event(
                event_type="vault.entry_created",
                entity_type="vault_entry",
                entity_id=str(vault_entry.pk),
                actor=str(actor),
            )
            generate_vault_pdf.delay(vault_entry_id=vault_entry.pk)
        return vault_entry

    @staticmethod
    def trigger_export(vault_entry_id: int, actor) -> dict:
        vault_entry = VaultEntry.objects.get(pk=vault_entry_id)

        if vault_entry.export_status == VaultEntry.ExportStatus.COMPLETED:
            return {"status": "completed", "pdf_storage_key": vault_entry.pdf_storage_key}

        if vault_entry.export_status == VaultEntry.ExportStatus.FAILED:
            vault_entry.export_status = VaultEntry.ExportStatus.PENDING
            vault_entry.retry_count += 1
            vault_entry.pdf_storage_key = ""
            vault_entry.save(
                update_fields=["export_status", "retry_count", "pdf_storage_key"]
            )
            AuditService.record_event(
                event_type="vault.export_retried",
                entity_type="vault_entry",
                entity_id=str(vault_entry.pk),
                actor=str(actor),
                metadata={"retry_count": vault_entry.retry_count},
            )
            generate_vault_pdf.delay(vault_entry_id=vault_entry.pk)
            return {"status": "pending"}

        return {"status": vault_entry.export_status}
