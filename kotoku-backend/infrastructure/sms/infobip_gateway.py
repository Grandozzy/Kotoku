import json
import logging
import re
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

_OTP_RE = re.compile(r"\b(\d{4})\b")


class InfobipSmsGateway:
    def __init__(self) -> None:
        self.api_key = getattr(settings, "INFOBIP_API_KEY", "")
        self.base_url = getattr(settings, "INFOBIP_BASE_URL", "").rstrip("/")
        self.sms_sender = getattr(settings, "INFOBIP_SMS_SENDER", "")
        self.whatsapp_number = getattr(settings, "INFOBIP_WHATSAPP_NUMBER", "")
        self.whatsapp_template = getattr(settings, "INFOBIP_WHATSAPP_TEMPLATE_NAME", "")
        self.sms_timeout = int(getattr(settings, "INFOBIP_SMS_TIMEOUT_SECONDS", 30))

    @staticmethod
    def _mask_phone(phone: str) -> str:
        if len(phone) <= 5:
            return phone
        return f"{phone[:4]}***{phone[-3:]}"

    @staticmethod
    def _extract_otp(body: str) -> str:
        match = _OTP_RE.search(body)
        return match.group(1) if match else body

    def _build_payload(self, to: str, body: str) -> dict:
        flow: list[dict] = [{"from": self.sms_sender, "channel": "SMS"}]
        has_whatsapp = bool(self.whatsapp_number and self.whatsapp_template)
        if has_whatsapp:
            flow.append({"from": self.whatsapp_number, "channel": "WHATSAPP"})

        payload: dict = {
            "scenarios": [{"name": "OTP_SMS_WA_FALLBACK", "flow": flow}],
            "destinations": [{"to": {"phoneNumber": to}}],
            "sms": {"text": body},
            "options": {
                "scheduling": {
                    "smsTimeout": {"timeout": self.sms_timeout, "timeUnit": "SECONDS"}
                }
            },
        }
        if has_whatsapp:
            payload["whatsApp"] = {
                "templateName": self.whatsapp_template,
                "templateData": [self._extract_otp(body)],
                "language": "en",
            }
        return payload

    def send(self, to: str, body: str) -> bool:
        if not self.api_key:
            raise RuntimeError(
                "INFOBIP_API_KEY is not configured. Set INFOBIP_API_KEY in your environment."
            )
        if not self.base_url:
            raise RuntimeError(
                "INFOBIP_BASE_URL is not configured. Set INFOBIP_BASE_URL in your environment."
            )

        log_context = {
            "provider": "infobip",
            "sms_sender": self.sms_sender or "<default>",
            "whatsapp_fallback": bool(self.whatsapp_number and self.whatsapp_template),
            "sms_timeout_seconds": self.sms_timeout,
            "to_masked": self._mask_phone(to),
        }

        url = f"{self.base_url}/omni/1/advanced"
        payload = self._build_payload(to, body)
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"App {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                messages = result.get("messages", [])
                if not messages:
                    logger.warning(
                        "Infobip returned empty messages list",
                        extra={"sms": {**log_context, "response": result}},
                    )
                    return False
                status = messages[0].get("status", {})
                group_name = status.get("groupName", "")
                message_id = messages[0].get("messageId", "")
                # PENDING means accepted and in-flight (omnichannel fallback may kick in)
                if group_name in ("PENDING", "DELIVERED"):
                    logger.info(
                        "SMS accepted by Infobip",
                        extra={
                            "sms": {
                                **log_context,
                                "message_id": message_id,
                                "status_group": group_name,
                                "status_description": status.get("description", ""),
                            }
                        },
                    )
                    return True
                logger.warning(
                    "SMS rejected by Infobip",
                    extra={
                        "sms": {
                            **log_context,
                            "message_id": message_id,
                            "status_group": group_name,
                            "status_description": status.get("description", ""),
                        }
                    },
                )
                return False
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logger.exception(
                "Infobip gateway HTTP error",
                extra={
                    "sms": {**log_context, "http_status": e.code, "error_body": error_body}
                },
            )
            return False
        except Exception:
            logger.exception("Infobip gateway error", extra={"sms": log_context})
            return False
