from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.models import DeviceSession, UserPin
from apps.auth.api.serializers import (
    PinSetupSerializer,
    PinVerifySerializer,
    RefreshTokenSerializer,
    SendOtpSerializer,
    VerifyOtpSerializer,
)
from apps.auth.services import AuthService, PinService, TokenService
from common.throttling import (
    AuthIpRateThrottle,
    PinVerifyPhoneRateThrottle,
    RefreshIpRateThrottle,
    SendOtpPhoneRateThrottle,
    VerifyOtpPhoneRateThrottle,
)
from common.exceptions import DomainError
from common.responses import ok


# Reads the client_type claim from an already-validated JWT (request.auth).
# Falls back to CLIENT_WEB so that tokens lacking the claim are treated
# as least-privileged.
def _jwt_client_type(request) -> str:
    try:
        return request.auth["client_type"]
    except (KeyError, TypeError):
        return DeviceSession.CLIENT_WEB


def _client_type(request) -> str:
    val = request.headers.get("X-Client-Type", "web").lower()
    return DeviceSession.CLIENT_MOBILE if val == "mobile" else DeviceSession.CLIENT_WEB


def _device_info(request) -> tuple[str, str]:
    fingerprint = request.headers.get("X-Device-Fingerprint", "")
    name = request.headers.get("X-Device-Name", "")
    return fingerprint, name


def _refresh_cookie_kwargs() -> dict:
    kwargs = {
        "path": settings.AUTH_REFRESH_COOKIE_PATH,
        "httponly": True,
        "secure": settings.AUTH_REFRESH_COOKIE_SECURE,
        "samesite": settings.AUTH_REFRESH_COOKIE_SAMESITE,
    }
    if settings.AUTH_REFRESH_COOKIE_DOMAIN:
        kwargs["domain"] = settings.AUTH_REFRESH_COOKIE_DOMAIN
    return kwargs


def _refresh_cookie_delete_kwargs() -> dict:
    kwargs = {
        "path": settings.AUTH_REFRESH_COOKIE_PATH,
        "samesite": settings.AUTH_REFRESH_COOKIE_SAMESITE,
    }
    if settings.AUTH_REFRESH_COOKIE_DOMAIN:
        kwargs["domain"] = settings.AUTH_REFRESH_COOKIE_DOMAIN
    return kwargs


def _set_web_refresh_cookie(response, refresh_token: str) -> None:
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=settings.AUTH_WEB_REFRESH_COOKIE_MAX_AGE,
        **_refresh_cookie_kwargs(),
    )


def _clear_web_refresh_cookie(response) -> None:
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        **_refresh_cookie_delete_kwargs(),
    )


def _web_token_response(result: dict, *, status_code: int = 200):
    response_payload = dict(result)
    refresh_token = response_payload.pop("refresh", "")
    response = ok(response_payload, status_code=status_code)
    if refresh_token:
        _set_web_refresh_cookie(response, refresh_token)
    return response


class SendOtpView(APIView):
    throttle_classes = [AuthIpRateThrottle, SendOtpPhoneRateThrottle]

    def post(self, request):
        serializer = SendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.send_otp(phone=serializer.validated_data["phone"])
        return ok({"message": "OTP sent", "expires_in_seconds": 600})


class VerifyOtpView(APIView):
    throttle_classes = [AuthIpRateThrottle, VerifyOtpPhoneRateThrottle]

    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fingerprint, name = _device_info(request)
        result = AuthService.verify_otp(
            phone=serializer.validated_data["phone"],
            otp_code=serializer.validated_data["otp_code"],
            client_type=_client_type(request),
            device_fingerprint=fingerprint,
            device_name=name,
        )
        # Service attaches User/Account model instances for testability.
        # Serialize them to dicts before sending the HTTP response.
        user = result.pop("user")
        account = result.pop("account", None)
        result["user"] = {
            "id": user.pk,
            "phone": user.phone,
            "pin_configured": UserPin.objects.filter(user=user).exists(),
            "account_id": account.pk if account else None,
        }
        if _client_type(request) == DeviceSession.CLIENT_WEB:
            return _web_token_response(result)
        return ok(result)


class RefreshTokenView(APIView):
    """Custom refresh view that validates against device_sessions (opaque tokens)."""
    throttle_classes = [RefreshIpRateThrottle]

    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client_type = _client_type(request)
        raw_token = serializer.validated_data.get("refresh", "")
        if client_type == DeviceSession.CLIENT_WEB:
            raw_token = raw_token or request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME, "")
        if not raw_token:
            response = ok({"detail": "Refresh token is required."}, status_code=401)
            if client_type == DeviceSession.CLIENT_WEB:
                _clear_web_refresh_cookie(response)
            return response
        try:
            result = TokenService.refresh(
                raw_token=raw_token,
                client_type=client_type,
            )
        except DomainError as exc:
            response = ok({"detail": str(exc)}, status_code=401)
            if client_type == DeviceSession.CLIENT_WEB:
                _clear_web_refresh_cookie(response)
            return response
        if client_type == DeviceSession.CLIENT_WEB:
            return _web_token_response(result)
        return ok(result)


class PinSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # PIN is mobile-only; reject web sessions.
        # Read from the validated JWT claim — not the spoofable X-Client-Type header.
        if _jwt_client_type(request) == DeviceSession.CLIENT_WEB:
            return ok({"detail": "PIN setup is not available for web sessions."}, status=403)

        serializer = PinSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            PinService.setup(user=request.user, pin=serializer.validated_data["pin"])
        except DomainError as exc:
            return ok({"detail": str(exc)}, status=400)
        return ok({"pin_configured": True})


class PinVerifyView(APIView):
    throttle_classes = [AuthIpRateThrottle, PinVerifyPhoneRateThrottle]

    def post(self, request):
        if _client_type(request) == DeviceSession.CLIENT_WEB:
            return ok({"detail": "PIN auth is not available for web sessions."}, status=403)

        serializer = PinVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fingerprint, name = _device_info(request)
        try:
            result = PinService.verify(
                phone=serializer.validated_data["phone"],
                pin=serializer.validated_data["pin"],
                client_type=DeviceSession.CLIENT_MOBILE,
                device_fingerprint=fingerprint,
                device_name=name,
            )
        except DomainError as exc:
            msg = str(exc)
            if msg == "__force_otp__":
                return ok({"force_otp": True}, status=403)
            # Check if locked
            if "Try again after" in msg:
                return ok({"detail": msg}, status=429)
            return ok({"detail": msg}, status=400)
        return ok(result)


class SignOutView(APIView):
    def post(self, request):
        # request.auth is already the validated JWT token (DRF + SimpleJWT).
        # Reading device_session_id from it avoids re-parsing the Bearer header.
        try:
            session_id = request.auth["device_session_id"]
            TokenService.revoke_session(
                session_id=session_id,
                reason=DeviceSession.REVOKE_LOGOUT,
            )
        except (KeyError, TypeError):
            raw_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME, "")
            if raw_token:
                try:
                    TokenService.revoke_raw_token(
                        raw_token=raw_token,
                        reason=DeviceSession.REVOKE_LOGOUT,
                    )
                except DomainError:
                    pass
        response = ok({"signed_out": True})
        if _client_type(request) == DeviceSession.CLIENT_WEB:
            _clear_web_refresh_cookie(response)
        return response


class SignOutAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = TokenService.revoke_all_sessions(
            user=request.user,
            reason=DeviceSession.REVOKE_SIGNOUT_ALL,
        )
        return ok({"sessions_revoked": count})
