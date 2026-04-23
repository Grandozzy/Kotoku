from rest_framework.authtoken.models import Token
from rest_framework.views import APIView

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
        token, _ = Token.objects.get_or_create(user=result["user"])
        return ok({"token": token.key, "is_new_user": result["is_new"]})
