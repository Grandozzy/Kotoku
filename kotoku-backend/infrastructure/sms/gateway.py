import json
import logging
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


class SmsGateway:
    def __init__(self) -> None:
        self.api_url = getattr(settings, "SMS_API_URL", "https://api.africastalking.com/v1/messaging")
        self.api_key = getattr(settings, "SMS_API_KEY", "")
        self.sender_id = getattr(settings, "SMS_SENDER_ID", "KOTOKU")

    def send(self, to: str, body: str) -> bool:
        if not self.api_key:
            logger.info("SMS gateway stub: would send to %s", to)
            return True
        payload = json.dumps({
            "username": self.sender_id,
            "to": to,
            "message": body,
        }).encode()
        req = urllib.request.Request(
            self.api_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "apikey": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200 or resp.status == 201
        except Exception:
            logger.exception("SMS gateway error for destination %s", to)
            return False
