import json
import logging
import urllib.parse
import urllib.request
from urllib.parse import urlparse

from django.conf import settings

logger = logging.getLogger(__name__)


class SmsGateway:
    def __init__(self) -> None:
        self.api_url = getattr(settings, "SMS_API_URL", "https://api.africastalking.com/version1/messaging")
        self.api_key = getattr(settings, "SMS_API_KEY", "")
        self.username = getattr(settings, "SMS_USERNAME", "sandbox")
        self.sender_id = getattr(settings, "SMS_SENDER_ID", "")

    def _mode(self) -> str:
        return "sandbox" if self.username == "sandbox" else "live"

    @staticmethod
    def _mask_phone(phone: str) -> str:
        if len(phone) <= 5:
            return phone
        return f"{phone[:4]}***{phone[-3:]}"

    def _log_context(self, to: str) -> dict[str, str]:
        endpoint = urlparse(self.api_url)
        return {
            "mode": self._mode(),
            "username": self.username,
            "sender_id": self.sender_id or "<default>",
            "endpoint_host": endpoint.netloc,
            "endpoint_path": endpoint.path,
            "to_masked": self._mask_phone(to),
        }

    def send(self, to: str, body: str) -> bool:
        if not self.api_key:
            raise RuntimeError(
                "SMS_API_KEY is not configured. Set SMS_API_KEY in your environment."
            )
        log_context = self._log_context(to)
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
                if recipients:
                    recipient = recipients[0]
                    recipient_status = recipient.get("status")
                    recipient_payload = {
                        "message_id": recipient.get("messageId"),
                        "status": recipient_status,
                        "status_code": recipient.get("statusCode"),
                        "number": recipient.get("number"),
                        "cost": recipient.get("cost"),
                    }
                else:
                    recipient = {}
                    recipient_status = None
                    recipient_payload = None
                if recipient_status == "Success":
                    logger.info(
                        "SMS accepted by gateway",
                        extra={
                            "sms": {
                                **log_context,
                                "provider_message": sms_data.get("Message"),
                                "recipient": recipient_payload,
                            }
                        },
                    )
                    return True
                logger.warning(
                    "SMS rejected by gateway",
                    extra={
                        "sms": {
                            **log_context,
                            "provider_message": sms_data.get("Message", "unknown error"),
                            "recipient": recipient_payload,
                        }
                    },
                )
                return False
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logger.exception(
                "SMS gateway HTTP error",
                extra={
                    "sms": {
                        **log_context,
                        "http_status": e.code,
                        "error_body": error_body,
                    }
                },
            )
            return False
        except Exception:
            logger.exception(
                "SMS gateway error",
                extra={"sms": log_context},
            )
            return False
