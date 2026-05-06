from infrastructure.sms import get_sms_gateway

from .base import NotificationProvider


class SmsNotificationProvider(NotificationProvider):
    def __init__(self) -> None:
        self.gateway = get_sms_gateway()

    def send(self, to: str, body: str) -> bool:
        return self.gateway.send(to, body)
