from infrastructure.sms.gateway import SmsGateway

from .base import NotificationProvider


class SmsNotificationProvider(NotificationProvider):
    def __init__(self) -> None:
        self.gateway = SmsGateway()

    def send(self, to: str, body: str) -> bool:
        return self.gateway.send(to, body)
