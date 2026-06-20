from django.db import transaction

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.audit.services import AuditService
from apps.parties.models import Party
from common.exceptions import DomainError
from common.phone_numbers import normalize_phone_for_compare, normalize_phone_to_e164


def _require_identity_fields(party_data: dict, *, role: str) -> None:
    id_type = party_data.get("id_type")
    id_number = party_data.get("id_number")
    if not id_type or not str(id_type).strip():
        raise DomainError(f"Identity document type is required for role '{role}'.")
    if not id_number or not str(id_number).strip():
        raise DomainError(f"Identity document number is required for role '{role}'.")


def _initiator_phone_keys(initiator_account) -> set[str]:
    user = getattr(initiator_account, "user", None)
    keys = {
        normalize_phone_for_compare(getattr(initiator_account, "phone", "")),
        normalize_phone_for_compare(getattr(user, "phone", "")),
    }
    keys.discard("")
    return keys


def _normalized_party_payloads(parties_data: list[dict]) -> list[dict]:
    normalized = []
    phone_keys = []
    for party_data in parties_data:
        phone = normalize_phone_to_e164(party_data.get("phone"))
        phone_key = normalize_phone_for_compare(phone)
        if not phone_key:
            raise DomainError("Each party must have a phone number.")
        normalized.append({**party_data, "phone": phone})
        phone_keys.append(phone_key)
    if len(phone_keys) != len(set(phone_keys)):
        raise DomainError("Each party must have a unique phone number.")
    return normalized


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

        if agreement.status not in (AgreementStatus.DRAFT, AgreementStatus.ACTIVE):
            raise DomainError("Cannot modify parties: agreement is not in an editable state.")

        if len(parties_data) < 2:
            raise DomainError("At least two parties are required.")

        roles = [p["role"] for p in parties_data]
        if len(roles) != len(set(roles)):
            raise DomainError("Each party must have a unique role.")

        parties_data = _normalized_party_payloads(parties_data)
        party_phone_keys = {normalize_phone_for_compare(p["phone"]) for p in parties_data}
        if not _initiator_phone_keys(initiator_account).intersection(party_phone_keys):
            raise DomainError("At least one party must match your account phone number.")

        for p in parties_data:
            _require_identity_fields(p, role=p["role"])

        Party.objects.filter(agreement=agreement).delete()
        parties = [
            Party(
                agreement=agreement,
                role=p["role"],
                display_name=p["full_name"],
                phone=p["phone"],
                id_type=p["id_type"],
                id_number=p["id_number"].strip(),
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

        if agreement.status not in (AgreementStatus.DRAFT, AgreementStatus.ACTIVE):
            raise DomainError("Cannot modify parties: agreement is not in an editable state.")

        updated = []
        for patch in parties_data:
            role = patch["role"]
            try:
                party = Party.objects.get(agreement=agreement, role=role)
            except Party.DoesNotExist:
                raise DomainError(
                    f"No party with role '{role}' exists on this agreement."
                ) from None
            update_fields = []
            if "full_name" in patch:
                party.display_name = patch["full_name"]
                update_fields.append("display_name")
            if "phone" in patch:
                normalized_phone = normalize_phone_to_e164(patch["phone"])
                normalized_phone_key = normalize_phone_for_compare(normalized_phone)
                if not normalized_phone_key:
                    raise DomainError("Each party must have a phone number.")
                existing_phone_keys = {
                    normalize_phone_for_compare(existing_phone)
                    for existing_phone in Party.objects.filter(agreement=agreement)
                    .exclude(pk=party.pk)
                    .values_list("phone", flat=True)
                }
                duplicate_exists = normalized_phone_key in existing_phone_keys
                if duplicate_exists:
                    raise DomainError("Each party must have a unique phone number.")
                party.phone = normalized_phone
                update_fields.append("phone")
            if "id_type" in patch:
                _require_identity_fields(
                    {"id_type": patch["id_type"], "id_number": party.id_number},
                    role=role,
                )
                party.id_type = patch["id_type"]
                update_fields.append("id_type")
            if "id_number" in patch:
                _require_identity_fields(
                    {"id_type": party.id_type, "id_number": patch["id_number"]},
                    role=role,
                )
                party.id_number = patch["id_number"].strip()
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
