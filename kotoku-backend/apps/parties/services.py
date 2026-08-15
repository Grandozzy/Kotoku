from django.db import transaction

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.audit.services import AuditService
from apps.identity.services import IdentityService
from apps.parties.identity import (
    ensure_unique_pins,
    is_identity_required,
    validate_party_identity_input,
)
from apps.parties.models import Party
from common.exceptions import DomainError
from common.phone_numbers import normalize_phone_for_compare, normalize_phone_to_e164


def _party_has_identity_uploads(party) -> bool:
    from apps.evidence.models import EvidenceItem
    patterns = [
        f"{party.role}_ghana_card_front",
        f"{party.role}_ghana_card_back",
        f"{party.role}_selfie",
    ]
    return EvidenceItem.objects.filter(
        agreement=party.agreement,
        evidence_type__in=patterns,
        upload_status=EvidenceItem.UploadStatus.CONFIRMED,
    ).exists()


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


def _normalized_identity_payloads(parties_data: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for party_data in parties_data:
        role = party_data["role"]
        _require_identity_fields(party_data, role=role)
        normalized_pin = validate_party_identity_input(
            role=role,
            id_type=str(party_data.get("id_type", "")).strip(),
            id_number=str(party_data.get("id_number", "")),
        )
        normalized.append({**party_data, "id_number": normalized_pin})
    ensure_unique_pins(normalized)
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

        parties_data = _normalized_identity_payloads(parties_data)

        Party.objects.filter(agreement=agreement).delete()
        parties = [
            Party(
                agreement=agreement,
                role=p["role"],
                display_name=p["full_name"],
                phone=p["phone"],
                id_type=p["id_type"],
                id_number=p["id_number"],
            )
            for p in parties_data
        ]
        Party.objects.bulk_create(parties)
        parties = list(Party.objects.filter(agreement=agreement).order_by("created_at"))
        for party in parties:
            if not party.id or not is_identity_required(party.role):
                continue
            IdentityService.reset_party_verification(party=party)
            if _party_has_identity_uploads(party):
                IdentityService.queue_party_verification(party_id=party.pk)

        AuditService.record_event(
            event_type="agreement.parties_set",
            entity_type="agreement",
            entity_id=str(agreement_id),
            actor=str(initiator_account.pk),
            metadata={"party_count": len(parties), "roles": roles},
        )
        return parties

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
            identity_changed = False
            if "full_name" in patch:
                party.display_name = patch["full_name"]
                update_fields.append("display_name")
                identity_changed = True
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
                party.id_type = patch["id_type"]
                update_fields.append("id_type")
                identity_changed = True
            if "id_number" in patch:
                party.id_number = patch["id_number"]
                update_fields.append("id_number")
                identity_changed = True
            if "id_type" in patch or "id_number" in patch:
                party.id_number = validate_party_identity_input(
                    role=role,
                    id_type=party.id_type,
                    id_number=party.id_number,
                )
                if "id_number" not in update_fields and role != "witness":
                    update_fields.append("id_number")
                if role != "witness":
                    existing_pins = {
                        value.strip().upper()
                        for value in Party.objects.filter(agreement=agreement)
                        .exclude(pk=party.pk)
                        .exclude(role="witness")
                        .values_list("id_number", flat=True)
                        if value
                    }
                    if party.id_number in existing_pins:
                        raise DomainError(
                            f"Ghana Card PIN must be unique per agreement. Another party already uses '{party.id_number}'."
                        )
            if update_fields:
                update_fields.append("updated_at")
                party.save(update_fields=update_fields)
                if is_identity_required(party.role) and identity_changed:
                    IdentityService.reset_party_verification(party=party)
                    if _party_has_identity_uploads(party):
                        IdentityService.queue_party_verification(party_id=party.pk)
            updated.append(party)

        AuditService.record_event(
            event_type="agreement.parties_patched",
            entity_type="agreement",
            entity_id=str(agreement_id),
            actor=str(initiator_account.pk),
            metadata={"patched_roles": [p["role"] for p in parties_data]},
        )
        return updated
