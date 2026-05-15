from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.models import DeviceSession
from apps.auth.api.serializers import (
    PinSetupSerializer,
    PinVerifySerializer,
    RefreshTokenSerializer,
    SendOtpSerializer,
    VerifyOtpSerializer,
)
from apps.auth.services import AuthService, PinService, TokenService
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


class SendOtpView(APIView):
    def post(self, request):
        serializer = SendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.send_otp(phone=serializer.validated_data["phone"])
        return ok({"message": "OTP sent", "expires_in_seconds": 600})


class VerifyOtpView(APIView):
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
        return ok(result)


class RefreshTokenView(APIView):
    """Custom refresh view that validates against device_sessions (opaque tokens)."""
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = TokenService.refresh(
                raw_token=serializer.validated_data["refresh"],
                client_type=_client_type(request),
            )
        except DomainError as exc:
            return ok({"detail": str(exc)}, status=401)
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
    permission_classes = [IsAuthenticated]

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
            pass
        return ok({"signed_out": True})


class SignOutAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = TokenService.revoke_all_sessions(
            user=request.user,
            reason=DeviceSession.REVOKE_SIGNOUT_ALL,
        )
        return ok({"sessions_revoked": count})
