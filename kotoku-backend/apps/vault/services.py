import logging

from django.db import transaction

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.agreements.models import Party
from apps.audit.services import AuditService
from apps.notifications.push import send_to_user
from apps.vault.models import VaultEntry
from common.exceptions import DomainError

logger = logging.getLogger(__name__)


class VaultService:
    @staticmethod
    def create_for_agreement(*, agreement_id: int) -> VaultEntry:
        """Create a VaultEntry immediately after an agreement is sealed.

        Idempotent: returns the existing entry if one already exists.
        """
        agreement = Agreement.objects.get(pk=agreement_id)
        if agreement.status != AgreementStatus.SEALED:
            raise DomainError("Vault entries can only be created for sealed agreements.")

        entry, created = VaultEntry.objects.get_or_create(
            agreement=agreement,
            defaults={"retain_until": VaultEntry.default_retain_until()},
        )
        if created:
            AuditService.record_event(
                event_type="vault.entry_created",
                entity_type="vault_entry",
                entity_id=str(entry.pk),
                metadata={"agreement_id": agreement_id},
            )
        return entry

    @staticmethod
    @transaction.atomic
    def request_export(*, agreement_id: int) -> VaultEntry:
        """Transition entry to GENERATING and enqueue the PDF Celery task."""
        try:
            entry = VaultEntry.objects.select_for_update().get(agreement_id=agreement_id)
        except VaultEntry.DoesNotExist:
            raise DomainError("No vault entry found for this agreement.") from None

        if entry.pdf_status == VaultEntry.PdfStatus.GENERATING:
            raise DomainError("PDF generation is already in progress.")

        entry.pdf_status = VaultEntry.PdfStatus.GENERATING
        entry.save(update_fields=["pdf_status", "updated_at"])

        from apps.vault.tasks import generate_pdf_export  # noqa: PLC0415
        generate_pdf_export.delay(entry.pk)

        AuditService.record_event(
            event_type="vault.export_requested",
            entity_type="vault_entry",
            entity_id=str(entry.pk),
            metadata={"agreement_id": agreement_id},
        )
        return entry

    @staticmethod
    @transaction.atomic
    def mark_pdf_ready(*, vault_entry_id: int, pdf_url: str) -> VaultEntry:
        entry = VaultEntry.objects.select_for_update().get(pk=vault_entry_id)
        entry.pdf_url = pdf_url
        entry.pdf_status = VaultEntry.PdfStatus.READY
        entry.save(update_fields=["pdf_url", "pdf_status", "updated_at"])
        AuditService.record_event(
            event_type="vault.export_ready",
            entity_type="vault_entry",
            entity_id=str(entry.pk),
            metadata={"pdf_url": pdf_url},
        )
        return entry

    @staticmethod
    @transaction.atomic
    def mark_pdf_failed(*, vault_entry_id: int) -> VaultEntry:
        entry = VaultEntry.objects.select_for_update().get(pk=vault_entry_id)
        entry.pdf_status = VaultEntry.PdfStatus.FAILED
        entry.save(update_fields=["pdf_status", "updated_at"])
        AuditService.record_event(
            event_type="vault.export_failed",
            entity_type="vault_entry",
            entity_id=str(entry.pk),
        )
        return entry

    @staticmethod
    @transaction.atomic
    def retry_export(*, agreement_id: int) -> VaultEntry:
        try:
            entry = VaultEntry.objects.select_for_update().get(agreement_id=agreement_id)
        except VaultEntry.DoesNotExist:
            raise DomainError("No vault entry found for this agreement.") from None

        if entry.pdf_status != VaultEntry.PdfStatus.FAILED:
            raise DomainError("Can only retry failed PDF generation.")

        entry.pdf_status = VaultEntry.PdfStatus.PENDING
        entry.save(update_fields=["pdf_status", "updated_at"])

        from apps.vault.tasks import generate_pdf_export  # noqa: PLC0415
        generate_pdf_export.delay(entry.pk)

        AuditService.record_event(
            event_type="vault.export_retry_requested",
            entity_type="vault_entry",
            entity_id=str(entry.pk),
            metadata={"agreement_id": agreement_id},
        )
        return entry

    @staticmethod
    def _push_vault_event(*, agreement_id: int, event_type: str, payload: dict | None = None):
        parties = Party.objects.filter(agreement_id=agreement_id).select_related("account")
        for p in parties:
            if p.phone:
                send_to_user(p.phone, event_type, payload or {"agreement_id": agreement_id})
