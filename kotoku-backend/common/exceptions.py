class DomainError(Exception):
    """Base application exception."""


class ServiceUnavailableError(DomainError):
    """Controlled infrastructure or dependency failure."""
