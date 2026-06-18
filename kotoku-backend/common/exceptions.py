class DomainError(Exception):
    """Base application exception."""

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code


class ServiceUnavailableError(DomainError):
    """Controlled infrastructure or dependency failure."""
