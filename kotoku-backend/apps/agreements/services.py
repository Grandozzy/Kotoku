import hashlib
import json

from django.db import transaction
from django.utils import timezone

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.domain.policies import (
    can_reopen,
    can_request_consent,
    can_request_reopen,
    can_seal,
)
from apps.agreements.domain.state_machine import next_state
from apps.agreements.models import Agreement
from apps.audit.services import AuditService
from apps.identity.models import IdentityRecord
from apps.parties.models import Party
from common.exceptions import DomainError


def _compute_seal_hash(agreement) -> str:
    """Return a SHA-256 hex digest of the agreement's state at seal time.

    Captures identity, evidence, and core fields so any tampering after
    sealing produces a detectable hash mismatch.
    """
    parties = list(
        agreement.parties.order_by("role").values(
            "role", "display_name", "id_type", "id_number", "phone"
        )
    )
    evidence = list(
        agreement.evidence_items.filter(upload_status="confirmed")
        .order_by("evidence_type", "file_key")
        .values("evidence_type", "file_hash", "file_key")
    )
    payload = {
        "agreement_id": agreement.pk,
        "title": agreement.title,
        "description": agreement.description,
        "scenario_template": agreement.scenario_template,
        "parties": parties,
        "evidence": evidence,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class AgreementService:
    @staticmethod
    def create_draft(
        *,
        title: str,
        created_by,
        description: str = "",
        scenario_template: str = "",
    ) -> Agreement:
        agreement = Agreement.objects.create(
            title=title,
            description=description,
            scenario_template=scenario_template,
            created_by=created_by,
        )
        AuditService.record_event(
            event_type="agreement.created",
            entity_type="agreement",
            entity_id=str(agreement.pk),
            actor=str(created_by.pk),
            metadata={"title": title},
        )
        return agreement

    @staticmethod
    def update_draft(
        *,
        agreement_id: int,
        title: str | None = None,
        description: str | None = None,
        scenario_template: str | None = None,
    ) -> Agreement:
        agreement = Agreement.objects.get(pk=agreement_id)
        if agreement.status != AgreementStatus.DRAFT:
            raise DomainError("Can only update a draft agreement")
        update_fields = ["updated_at"]
        if title is not None:
            agreement.title = title
            update_fields.append("title")
        if description is not None:
            agreement.description = description
            update_fields.append("description")
        if scenario_template is not None:
            agreement.scenario_template = scenario_template
            update_fields.append("scenario_template")
        agreement.save(update_fields=update_fields)
        AuditService.record_event(
            event_type="agreement.updated",
            entity_type="agreement",
            entity_id=str(agreement.pk),
            metadata={"updated_fields": update_fields},
        )
        return agreement

    @staticmethod
    def add_party(
        *,
        agreement_id: int,
        identity_id: int,
        role: str,
        display_name: str,
    ) -> Party:
        agreement = Agreement.objects.get(pk=agreement_id)
        if agreement.status != AgreementStatus.DRAFT:
            raise DomainError("Can only add parties to a draft agreement")
        identity = IdentityRecord.objects.get(pk=identity_id)
        party = Party.objects.create(
            agreement=agreement,
            identity=identity,
            role=role,
            display_name=display_name,
        )
        AuditService.record_event(
            event_type="agreement.party_added",
            entity_type="agreement",
            entity_id=str(agreement.pk),
            metadata={"party_id": party.pk, "role": role},
        )
        return party

    @staticmethod
    @transaction.atomic
    def request_consent(*, agreement_id: int) -> Agreement:
        agreement = Agreement.objects.select_for_update().get(pk=agreement_id)
        if not can_request_consent(agreement):
            raise DomainError(
                "Cannot request consent: agreement must have at least 2 parties "
                "and be in draft or pending_consent status."
            )
        new_status = next_state(agreement.status, "request_consent")
        agreement.status = new_status
        agreement.save(update_fields=["status", "updated_at"])
        AuditService.record_event(
            event_type="agreement.consent_requested",
            entity_type="agreement",
            entity_id=str(agreement.pk),
        )
        return agreement

    @staticmethod
    @transaction.atomic
    def seal_agreement(*, agreement_id: int) -> Agreement:
        agreement = Agreement.objects.select_for_update().get(pk=agreement_id)
        if not can_seal(agreement):
            raise DomainError(
                "Cannot seal: all parties must have consented and at least one "
                "piece of evidence must be confirmed."
            )
        new_status = next_state(agreement.status, "seal")
        agreement.status = new_status
        agreement.sealed_at = timezone.now()
        agreement.seal_hash = _compute_seal_hash(agreement)
        agreement.save(update_fields=["status", "sealed_at", "seal_hash", "updated_at"])
        AuditService.record_event(
            event_type="agreement.sealed",
            entity_type="agreement",
            entity_id=str(agreement.pk),
        )
        return agreement

    @staticmethod
    @transaction.atomic
    def close_agreement(*, agreement_id: int) -> Agreement:
        agreement = Agreement.objects.select_for_update().get(pk=agreement_id)
        new_status = next_state(agreement.status, "close")
        agreement.status = new_status
        agreement.closed_at = timezone.now()
        agreement.save(update_fields=["status", "closed_at", "updated_at"])
        AuditService.record_event(
            event_type="agreement.closed",
            entity_type="agreement",
            entity_id=str(agreement.pk),
        )
        return agreement

    @staticmethod
    @transaction.atomic
    def request_reopen(*, agreement_id: int) -> Agreement:
        """Initiate a bilateral reopen request: SEALED → REOPEN_REQUESTED.

        OTP issuance is handled separately by ConsentService.request_reopen_otp
        so that the state transition and OTP dispatch can be called from the same
        API view in a single request.
        """
        agreement = Agreement.objects.select_for_update().get(pk=agreement_id)
        if not can_request_reopen(agreement):
            raise DomainError("Reopen can only be requested for sealed agreements.")
        new_status = next_state(agreement.status, "request_reopen")
        agreement.status = new_status
        agreement.save(update_fields=["status", "updated_at"])
        AuditService.record_event(
            event_type="agreement.reopen_requested",
            entity_type="agreement",
            entity_id=str(agreement.pk),
        )
        return agreement

    @staticmethod
    @transaction.atomic
    def complete_bilateral_reopen(*, agreement_id: int) -> Agreement:
        """Finalize the reopen once all parties have confirmed: REOPEN_REQUESTED → ACTIVE.

        Called automatically by ConsentService.confirm_reopen_by_phone when the
        last party confirms. Clears sealed_at and seal_hash so the agreement can
        be edited and re-sealed cleanly.
        """
        agreement = Agreement.objects.select_for_update().get(pk=agreement_id)
        new_status = next_state(agreement.status, "bilateral_confirm")
        agreement.status = new_status
        agreement.sealed_at = None
        agreement.seal_hash = ""
        agreement.save(update_fields=["status", "sealed_at", "seal_hash", "updated_at"])
        AuditService.record_event(
            event_type="agreement.reopened_bilateral",
            entity_type="agreement",
            entity_id=str(agreement.pk),
        )
        return agreement

    @staticmethod
    @transaction.atomic
    def cancel_reopen(*, agreement_id: int) -> Agreement:
        """Cancel a pending reopen request: REOPEN_REQUESTED → SEALED."""
        agreement = Agreement.objects.select_for_update().get(pk=agreement_id)
        new_status = next_state(agreement.status, "cancel_reopen")
        agreement.status = new_status
        agreement.save(update_fields=["status", "updated_at"])
        AuditService.record_event(
            event_type="agreement.reopen_cancelled",
            entity_type="agreement",
            entity_id=str(agreement.pk),
        )
        return agreement

    @staticmethod
    @transaction.atomic
    def reopen_agreement(*, agreement_id: int) -> Agreement:
        agreement = Agreement.objects.select_for_update().get(pk=agreement_id)
        if not can_reopen(agreement):
            raise DomainError(
                "Cannot reopen: agreement must be sealed within the last 24 hours"
            )
        new_status = next_state(agreement.status, "reopen")
        agreement.status = new_status
        agreement.sealed_at = None
        agreement.save(update_fields=["status", "sealed_at", "updated_at"])
        AuditService.record_event(
            event_type="agreement.reopened",
            entity_type="agreement",
            entity_id=str(agreement.pk),
        )
        return agreement
