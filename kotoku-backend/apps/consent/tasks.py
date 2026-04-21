from django.db import transaction

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.domain.state_machine import next_state
from apps.agreements.models import Agreement
from apps.audit.services import AuditService
from apps.consent.selectors import ConsentSelector


@transaction.atomic
def sync_consent(agreement_id: int) -> None:
    """Transition agreement to ACTIVE once all parties have consented.

    Idempotent: safe to call even if verify_otp() has already applied the
    transition. Uses a row-level lock to prevent races with concurrent calls.
    """
    if not ConsentSelector.all_parties_consented(agreement_id=agreement_id):
        return
    agreement = Agreement.objects.select_for_update().get(pk=agreement_id)
    if agreement.status == AgreementStatus.ACTIVE:
        return  # Already transitioned; nothing to do
    new_status = next_state(agreement.status, "all_consented")
    agreement.status = new_status
    agreement.save(update_fields=["status", "updated_at"])
    AuditService.record_event(
        event_type="agreement.all_consented",
        entity_type="agreement",
        entity_id=str(agreement.pk),
    )
