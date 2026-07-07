import logging

from django.conf import settings
from django.core import signing
from django.db import transaction

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.audit.services import AuditService
from apps.evidence.models import EvidenceItem
from apps.notifications.push import send_to_user
from apps.parties.models import Party
from apps.vault.models import VaultEntry
from common.exceptions import DomainError
from infrastructure.storage.s3 import S3StorageClient

logger = logging.getLogger(__name__)
_SEALED_RECEIPT_LINK_SALT = "kotoku.sealed-receipt-link.v1"


def _public_evidence_payload(item: EvidenceItem) -> dict:
    view_url = None
    if item.file_key:
        try:
            view_url = S3StorageClient().generate_presigned_view_url(
                item.file_key,
                content_type=item.mime_type,
                expires_in=settings.EVIDENCE_VIEW_URL_TTL_SECONDS,
            )
        except Exception:
            logger.exception(
                "Failed to generate sealed receipt evidence view URL",
                extra={"evidence_id": item.pk, "agreement_id": item.agreement_id},
            )

    return {
        "id": item.pk,
        "evidence_type": item.evidence_type,
        "file_type": item.file_type,
        "mime_type": item.mime_type,
        "size_bytes": item.size_bytes,
        "original_name": item.original_name,
        "upload_status": item.upload_status,
        "uploaded_by_role": item.uploaded_by.role if item.uploaded_by_id else None,
        "created_at": item.created_at,
        "view_url": view_url,
    }


class VaultService:
    @staticmethod
    def _enqueue_pdf_export(vault_entry_id: int) -> None:
        from apps.vault.tasks import generate_pdf_export  # noqa: PLC0415

        generate_pdf_export.delay(vault_entry_id)

    @staticmethod
    def _set_generating_and_enqueue(
        *,
        entry: VaultEntry,
        audit_event_type: str,
        audit_metadata: dict | None = None,
    ) -> VaultEntry:
        entry.pdf_status = VaultEntry.PdfStatus.GENERATING
        entry.pdf_key = ""
        entry.pdf_url = ""
        entry.save(update_fields=["pdf_status", "pdf_key", "pdf_url", "updated_at"])
        VaultService._enqueue_pdf_export(entry.pk)
        AuditService.record_event(
            event_type=audit_event_type,
            entity_type="vault_entry",
            entity_id=str(entry.pk),
            metadata=audit_metadata or {"agreement_id": entry.agreement_id},
        )
        return entry

    @staticmethod
    def make_sealed_receipt_token(*, agreement_id: int, party_id: int) -> str:
        return signing.dumps(
            {"agreement_id": agreement_id, "party_id": party_id},
            salt=_SEALED_RECEIPT_LINK_SALT,
        )

    @staticmethod
    def load_sealed_receipt_token(token: str) -> dict:
        try:
            payload = signing.loads(
                token,
                salt=_SEALED_RECEIPT_LINK_SALT,
                max_age=settings.SEALED_RECEIPT_LINK_MAX_AGE_SECONDS,
            )
        except signing.BadSignature:
            raise DomainError("Invalid or expired sealed receipt link.") from None
        if not isinstance(payload, dict):
            raise DomainError("Invalid or expired sealed receipt link.")
        return payload

    @staticmethod
    def get_public_receipt_context(*, token: str) -> dict:
        payload = VaultService.load_sealed_receipt_token(token)
        agreement_id = int(payload.get("agreement_id") or 0)
        party_id = int(payload.get("party_id") or 0)

        try:
            entry = (
                VaultEntry.objects.select_related("agreement", "agreement__created_by")
                .get(agreement_id=agreement_id)
            )
            party = Party.objects.get(pk=party_id, agreement_id=agreement_id)
        except (VaultEntry.DoesNotExist, Party.DoesNotExist):
            raise DomainError("Invalid or expired sealed receipt link.") from None

        agreement = entry.agreement
        if agreement.status not in (
            AgreementStatus.SEALED,
            AgreementStatus.REOPEN_REQUESTED,
            AgreementStatus.ACTIVE,
            AgreementStatus.CLOSED,
        ):
            raise DomainError("This sealed receipt is not available.")

        parties = list(Party.objects.filter(agreement=agreement).order_by("id"))
        evidence = [
            _public_evidence_payload(item)
            for item in EvidenceItem.objects.filter(
                agreement=agreement,
                upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            )
            .select_related("uploaded_by")
            .order_by("-created_at")
        ]

        return {
            "vault_entry": entry,
            "agreement": agreement,
            "party": party,
            "parties": parties,
            "evidence": evidence,
        }

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

        return VaultService._set_generating_and_enqueue(
            entry=entry,
            audit_event_type="vault.export_requested",
            audit_metadata={"agreement_id": agreement_id},
        )

    @staticmethod
    @transaction.atomic
    def mark_pdf_ready(*, vault_entry_id: int, pdf_key: str, pdf_url: str = "") -> VaultEntry:
        entry = VaultEntry.objects.select_for_update().get(pk=vault_entry_id)
        entry.pdf_key = pdf_key
        entry.pdf_url = pdf_url
        entry.pdf_status = VaultEntry.PdfStatus.READY
        entry.save(update_fields=["pdf_key", "pdf_url", "pdf_status", "updated_at"])
        AuditService.record_event(
            event_type="vault.export_ready",
            entity_type="vault_entry",
            entity_id=str(entry.pk),
            metadata={"pdf_key": pdf_key},
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

        return VaultService._set_generating_and_enqueue(
            entry=entry,
            audit_event_type="vault.export_retry_requested",
            audit_metadata={"agreement_id": agreement_id},
        )

    @staticmethod
    @transaction.atomic
    def recover_stuck_export(*, vault_entry_id: int) -> bool:
        try:
            entry = VaultEntry.objects.select_for_update().get(pk=vault_entry_id)
        except VaultEntry.DoesNotExist:
            return False

        if entry.pdf_status != VaultEntry.PdfStatus.GENERATING:
            return False

        entry.save(update_fields=["updated_at"])
        VaultService._enqueue_pdf_export(entry.pk)
        AuditService.record_event(
            event_type="vault.export_recovered",
            entity_type="vault_entry",
            entity_id=str(entry.pk),
            metadata={"agreement_id": entry.agreement_id},
        )
        return True

    @staticmethod
    def _push_vault_event(*, agreement_id: int, event_type: str, payload: dict | None = None):
        parties = Party.objects.filter(agreement_id=agreement_id)
        for p in parties:
            if p.phone:
                send_to_user(p.phone, event_type, payload or {"agreement_id": agreement_id})
