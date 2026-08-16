import re
from dataclasses import dataclass

from apps.evidence.models import EvidenceItem
from apps.identity.models import PartyIdentityVerification
from common.exceptions import DomainError
from infrastructure.storage.s3 import S3StorageClient

_GHANA_CARD_PIN_RE = re.compile(r"^GHA-\d{9}-\d$")
_IDENTITY_SUFFIXES = ("ghana_card_front", "ghana_card_back", "selfie")
_SUPPORTED_ROLES = {"buyer", "seller", "landlord", "tenant"}


def is_identity_required(role: str) -> bool:
    return role != "witness"


def normalize_ghana_card_pin(value: str) -> str:
    return value.strip().upper()


def is_valid_ghana_card_pin(value: str) -> bool:
    return bool(_GHANA_CARD_PIN_RE.match(normalize_ghana_card_pin(value)))


def validate_party_identity_input(*, role: str, id_type: str, id_number: str) -> str:
    if not is_identity_required(role):
        return id_number.strip()

    if id_type != "ghana_card":
        raise DomainError(f"Only Ghana Card is supported for role '{role}'.")

    normalized_pin = normalize_ghana_card_pin(id_number)
    if not normalized_pin:
        raise DomainError(f"Ghana Card PIN is required for role '{role}'.")
    if not is_valid_ghana_card_pin(normalized_pin):
        raise DomainError(
            f"Ghana Card PIN must use the format GHA-000000000-0 for role '{role}'."
        )
    return normalized_pin


def ensure_unique_pins(parties_data: list[dict]) -> None:
    pins: dict[str, str] = {}
    for party_data in parties_data:
        role = party_data["role"]
        if not is_identity_required(role):
            continue
        pin = normalize_ghana_card_pin(str(party_data.get("id_number", "")))
        if not pin:
            continue
        if pin in pins:
            raise DomainError(
                f"Ghana Card PIN must be unique per agreement. Roles '{pins[pin]}' and '{role}' cannot share one."
            )
        pins[pin] = role


def identity_evidence_type(role: str, side: str) -> str:
    if role not in _SUPPORTED_ROLES:
        raise ValueError(f"Unsupported role '{role}' for identity evidence.")
    if side not in ("front", "back", "selfie"):
        raise ValueError(f"Unsupported identity evidence side '{side}'.")
    if side == "selfie":
        return f"{role}_selfie"
    return f"{role}_ghana_card_{side}"


def parse_identity_evidence_type(evidence_type: str) -> tuple[str, str] | None:
    for suffix in _IDENTITY_SUFFIXES:
        prefix = f"_{suffix}"
        if evidence_type.endswith(prefix):
            role = evidence_type[: -len(prefix)]
            if suffix == "selfie":
                side = "selfie"
            else:
                side = "front" if suffix.endswith("front") else "back"
            if role in _SUPPORTED_ROLES:
                return role, side
    return None


def validate_identity_evidence_type(*, agreement, evidence_type: str) -> None:
    parsed = parse_identity_evidence_type(evidence_type)
    if parsed is None:
        return
    role, _side = parsed
    if not agreement.parties.filter(role=role).exists():
        raise DomainError(
            f"Identity evidence type '{evidence_type}' does not match a party role on this agreement."
        )


def latest_identity_evidence_by_party(*, parties, evidence_items) -> dict[str, dict[str, EvidenceItem]]:
    latest_by_slot: dict[tuple[str, str], EvidenceItem] = {}
    for item in evidence_items:
        if item.upload_status != EvidenceItem.UploadStatus.CONFIRMED:
            continue
        parsed = parse_identity_evidence_type(item.evidence_type)
        if parsed is None:
            continue
        role, side = parsed
        slot = (role, side)
        current = latest_by_slot.get(slot)
        if current is None or item.pk > current.pk:
            latest_by_slot[slot] = item

    identity_items: dict[str, dict[str, EvidenceItem]] = {}
    for party in parties:
        if not is_identity_required(party.role):
            continue
        role_items: dict[str, EvidenceItem] = {}
        for side in ("front", "back", "selfie"):
            item = latest_by_slot.get((party.role, side))
            if item is not None:
                role_items[side] = item
        identity_items[party.role] = role_items
    return identity_items


@dataclass(frozen=True)
class PartyIdentityState:
    pin: str
    front_uploaded: bool
    back_uploaded: bool
    selfie_uploaded: bool
    front_view_url: str | None
    back_view_url: str | None
    selfie_view_url: str | None
    verification_status: str
    verification_detail: str
    verification_failure_codes: list[str]
    liveness_status: str  # "", "pending", "passed", "failed"


def build_party_identity_states(
    *,
    parties,
    evidence_items,
    include_view_urls: bool = True,
) -> dict[str, PartyIdentityState]:
    parties = list(parties)
    identity_items = latest_identity_evidence_by_party(
        parties=parties,
        evidence_items=evidence_items,
    )
    verification_map = {
        record.party_id: record
        for record in PartyIdentityVerification.objects.filter(
            party_id__in=[p.id for p in parties if p.id]
        )
    }

    storage = S3StorageClient() if include_view_urls else None
    states: dict[str, PartyIdentityState] = {}
    for party in parties:
        if not is_identity_required(party.role):
            continue
        role_items = identity_items.get(party.role, {})
        front = role_items.get("front")
        back = role_items.get("back")
        selfie = role_items.get("selfie")
        verification = verification_map.get(party.id)
        states[party.role] = PartyIdentityState(
            pin=normalize_ghana_card_pin(party.id_number or ""),
            front_uploaded=front is not None,
            back_uploaded=back is not None,
            selfie_uploaded=selfie is not None,
            front_view_url=(
                storage.generate_presigned_view_url(front.file_key, content_type=front.mime_type)
                if storage and front and front.file_key
                else None
            ),
            back_view_url=(
                storage.generate_presigned_view_url(back.file_key, content_type=back.mime_type)
                if storage and back and back.file_key
                else None
            ),
            selfie_view_url=(
                storage.generate_presigned_view_url(selfie.file_key, content_type=selfie.mime_type)
                if storage and selfie and selfie.file_key
                else None
            ),
            verification_status=(
                verification.status
                if verification
                else PartyIdentityVerification.Status.PENDING
            ),
            verification_detail=(
                verification.detail
                if verification and verification.detail
                else "Awaiting Ghana Card verification."
            ),
            verification_failure_codes=list(verification.failure_codes if verification else []),
            liveness_status=verification.liveness_status if verification else "",
        )
    return states
