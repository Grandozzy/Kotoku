from rest_framework import serializers

_E164_PATTERN = r"^\+[1-9]\d{7,14}$"


class SendOtpSerializer(serializers.Serializer):
    phone = serializers.RegexField(_E164_PATTERN, max_length=20)


class VerifyOtpSerializer(serializers.Serializer):
    phone = serializers.RegexField(_E164_PATTERN, max_length=20)
    otp_code = serializers.CharField(max_length=8)
