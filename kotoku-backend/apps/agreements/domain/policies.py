from datetime import timedelta

from django.utils import timezone

from apps.agreements.domain.enums import AgreementStatus


def can_request_consent(agreement) -> bool:
    if agreement.status != AgreementStatus.DRAFT:
        return False
    return agreement.parties.count() >= 2


def can_seal(agreement) -> bool:
    if agreement.status != AgreementStatus.ACTIVE:
        return False
    return agreement.evidence_items.exists()


def can_reopen(agreement) -> bool:
    if agreement.status != AgreementStatus.SEALED:
        return False
    if agreement.sealed_at is None:
        return False
    reopen_window = timedelta(hours=24)
    return timezone.now() <= agreement.sealed_at + reopen_window
