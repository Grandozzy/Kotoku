from django.db import transaction

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.audit.services import AuditService
from apps.parties.models import Party
from common.exceptions import DomainError


class PartyService:
    @staticmethod
    @transaction.atomic
    def set_parties(
        *,
        agreement_id: int,
        initiator_account,
        parties_data: list[dict],
    ) -> list[Party]:
        """Replace the full party set for a draft agreement (POST semantics).

        Rules enforced:
        - Agreement must not be sealed.
        - At least two parties required.
        - Each role must be unique within the submitted list.
        - At least one party phone must match the initiator's account phone.
        """
        agreement = Agreement.objects.select_for_update().get(pk=agreement_id)

        if agreement.status == AgreementStatus.SEALED:
            raise DomainError("Cannot modify parties of a sealed agreement.")

        if len(parties_data) < 2:
            raise DomainError("At least two parties are required.")

        roles = [p["role"] for p in parties_data]
        if len(roles) != len(set(roles)):
            raise DomainError("Each party must have a unique role.")

        phones = [p["phone"] for p in parties_data]
        if initiator_account.phone not in phones:
            raise DomainError(
                "At least one party must match your account phone number."
            )

        Party.objects.filter(agreement=agreement).delete()
        parties = [
            Party(
                agreement=agreement,
                role=p["role"],
                display_name=p["full_name"],
                phone=p["phone"],
                id_type=p.get("id_type", ""),
                id_number=p.get("id_number", ""),
            )
            for p in parties_data
        ]
        Party.objects.bulk_create(parties)

        AuditService.record_event(
            event_type="agreement.parties_set",
            entity_type="agreement",
            entity_id=str(agreement_id),
            actor=str(initiator_account.pk),
            metadata={"party_count": len(parties), "roles": roles},
        )
        return list(Party.objects.filter(agreement=agreement).order_by("created_at"))

    @staticmethod
    @transaction.atomic
    def patch_parties(
        *,
        agreement_id: int,
        initiator_account,
        parties_data: list[dict],
    ) -> list[Party]:
        """Partially update existing parties matched by role (PATCH semantics).

        Each entry must supply a role to identify the party. Only the supplied
        fields are updated; omitted fields are left unchanged.
        """
        agreement = Agreement.objects.select_for_update().get(pk=agreement_id)

        if agreement.status == AgreementStatus.SEALED:
            raise DomainError("Cannot modify parties of a sealed agreement.")

        updated = []
        for patch in parties_data:
            role = patch["role"]
            try:
                party = Party.objects.get(agreement=agreement, role=role)
            except Party.DoesNotExist:
                raise DomainError(
                    f"No party with role '{role}' exists on this agreement."
                )
            update_fields = []
            if "full_name" in patch:
                party.display_name = patch["full_name"]
                update_fields.append("display_name")
            if "phone" in patch:
                party.phone = patch["phone"]
                update_fields.append("phone")
            if "id_type" in patch:
                party.id_type = patch["id_type"]
                update_fields.append("id_type")
            if "id_number" in patch:
                party.id_number = patch["id_number"]
                update_fields.append("id_number")
            if update_fields:
                update_fields.append("updated_at")
                party.save(update_fields=update_fields)
            updated.append(party)

        AuditService.record_event(
            event_type="agreement.parties_patched",
            entity_type="agreement",
            entity_id=str(agreement_id),
            actor=str(initiator_account.pk),
            metadata={"patched_roles": [p["role"] for p in parties_data]},
        )
        return updated
