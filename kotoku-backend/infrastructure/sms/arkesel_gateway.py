import json
import logging
import urllib.error
import urllib.request
from urllib.parse import urlparse

from django.conf import settings

logger = logging.getLogger(__name__)


class ArkeselSmsGateway:
    def __init__(self) -> None:
        self.api_url = getattr(
            settings,
            "ARKESEL_SMS_URL",
            "https://sms.arkesel.com/api/v2/sms/send",
        )
        self.api_key = getattr(settings, "ARKESEL_API_KEY", "")
        self.sender_id = getattr(settings, "ARKESEL_SENDER_ID", "")

    @staticmethod
    def _mask_phone(phone: str) -> str:
        if len(phone) <= 5:
            return phone
        return f"{phone[:4]}***{phone[-3:]}"

    def _log_context(self, to: str) -> dict[str, str]:
        endpoint = urlparse(self.api_url)
        return {
            "provider": "arkesel",
            "sender_id": self.sender_id or "<default>",
            "endpoint_host": endpoint.netloc,
            "endpoint_path": endpoint.path,
            "to_masked": self._mask_phone(to),
        }

    def send(self, to: str, body: str) -> bool:
        if not self.api_key:
            raise RuntimeError(
                "ARKESEL_API_KEY is not configured. Set ARKESEL_API_KEY in your environment."
            )

        log_context = self._log_context(to)
        payload = {
            "sender": self.sender_id or "Kotoku",
            "message": body,
            "recipients": [to],
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            self.api_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "api-key": self.api_key,
                "User-Agent": "KotokuApp/1.0 (+https://kotoku-app.com)",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                if resp.status == 200 and result.get("status") == "success":
                    logger.info(
                        "SMS accepted by Arkesel gateway",
                        extra={"sms": {**log_context, "response": result}},
                    )
                    return True

                logger.warning(
                    "SMS rejected by Arkesel gateway",
                    extra={"sms": {**log_context, "response": result}},
                )
                return False
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logger.error(
                "Arkesel SMS gateway HTTP error http_status=%s error_body=%s",
                e.code,
                error_body,
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
            logger.exception("Arkesel SMS gateway error", extra={"sms": log_context})
            return False
