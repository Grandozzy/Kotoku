from apps.agreements.models import Agreement
from apps.audit.services import AuditService
from apps.evidence.models import EvidenceItem
from apps.evidence.storage import store_evidence
from apps.parties.models import Party
from common.exceptions import DomainError

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Magic bytes for each allowed file type (checked against the first bytes of the upload)
_MAGIC_BYTES: dict[str, list[bytes]] = {
    EvidenceItem.FileType.PHOTO: [
        b"\xff\xd8\xff",          # JPEG
        b"\x89PNG\r\n\x1a\n",    # PNG
    ],
    EvidenceItem.FileType.SIGNATURE: [
        b"\x89PNG\r\n\x1a\n",    # PNG
        b"\xff\xd8\xff",          # JPEG
    ],
    EvidenceItem.FileType.VOICE_NOTE: [
        b"RIFF",   # WAV
        b"OggS",   # OGG
        b"ID3",    # MP3 with ID3 tag
        b"\xff\xfb", b"\xff\xf3", b"\xff\xf2",  # MP3 sync bytes
    ],
    EvidenceItem.FileType.DOCUMENT: [
        b"%PDF",              # PDF
        b"\xff\xd8\xff",     # JPEG (scanned doc)
        b"\x89PNG\r\n\x1a\n",  # PNG (scanned doc)
    ],
}


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
