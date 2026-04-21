import logging

from .base import NotificationProvider

logger = logging.getLogger(__name__)


class StubNotificationProvider(NotificationProvider):
    """No-op provider for use in tests and local dev without SMS credentials.

    Records sent messages so tests can assert on them::

        provider = StubNotificationProvider()
        provider.send("+233...", "Your code is 123456")
        assert provider.sent[0] == ("+233...", "Your code is 123456")
    """

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, to: str, body: str) -> bool:
        logger.info("STUB SMS to %s: %s", to, body)
        self.sent.append((to, body))
        return True
