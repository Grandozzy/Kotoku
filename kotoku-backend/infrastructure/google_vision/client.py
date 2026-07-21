import base64
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from common.exceptions import ServiceUnavailableError

logger = logging.getLogger("kotoku")

_VISION_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
_VISION_ANNOTATE_URL = "https://vision.googleapis.com/v1/images:annotate"


class GoogleVisionClient:
    def __init__(self) -> None:
        try:
            from google.auth.transport.requests import Request as GoogleAuthRequest
            from google.oauth2 import service_account
        except ImportError as exc:
            logger.exception("[IDENTITY] google_vision_dependency_missing")
            raise ServiceUnavailableError(
                "Identity verification is temporarily unavailable. Please try again later."
            ) from exc

        raw_credentials = getattr(settings, "GOOGLE_VISION_SERVICE_ACCOUNT_JSON", "")
        if not raw_credentials:
            raise ServiceUnavailableError(
                "Identity verification is temporarily unavailable. Please try again later."
            )
        try:
            info = json.loads(raw_credentials)
        except json.JSONDecodeError as exc:
            logger.exception("[IDENTITY] invalid_google_vision_credentials_json")
            raise ServiceUnavailableError(
                "Identity verification is temporarily unavailable. Please try again later."
            ) from exc

        self._google_auth_request = GoogleAuthRequest
        self._credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=[_VISION_SCOPE],
        )
        self._timeout = float(getattr(settings, "GOOGLE_VISION_TIMEOUT_SECONDS", 20))

    def extract_document_text(self, image_bytes: bytes) -> str:
        credentials = self._credentials.with_scopes([_VISION_SCOPE])
        credentials.refresh(self._google_auth_request())

        payload: dict[str, object] = {
            "requests": [
                {
                    "image": {"content": base64.b64encode(image_bytes).decode("ascii")},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                }
            ]
        }
        request = Request(
            _VISION_ANNOTATE_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            logger.warning(
                "[IDENTITY] google_vision_http_error status=%s",
                exc.code,
            )
            raise ServiceUnavailableError(
                "Identity verification is temporarily unavailable. Please try again later."
            ) from exc
        except URLError as exc:
            logger.warning("[IDENTITY] google_vision_network_error")
            raise ServiceUnavailableError(
                "Identity verification is temporarily unavailable. Please try again later."
            ) from exc

        parsed = json.loads(body)
        responses = parsed.get("responses", [])
        if not responses:
            return ""
        result = responses[0]
        if result.get("error"):
            logger.warning(
                "[IDENTITY] google_vision_response_error code=%s",
                result["error"].get("code"),
            )
            raise ServiceUnavailableError(
                "Identity verification is temporarily unavailable. Please try again later."
            )
        full_text = result.get("fullTextAnnotation", {}).get("text")
        if full_text:
            return str(full_text)
        annotations = result.get("textAnnotations", [])
        if annotations:
            return str(annotations[0].get("description", ""))
        return ""
