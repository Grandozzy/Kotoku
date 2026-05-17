import hashlib
import json
import logging

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
from apps.agreements.models import Agreement, AgreementRevision
from apps.audit.services import AuditService
from apps.identity.models import IdentityRecord
from apps.notifications.push import send_to_user
from apps.parties.models import Party
from common.exceptions import DomainError

logger = logging.getLogger("kotoku")


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


def _build_snapshot(agreement) -> dict:
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
    return {
        "agreement_id": agreement.pk,
        "title": agreement.title,
        "description": agreement.description,
        "scenario_template": agreement.scenario_template,
        "field_data": agreement.field_data,
        "parties": parties,
        "evidence": evidence,
    }


class AgreementService:
    @staticmethod
    def create_draft(
        *,
        title: str,
        created_by,
        description: str = "",
        scenario_template: str = "",
    ) -> Agreement:
        logger.info(
            "[DRAFT] service.create_draft title='%s' scenario_template='%s' creator=%s",
            title,
            scenario_template,
            created_by.pk,
        )
        agreement = Agreement.objects.create(
            title=title,
            description=description,
            scenario_template=scenario_template,
            created_by=created_by,
        )
        logger.info(
            "[DRAFT] service.create_draft persisted id=%s",
            agreement.pk,
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
        field_data: dict | None = None,
        step_index: int | None = None,
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
        if field_data is not None:
            agreement.field_data = field_data
            update_fields.append("field_data")
        if step_index is not None:
            agreement.step_index = step_index
            update_fields.append("step_index")
        agreement.save(update_fields=update_fields)
        logger.info(
            "[DRAFT] service.update_draft id=%s fields=%s scenario_template='%s' step_index=%s field_data_len=%s",
            agreement_id,
            [f for f in update_fields if f != "updated_at"],
            agreement.scenario_template,
            agreement.step_index,
            len(agreement.field_data) if agreement.field_data else 0,
        )
        AuditService.record_event(
            event_type="agreement.updated",
            entity_type="agreement",
            entity_id=str(agreement.pk),
            metadata={"updated_fields": update_fields},
        )
        return agreement

    @staticmethod
    def update_active(
        *,
        agreement_id: int,
        title: str | None = None,
        description: str | None = None,
        scenario_template: str | None = None,
        field_data: dict | None = None,
        step_index: int | None = None,
    ) -> Agreement:
        agreement = Agreement.objects.get(pk=agreement_id)
        if agreement.status != AgreementStatus.ACTIVE:
            raise DomainError("Can only update an active (reopened) agreement")
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
        if field_data is not None:
            agreement.field_data = field_data
            update_fields.append("field_data")
        if step_index is not None:
            agreement.step_index = step_index
            update_fields.append("step_index")
        agreement.save(update_fields=update_fields)
        AuditService.record_event(
            event_type="agreement.updated_active",
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
        from apps.billing.services import BillingService  # avoid circular at module load

        agreement = Agreement.objects.select_for_update().get(pk=agreement_id)

        # Check plan cap before any state mutation
        try:
            creator_account = agreement.created_by
            BillingService.check_seal_allowed(creator_account)
        except Exception as exc:
            from common.exceptions import DomainError as _DE
            if isinstance(exc, _DE):
                raise
            # If billing check itself errors, fail open (don't block sealing)
            pass

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
        parties = Party.objects.filter(agreement=agreement)
        for p in parties:
            if p.phone:
                send_to_user(p.phone, "agreement.sealed", {
                    "agreement_id": agreement.pk,
                    "title": agreement.title,
                })
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
        parties = Party.objects.filter(agreement=agreement)
        for p in parties:
            if p.phone:
                send_to_user(p.phone, "agreement.reopen_requested", {
                    "agreement_id": agreement.pk,
                    "title": agreement.title,
                })
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
        be edited and re-sealed cleanly. Creates an AgreementRevision snapshot
        before clearing seal data.
        """
        agreement = Agreement.objects.select_for_update().get(pk=agreement_id)
        new_status = next_state(agreement.status, "bilateral_confirm")
        snapshot_data = _build_snapshot(agreement)
        revision_number = AgreementRevision.objects.filter(
            agreement=agreement
        ).count() + 1
        AgreementRevision.objects.create(
            agreement=agreement,
            revision_number=revision_number,
            seal_hash=agreement.seal_hash,
            sealed_at=agreement.sealed_at,
            snapshot=snapshot_data,
        )
        agreement.status = new_status
        agreement.sealed_at = None
        agreement.seal_hash = ""
        agreement.save(update_fields=["status", "sealed_at", "seal_hash", "updated_at"])
        parties = Party.objects.filter(agreement=agreement)
        for p in parties:
            if p.phone:
                send_to_user(p.phone, "agreement.reopen_confirmed", {
                    "agreement_id": agreement.pk,
                    "title": agreement.title,
                })
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
