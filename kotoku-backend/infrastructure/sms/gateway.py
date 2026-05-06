import json
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
        self.sender_id = getattr(settings, "SMS_SENDER_ID", "")

    def send(self, to: str, body: str) -> bool:
        if not self.api_key:
            raise RuntimeError(
                "SMS_API_KEY is not configured. Set SMS_API_KEY in your environment."
            )
        data = {
            "username": self.username,
            "to": to,
            "message": body,
            "bulkSMSMode": 1,
        }
        if self.sender_id:
            data["from"] = self.sender_id
        payload = urllib.parse.urlencode(data).encode()
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
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                sms_data = result.get("SMSMessageData", {})
                recipients = sms_data.get("Recipients", [])
                if recipients and recipients[0].get("status") == "Success":
                    logger.info("SMS sent successfully to %s (messageId: %s)", to, recipients[0].get("messageId"))
                    return True
                logger.warning("SMS not delivered to %s: %s", to, sms_data.get("Message", "unknown error"))
                return False
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logger.exception("SMS gateway HTTP error %d for %s: %s", e.code, to, error_body)
            return False
        except Exception:
            logger.exception("SMS gateway error for destination %s", to)
            return False
