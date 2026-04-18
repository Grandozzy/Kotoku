from apps.agreements.domain.state_machine import next_state
from apps.agreements.models import Agreement
from apps.audit.services import AuditService
from apps.consent.models import ConsentRecord
from apps.consent.selectors import ConsentSelector


def sync_consent(agreement_id: int) -> None:
    if not ConsentSelector.all_parties_consented(agreement_id=agreement_id):
        return
    agreement = Agreement.objects.get(pk=agreement_id)
    new_status = next_state(agreement.status, "all_consented")
    agreement.status = new_status
    agreement.save(update_fields=["status", "updated_at"])
    AuditService.record_event(
        event_type="agreement.all_consented",
        entity_type="agreement",
        entity_id=str(agreement.pk),
    )
