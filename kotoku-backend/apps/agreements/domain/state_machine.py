from __future__ import annotations

from apps.agreements.domain.enums import AgreementStatus
from common.exceptions import DomainError

_TRANSITIONS: dict[tuple[str, str], str] = {
    (AgreementStatus.DRAFT, "add_party"): AgreementStatus.DRAFT,
    (AgreementStatus.DRAFT, "request_consent"): AgreementStatus.PENDING_CONSENT,
    # Legacy path: all_consented transitions to ACTIVE (kept for backward compat).
    (AgreementStatus.PENDING_CONSENT, "all_consented"): AgreementStatus.ACTIVE,
    # New path: seal directly from PENDING_CONSENT once all parties have consented.
    (AgreementStatus.PENDING_CONSENT, "seal"): AgreementStatus.SEALED,
    (AgreementStatus.ACTIVE, "request_consent"): AgreementStatus.PENDING_CONSENT,
    (AgreementStatus.ACTIVE, "seal"): AgreementStatus.SEALED,
    (AgreementStatus.SEALED, "close"): AgreementStatus.CLOSED,
    # Legacy single-party reopen (kept for backward compat with existing service method).
    (AgreementStatus.SEALED, "reopen"): AgreementStatus.ACTIVE,
    # Sprint 6: bilateral reopen flow.
    (AgreementStatus.SEALED, "request_reopen"): AgreementStatus.REOPEN_REQUESTED,
    # When all parties confirm reopen OTPs, go back to ACTIVE for re-editing.
    (AgreementStatus.REOPEN_REQUESTED, "bilateral_confirm"): AgreementStatus.ACTIVE,
    # A reopen request can be cancelled (e.g. by the initiator or timeout).
    (AgreementStatus.REOPEN_REQUESTED, "cancel_reopen"): AgreementStatus.SEALED,
    # Archival and expiry are terminal states.
    (AgreementStatus.SEALED, "archive"): AgreementStatus.ARCHIVED,
    (AgreementStatus.CLOSED, "archive"): AgreementStatus.ARCHIVED,
    (AgreementStatus.SEALED, "expire"): AgreementStatus.EXPIRED,
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
