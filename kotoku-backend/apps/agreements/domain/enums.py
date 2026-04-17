from enum import StrEnum


class AgreementStatus(StrEnum):
    DRAFT = "draft"
    PENDING_CONSENT = "pending_consent"
    ACTIVE = "active"
    SEALED = "sealed"
    CLOSED = "closed"
