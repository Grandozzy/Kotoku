import re
import uuid

from django.db import transaction

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.audit.services import AuditService
from apps.evidence.models import EvidenceItem
from apps.evidence.storage import store_evidence
from apps.parties.models import Party
from common.exceptions import DomainError
from infrastructure.storage.s3 import S3StorageClient

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Magic bytes for each allowed file type (used by the legacy upload_evidence path).
_MAGIC_BYTES: dict[str, list[bytes]] = {
    EvidenceItem.FileType.PHOTO: [
        b"\xff\xd8\xff",
        b"\x89PNG\r\n\x1a\n",
    ],
    EvidenceItem.FileType.SIGNATURE: [
        b"\x89PNG\r\n\x1a\n",
        b"\xff\xd8\xff",
    ],
    EvidenceItem.FileType.VOICE_NOTE: [
        b"RIFF",
        b"OggS",
        b"ID3",
        b"\xff\xfb", b"\xff\xf3", b"\xff\xf2",
    ],
    EvidenceItem.FileType.DOCUMENT: [
        b"%PDF",
        b"\xff\xd8\xff",
        b"\x89PNG\r\n\x1a\n",
    ],
}

# Allowed MIME types and their derived FileType / extension.
_MIME_TO_FILE_TYPE: dict[str, str] = {
    "image/jpeg":       EvidenceItem.FileType.PHOTO,
    "image/png":        EvidenceItem.FileType.PHOTO,
    "audio/wav":        EvidenceItem.FileType.VOICE_NOTE,
    "audio/ogg":        EvidenceItem.FileType.VOICE_NOTE,
    "audio/mpeg":       EvidenceItem.FileType.VOICE_NOTE,
    "application/pdf":  EvidenceItem.FileType.DOCUMENT,
}

_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg":       "jpg",
    "image/png":        "png",
    "audio/wav":        "wav",
    "audio/ogg":        "ogg",
    "audio/mpeg":       "mp3",
    "application/pdf":  "pdf",
}

# evidence_type must be lowercase alphanumeric with underscores only.
_EVIDENCE_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]{1,126}$")


def _validate_file(file_type: str, file_data: bytes) -> None:
    if len(file_data) == 0:
        raise DomainError("Uploaded file is empty")
    if len(file_data) > _MAX_FILE_SIZE:
        raise DomainError(
            f"File exceeds maximum allowed size of {_MAX_FILE_SIZE // (1024 * 1024)} MB"
        )
    allowed_signatures = _MAGIC_BYTES.get(file_type)
    if allowed_signatures is None:
        raise DomainError(f"Unknown file type: {file_type}")
    if not any(file_data.startswith(sig) for sig in allowed_signatures):
        raise DomainError(
            f"File content does not match the declared type '{file_type}'"
        )


class EvidenceService:
    # ------------------------------------------------------------------ #
    # Legacy path: file streams through Django (kept for internal use).   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def upload_evidence(
        *,
        agreement_id: int,
        party_id: int,
        file_type: str,
        file_data: bytes,
        original_name: str = "",
    ) -> EvidenceItem:
        _validate_file(file_type, file_data)

        agreement = Agreement.objects.get(pk=agreement_id)
        party = Party.objects.get(pk=party_id)
        if party.agreement_id != agreement.pk:
            raise DomainError("Party does not belong to this agreement")

        file_hash, storage_url = store_evidence(file_data, original_name)
        item = EvidenceItem.objects.create(
            agreement=agreement,
            uploaded_by=party,
            file_type=file_type,
            file_hash=file_hash,
            storage_url=storage_url,
            original_name=original_name,
            upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        )
        AuditService.record_event(
            event_type="evidence.uploaded",
            entity_type="evidence",
            entity_id=str(item.pk),
            metadata={
                "agreement_id": agreement.pk,
                "file_type": file_type,
                "file_hash": file_hash,
            },
        )
        return item

    # ------------------------------------------------------------------ #
    # Presigned URL path: client uploads directly to S3.                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_upload_url(
        *,
        agreement_id: int,
        uploading_account,
        evidence_type: str,
        mime_type: str,
        size_bytes: int,
    ) -> dict:
        """Issue a presigned PUT URL and create a pending EvidenceItem.

        Returns a dict with upload_url, file_key, and required headers so the
        mobile client can PUT the file directly to object storage.
        """
        if not _EVIDENCE_TYPE_RE.match(evidence_type):
            raise DomainError(
                "evidence_type must be lowercase letters, digits, or underscores "
                "(e.g. 'vehicle_photo_front')."
            )

        file_type = _MIME_TO_FILE_TYPE.get(mime_type)
        if file_type is None:
            raise DomainError(
                f"Unsupported MIME type '{mime_type}'. "
                f"Allowed: {', '.join(sorted(_MIME_TO_FILE_TYPE))}."
            )

        if size_bytes <= 0:
            raise DomainError("size_bytes must be greater than zero.")
        if size_bytes > _MAX_FILE_SIZE:
            raise DomainError(
                f"File size {size_bytes} exceeds the {_MAX_FILE_SIZE // (1024 * 1024)} MB limit."
            )

        agreement = Agreement.objects.get(pk=agreement_id)
        if agreement.status == AgreementStatus.SEALED:
            raise DomainError("Cannot add evidence to a sealed agreement.")

        ext = _MIME_TO_EXT[mime_type]
        file_key = (
            f"agreements/{agreement_id}/evidence"
            f"/{evidence_type}_{uuid.uuid4().hex[:8]}.{ext}"
        )

        storage = S3StorageClient()
        upload_url, headers = storage.generate_presigned_upload_url(
            file_key, mime_type, expires_in=900
        )

        # Find the matching party for this account (best-effort; null if not found).
        uploaded_by = Party.objects.filter(
            agreement=agreement, phone=uploading_account.phone
        ).first()

        item = EvidenceItem.objects.create(
            agreement=agreement,
            uploaded_by=uploaded_by,
            file_type=file_type,
            evidence_type=evidence_type,
            mime_type=mime_type,
            size_bytes=size_bytes,
            file_key=file_key,
            upload_status=EvidenceItem.UploadStatus.PENDING,
        )

        AuditService.record_event(
            event_type="evidence.upload_url_issued",
            entity_type="evidence",
            entity_id=str(item.pk),
            actor=str(uploading_account.pk),
            metadata={
                "agreement_id": agreement_id,
                "evidence_type": evidence_type,
                "mime_type": mime_type,
                "size_bytes": size_bytes,
            },
        )

        return {
            "upload_url": upload_url,
            "file_key": file_key,
            "headers": headers,
            "evidence_id": item.pk,
        }

    @staticmethod
    @transaction.atomic
    def confirm_upload(
        *,
        agreement_id: int,
        file_key: str,
        evidence_type: str,
        mime_type: str,
    ) -> EvidenceItem:
        """Confirm that the client has uploaded the file and finalise the record.

        Validates that the supplied file_key and evidence_type match the pending
        EvidenceItem created during generate_upload_url, then marks it confirmed
        and sets the permanent storage URL.
        """
        try:
            item = EvidenceItem.objects.select_for_update().get(
                agreement_id=agreement_id,
                file_key=file_key,
                upload_status=EvidenceItem.UploadStatus.PENDING,
            )
        except EvidenceItem.DoesNotExist:
            raise DomainError(
                "No pending upload found for this file key on this agreement."
            )

        if item.evidence_type != evidence_type:
            raise DomainError(
                "evidence_type does not match the original upload request."
            )
        if item.mime_type != mime_type:
            raise DomainError(
                "mime_type does not match the original upload request."
            )

        item.storage_url = S3StorageClient().build_object_url(file_key)
        item.upload_status = EvidenceItem.UploadStatus.CONFIRMED
        item.save(update_fields=["storage_url", "upload_status"])

        AuditService.record_event(
            event_type="evidence.confirmed",
            entity_type="evidence",
            entity_id=str(item.pk),
            metadata={
                "agreement_id": agreement_id,
                "evidence_type": evidence_type,
                "file_key": file_key,
            },
        )
        return item
