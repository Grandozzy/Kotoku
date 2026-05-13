from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auth.api.serializers import SendOtpSerializer, VerifyOtpSerializer
from apps.auth.services import AuthService
from common.responses import ok


class SendOtpView(APIView):
    def post(self, request):
        serializer = SendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.send_otp(phone=serializer.validated_data["phone"])
        return ok({"message": "OTP sent"})


class VerifyOtpView(APIView):
    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthService.verify_otp(
            phone=serializer.validated_data["phone"],
            otp_code=serializer.validated_data["otp_code"],
        )
        user = result["user"]
        refresh = RefreshToken.for_user(user)
        return ok({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "is_new_user": result["is_new"],
            "account_id": user.account.pk,
        })
