import logging

from django.utils import timezone

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.audit.services import AuditService
from apps.disputes.models import Dispute
from apps.parties.models import Party
from common.exceptions import DomainError

logger = logging.getLogger(__name__)

# Disputes can be raised on sealed agreements or those that are in
# a reopen/archive/expired terminal state — anything that is no longer
# a simple editable draft.
_DISPUTABLE_STATUSES = {
    AgreementStatus.SEALED,
    AgreementStatus.REOPEN_REQUESTED,
    AgreementStatus.CLOSED,
    AgreementStatus.ARCHIVED,
    AgreementStatus.EXPIRED,
}


class DisputeService:
    @staticmethod
    def open_dispute(
        *,
        agreement_id: int,
        raised_by_party_id: int,
        reason: str,
    ) -> Dispute:
        """Raise a dispute against a sealed (or closed/archived) agreement."""
        agreement = Agreement.objects.get(pk=agreement_id)
        if agreement.status not in _DISPUTABLE_STATUSES:
            raise DomainError(
                "Disputes can only be raised against sealed, closed, or archived agreements."
            )
        try:
            party = Party.objects.get(pk=raised_by_party_id, agreement_id=agreement_id)
        except Party.DoesNotExist:
            raise DomainError("The disputing party must be a party on this agreement.") from None

        if not reason or not reason.strip():
            raise DomainError("A reason is required to open a dispute.")

        dispute = Dispute.objects.create(
            agreement=agreement,
            raised_by=party,
            reason=reason.strip(),
        )
        logger.info(
            "dispute_opened: agreement_id=%s dispute_id=%s party_id=%s",
            agreement_id,
            dispute.pk,
            party.pk,
        )
        AuditService.record_event(
            event_type="dispute.opened",
            entity_type="dispute",
            entity_id=str(dispute.pk),
            actor=str(party.pk),
            metadata={"agreement_id": agreement_id, "reason_preview": reason[:80]},
        )
        return dispute

    @staticmethod
    def generate_case_pack(*, dispute: Dispute) -> dict:
        agreement = dispute.agreement
        case_pack = {
            "dispute_id": dispute.pk,
            "generated_at": timezone.now().isoformat(),
            "agreement": {
                "id": agreement.pk,
                "title": agreement.title,
                "scenario": agreement.scenario_template,
                "sealed_at": agreement.sealed_at.isoformat() if agreement.sealed_at else None,
                "seal_hash": agreement.seal_hash,
                "status": agreement.status,
            },
            "parties": [
                {
                    "id": p.pk,
                    "display_name": p.display_name,
                    "phone": p.phone,
                    "role": p.role,
                }
                for p in agreement.parties.all()
            ],
            "dispute": {
                "raised_by": dispute.raised_by.display_name,
                "raised_by_party_id": dispute.raised_by.pk,
                "reason": dispute.reason,
                "status": dispute.status,
                "resolution": dispute.resolution,
                "created_at": dispute.created_at.isoformat(),
                "resolved_at": dispute.resolved_at.isoformat() if dispute.resolved_at else None,
            },
        }
        return case_pack
