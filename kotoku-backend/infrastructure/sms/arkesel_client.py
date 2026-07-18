import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

from common.exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)

# Arkesel OTP API response codes.
CODE_SEND_OK = "1000"      # OTP sent successfully.
CODE_VERIFY_OK = "1100"    # OTP verified successfully.


class ArkeselOtpClient:
    """Thin client for the Arkesel OTP API (send + verify)."""

    def __init__(self) -> None:
        self.api_key = getattr(settings, "ARKESEL_API_KEY", "")
        self.base_url = getattr(
            settings,
            "ARKESEL_SMS_URL",
            "https://sms.arkesel.com/api/v2/otp",
        ).rstrip("/")
        self.sender_id = getattr(settings, "ARKESEL_SENDER_ID", "")

    @staticmethod
    def _mask_phone(phone: str) -> str:
        if len(phone) <= 5:
            return phone
        return f"{phone[:4]}***{phone[-3:]}"

    def _headers(self) -> dict[str, str]:
        return {
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(
        self,
        endpoint: str,
        payload: dict,
        success_code: str,
        log_context: dict,
        operation: str,
    ) -> bool:
        """POST to Arkesel and return True if response code matches success_code.

        Raises ServiceUnavailableError for HTTP errors and connection failures
        so callers can distinguish infrastructure faults from rejected codes.
        """
        if not self.api_key:
            raise RuntimeError(
                "ARKESEL_API_KEY is not configured. Set ARKESEL_API_KEY in your environment."
            )

        data = json.dumps(payload).encode()
        url = f"{self.base_url}/{endpoint}"
        req = urllib.request.Request(
            url,
            data=data,
            headers=self._headers(),
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                response_code = result.get("code", "")
                if response_code == success_code:
                    logger.info(
                        "Arkesel %s succeeded", operation,
                        extra={"otp": {**log_context, "response": result}},
                    )
                    return True
                logger.info(
                    "Arkesel %s rejected", operation,
                    extra={"otp": {**log_context, "response": result}},
                )
                return False
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logger.exception(
                "Arkesel %s HTTP error", operation,
                extra={
                    "otp": {**log_context, "http_status": e.code, "error_body": error_body}
                },
            )
            raise ServiceUnavailableError(
                "OTP service is temporarily unavailable. Please try again."
            ) from e
        except Exception as e:
            logger.exception("Arkesel %s error", operation, extra={"otp": log_context})
            raise ServiceUnavailableError(
                "OTP service is temporarily unavailable. Please try again."
            ) from e

    def send_otp(
        self,
        *,
        number: str,
        message: str,
        expiry: int = 5,
        length: int = 6,
        medium: str = "sms",
    ) -> bool:
        """Send an OTP via Arkesel. Arkesel generates, stores, and delivers the code."""
        log_context = {
            "provider": "arkesel",
            "sender_id": self.sender_id or "<default>",
            "number_masked": self._mask_phone(number),
            "medium": medium,
            "expiry": expiry,
            "length": length,
        }
        return self._request(
            endpoint="send",
            payload={
                "number": number,
                "message": message,
                "sender_id": self.sender_id,
                "type": "numeric",
                "expiry": expiry,
                "length": length,
                "medium": medium,
            },
            success_code=CODE_SEND_OK,
            log_context=log_context,
            operation="send_otp",
        )

    def verify_otp(self, *, number: str, code: str) -> bool:
        """Verify an OTP code against Arkesel's server-side storage."""
        log_context = {
            "provider": "arkesel",
            "number_masked": self._mask_phone(number),
        }
        return self._request(
            endpoint="verify",
            payload={
                "code": code,
                "number": number,
            },
            success_code=CODE_VERIFY_OK,
            log_context=log_context,
            operation="verify_otp",
        )
