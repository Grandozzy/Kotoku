from apps.evidence.models import EvidenceItem


class EvidenceSelector:
    @staticmethod
    def list_evidence_for_agreement(agreement_id: int):
        return (
            EvidenceItem.objects.filter(agreement_id=agreement_id)
            .select_related("uploaded_by", "uploaded_by__identity")
            .order_by("-created_at")
        )

    @staticmethod
    def get_evidence_detail(evidence_id: int) -> EvidenceItem:
        return EvidenceItem.objects.select_related(
            "agreement", "uploaded_by", "uploaded_by__identity"
        ).get(pk=evidence_id)
