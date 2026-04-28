import logging
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


class SmsGateway:
    def __init__(self) -> None:
        self.api_url = getattr(settings, "SMS_API_URL", "https://api.africastalking.com/version1/messaging")
        self.api_key = getattr(settings, "SMS_API_KEY", "")
        self.username = getattr(settings, "SMS_USERNAME", "sandbox")
        self.sender_id = getattr(settings, "SMS_SENDER_ID", "KOTOKU")

    def send(self, to: str, body: str) -> bool:
        if not self.api_key:
            raise RuntimeError(
                "SMS_API_KEY is not configured. Set SMS_API_KEY in your environment."
            )
        # Africa's Talking requires application/x-www-form-urlencoded
        payload = urllib.parse.urlencode({
            "username": self.username,
            "to": to,
            "message": body,
            "from": self.sender_id,
        }).encode()
        req = urllib.request.Request(
            self.api_url,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "apiKey": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200 or resp.status == 201
        except Exception:
            logger.exception("SMS gateway error for destination %s", to)
            return False
