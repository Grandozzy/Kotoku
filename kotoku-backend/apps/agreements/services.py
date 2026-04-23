from django.db import transaction
from django.utils import timezone

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.domain.policies import can_reopen, can_request_consent, can_seal
from apps.agreements.domain.state_machine import next_state
from apps.agreements.models import Agreement
from apps.audit.services import AuditService
from apps.identity.models import IdentityRecord
from apps.parties.models import Party
from common.exceptions import DomainError


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
                "Cannot request consent: agreement must be draft with at least 2 parties"
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
                "Cannot seal: agreement must be active with evidence attached"
            )
        new_status = next_state(agreement.status, "seal")
        agreement.status = new_status
        agreement.sealed_at = timezone.now()
        agreement.save(update_fields=["status", "sealed_at", "updated_at"])
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
