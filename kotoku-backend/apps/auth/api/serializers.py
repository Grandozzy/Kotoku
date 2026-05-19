import re

from rest_framework import serializers

_E164_PATTERN = r"^\+[1-9]\d{7,14}$"


class SendOtpSerializer(serializers.Serializer):
    phone = serializers.RegexField(_E164_PATTERN, max_length=20)


class VerifyOtpSerializer(serializers.Serializer):
    phone = serializers.RegexField(_E164_PATTERN, max_length=20)
    otp_code = serializers.CharField(min_length=8, max_length=8)


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class PinSetupSerializer(serializers.Serializer):
    pin = serializers.CharField(min_length=4, max_length=4)

    def validate_pin(self, value: str) -> str:
        if not re.fullmatch(r"\d{4}", value):
            raise serializers.ValidationError("PIN must be exactly 4 digits.")
        return value


class PinVerifySerializer(serializers.Serializer):
    phone = serializers.RegexField(_E164_PATTERN, max_length=20)
    pin = serializers.CharField(min_length=4, max_length=4)

    def validate_pin(self, value: str) -> str:
        if not re.fullmatch(r"\d{4}", value):
            raise serializers.ValidationError("PIN must be exactly 4 digits.")
        return value
