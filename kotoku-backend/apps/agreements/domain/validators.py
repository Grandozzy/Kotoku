"""Agreement validation rules.

Checks whether an agreement satisfies all business requirements before
sealing.  Pure functions — no DB writes, no state changes.

Usage:
    result = validate_agreement(agreement)
    if not result.valid:
        for err in result.errors:
            print(err.code, err.message)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.parties.identity import (
    build_party_identity_states,
    is_identity_required,
    is_valid_ghana_card_pin,
    normalize_ghana_card_pin,
)

# ── Data types ────────────────────────────────────────────────────────────── #


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str
    field: str


@dataclass
class ValidationResult:
    errors: list[ValidationError] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def add(self, code: str, message: str, field_name: str) -> None:
        self.errors.append(ValidationError(code=code, message=message, field=field_name))


# ── Scenario slugs ────────────────────────────────────────────────────────── #

SCENARIO_USED_VEHICLE_SALE = "used_vehicle_sale"
SCENARIO_ROOM_RENTAL = "room_rental"

# Roles that must be present for each scenario (at least one pair).
_SCENARIO_REQUIRED_ROLE_PAIRS: dict[str, tuple[str, str]] = {
    SCENARIO_USED_VEHICLE_SALE: ("buyer", "seller"),
    SCENARIO_ROOM_RENTAL: ("landlord", "tenant"),
}


# ── Internal helpers ──────────────────────────────────────────────────────── #


def _count_confirmed_evidence(agreement, evidence_type_prefix: str) -> int:
    """Count confirmed evidence items whose evidence_type starts with prefix."""
    return agreement.evidence_items.filter(
        upload_status="confirmed",
        evidence_type__startswith=evidence_type_prefix,
    ).count()


def _party_identity_states(agreement, parties: list):
    return build_party_identity_states(
        parties=parties,
        evidence_items=agreement.evidence_items.all(),
        include_view_urls=False,
    )


# ── Core field checks ─────────────────────────────────────────────────────── #


def _check_core_fields(agreement, result: ValidationResult) -> None:
    if not agreement.title or not agreement.title.strip():
        result.add(
            code="MISSING_TITLE",
            message="Agreement title is required.",
            field_name="title",
        )
    if not agreement.scenario_template or not agreement.scenario_template.strip():
        result.add(
            code="MISSING_SCENARIO_TEMPLATE",
            message="A scenario template must be set before sealing.",
            field_name="scenario_template",
        )


# ── Party checks ──────────────────────────────────────────────────────────── #


def _check_parties(agreement, result: ValidationResult) -> list:
    """Validate party count and roles; return the party list for further checks."""
    parties = list(agreement.parties.all())
    roles = {p.role for p in parties}

    if len(parties) < 2:
        result.add(
            code="INSUFFICIENT_PARTIES",
            message="At least 2 parties are required.",
            field_name="parties",
        )
        return parties

    scenario = agreement.scenario_template
    if scenario in _SCENARIO_REQUIRED_ROLE_PAIRS:
        r1, r2 = _SCENARIO_REQUIRED_ROLE_PAIRS[scenario]
        if r1 not in roles or r2 not in roles:
            result.add(
                code="MISSING_REQUIRED_ROLES",
                message=f"This agreement requires a '{r1}' and a '{r2}'.",
                field_name="parties",
            )

    return parties


# ── Scenario-specific evidence checks ────────────────────────────────────── #


def _check_used_vehicle_sale(agreement, parties: list, result: ValidationResult) -> None:
    vehicle_photo_count = _count_confirmed_evidence(agreement, "vehicle_photo")
    if vehicle_photo_count < 3:
        result.add(
            code="INSUFFICIENT_VEHICLE_PHOTOS",
            message="Add at least 3 photos of the vehicle.",
            field_name="evidence",
        )


def _check_room_rental(agreement, parties: list, result: ValidationResult) -> None:
    property_photo_count = _count_confirmed_evidence(agreement, "property_photo")
    if property_photo_count < 2:
        result.add(
            code="INSUFFICIENT_PROPERTY_PHOTOS",
            message="Add at least 2 photos of the property.",
            field_name="evidence",
        )

    # If a deposit amount is set, require at least one condition/defect photo.
    deposit = getattr(agreement, "deposit_amount", None)
    if deposit and deposit > 0:
        if _count_confirmed_evidence(agreement, "condition_photo") < 1:
            result.add(
                code="MISSING_CONDITION_PHOTO",
                message=(
                    "At least one condition/defect photo is required when a deposit is specified."
                ),
                field_name="evidence",
            )


# ── Identity baseline checks ──────────────────────────────────────────────── #


def _check_identity_baseline(parties: list, result: ValidationResult) -> None:
    """Every non-witness party must have a valid, unique Ghana Card PIN recorded."""
    seen_pins: dict[str, str] = {}
    for party in parties:
        if not is_identity_required(party.role):
            continue
        if not party.id_type or not party.id_number:
            result.add(
                code="MISSING_GHANA_CARD_PIN",
                message=(
                    f"Ghana Card PIN is required for the {party.role}. "
                    "Please provide the Ghana Card PIN."
                ),
                field_name="parties",
            )
            continue
        if party.id_type != "ghana_card" or not is_valid_ghana_card_pin(party.id_number):
            result.add(
                code="INVALID_GHANA_CARD_PIN",
                message=(
                    f"The {party.role} must use a valid Ghana Card PIN in the form "
                    "GHA-000000000-0."
                ),
                field_name="parties",
            )
            continue
        normalized_pin = normalize_ghana_card_pin(party.id_number)
        if normalized_pin in seen_pins:
            result.add(
                code="DUPLICATE_GHANA_CARD_PIN",
                message=(
                    f"The {party.role} and {seen_pins[normalized_pin]} cannot share the same Ghana Card PIN."
                ),
                field_name="parties",
            )
            continue
        seen_pins[normalized_pin] = party.role


def _check_party_ghana_card_uploads(
    parties: list,
    identity_states: dict,
    result: ValidationResult,
) -> None:
    for party in parties:
        if not is_identity_required(party.role):
            continue
        state = identity_states.get(party.role)
        if state is None or not state.front_uploaded:
            result.add(
                code="MISSING_GHANA_CARD_FRONT",
                message=f"A confirmed Ghana Card front image is required for the {party.role}.",
                field_name="evidence",
            )
        if state is None or not state.back_uploaded:
            result.add(
                code="MISSING_GHANA_CARD_BACK",
                message=f"A confirmed Ghana Card back image is required for the {party.role}.",
                field_name="evidence",
            )
            continue
        if not state.selfie_uploaded:
            result.add(
                code="MISSING_IDENTITY_SELFIE",
                message=f"A confirmed selfie photo is required for the {party.role}.",
                field_name="evidence",
            )
            continue
        if state.verification_status == "verified":
            continue
        if state.verification_status in ("pending", "processing"):
            result.add(
                code="GHANA_CARD_VERIFICATION_PENDING",
                message=f"Ghana Card verification is still pending for the {party.role}.",
                field_name="evidence",
            )
            continue
        if state.verification_status == "manual_review_required":
            result.add(
                code="GHANA_CARD_REVIEW_REQUIRED",
                message=f"Ghana Card verification needs manual review for the {party.role}.",
                field_name="evidence",
            )
            continue
        result.add(
            code="GHANA_CARD_VERIFICATION_FAILED",
            message=f"Ghana Card verification failed for the {party.role}. Upload a clearer card image that matches the entered details.",
            field_name="evidence",
        )


_SCENARIO_CHECKERS = {
    SCENARIO_USED_VEHICLE_SALE: _check_used_vehicle_sale,
    SCENARIO_ROOM_RENTAL: _check_room_rental,
}


# ── Public API ────────────────────────────────────────────────────────────── #


def validate_agreement(agreement) -> ValidationResult:
    """Run all business-rule checks on *agreement* and return a ValidationResult.

    No state is mutated; the caller decides what to do with the result.
    """
    result = ValidationResult()

    _check_core_fields(agreement, result)
    parties = _check_parties(agreement, result)
    _check_identity_baseline(parties, result)
    _check_party_ghana_card_uploads(parties, _party_identity_states(agreement, parties), result)

    scenario = agreement.scenario_template
    checker = _SCENARIO_CHECKERS.get(scenario)
    if checker is not None:
        checker(agreement, parties, result)

    return result
