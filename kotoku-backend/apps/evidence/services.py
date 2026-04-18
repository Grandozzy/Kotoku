from apps.agreements.models import Agreement
from apps.audit.services import AuditService
from apps.evidence.models import EvidenceItem
from apps.evidence.storage import store_evidence
from apps.parties.models import Party
from common.exceptions import DomainError


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
