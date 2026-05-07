from datetime import timedelta

from django.utils import timezone

from apps.agreements.domain.enums import AgreementStatus


def can_request_consent(agreement) -> bool:
    if agreement.status not in (
        AgreementStatus.DRAFT,
        AgreementStatus.PENDING_CONSENT,
        AgreementStatus.ACTIVE,
    ):
        return False
    return agreement.parties.count() >= 2


def can_seal(agreement) -> bool:
    """Agreement can be sealed from PENDING_CONSENT (new flow) or ACTIVE (legacy flow).

    PENDING_CONSENT path: all parties must have consented (ConsentRecord.granted).
    ACTIVE path: consent was already verified at the all_consented transition.
    Both paths require at least one confirmed evidence item.
    """
    if agreement.status not in (AgreementStatus.PENDING_CONSENT, AgreementStatus.ACTIVE):
        return False
    if not agreement.evidence_items.filter(upload_status="confirmed").exists():
        return False
    if agreement.status == AgreementStatus.PENDING_CONSENT:
        # Avoid a circular import by doing the import here.
        from apps.consent.selectors import ConsentSelector  # noqa: PLC0415
        return ConsentSelector.all_parties_consented(agreement_id=agreement.pk)
    return True  # ACTIVE: consent was already verified when transitioning from PENDING_CONSENT.


def can_reopen(agreement) -> bool:
    """Legacy single-party reopen check (24-hour window)."""
    if agreement.status != AgreementStatus.SEALED:
        return False
    if agreement.sealed_at is None:
        return False
    reopen_window = timedelta(hours=24)
    return timezone.now() <= agreement.sealed_at + reopen_window


def can_request_reopen(agreement) -> bool:
    """Bilateral reopen request is allowed on any sealed agreement."""
    return agreement.status == AgreementStatus.SEALED


def all_parties_confirmed_reopen(agreement_id: int) -> bool:
    """Return True when every party has a granted reopen-consent OTP record."""
    from apps.consent.models import ConsentRecord  # noqa: PLC0415
    from apps.parties.models import Party  # noqa: PLC0415

    party_ids = set(Party.objects.filter(agreement_id=agreement_id).values_list("pk", flat=True))
    if not party_ids:
        return False
    confirmed_ids = set(
        ConsentRecord.objects.filter(
            agreement_id=agreement_id,
            purpose=ConsentRecord.Purpose.REOPEN,
            granted=True,
        ).values_list("party_id", flat=True)
    )
    return party_ids == confirmed_ids


def can_annotate(agreement) -> bool:
    """Post-seal annotations are allowed on sealed or reopen_requested agreements."""
    return agreement.status in (
        AgreementStatus.SEALED,
        AgreementStatus.REOPEN_REQUESTED,
    )
