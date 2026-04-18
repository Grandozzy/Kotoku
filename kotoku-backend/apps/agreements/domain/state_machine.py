from __future__ import annotations

from apps.agreements.domain.enums import AgreementStatus
from common.exceptions import DomainError

_TRANSITIONS: dict[tuple[str, str], str] = {
    (AgreementStatus.DRAFT, "add_party"): AgreementStatus.DRAFT,
    (AgreementStatus.DRAFT, "request_consent"): AgreementStatus.PENDING_CONSENT,
    (AgreementStatus.PENDING_CONSENT, "all_consented"): AgreementStatus.ACTIVE,
    (AgreementStatus.ACTIVE, "seal"): AgreementStatus.SEALED,
    (AgreementStatus.SEALED, "close"): AgreementStatus.CLOSED,
    (AgreementStatus.SEALED, "reopen"): AgreementStatus.ACTIVE,
}


def next_state(current: str, action: str) -> str:
    key = (current, action)
    if key not in _TRANSITIONS:
        raise DomainError(
            f"Invalid transition: cannot perform '{action}' from '{current}'"
        )
    return _TRANSITIONS[key]


def valid_actions(current: str) -> list[str]:
    return [action for (state, action) in _TRANSITIONS if state == current]
