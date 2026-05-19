import re
from typing import Dict, Any

from rest_framework import serializers

from apps.auth.services import PhoneService


class SendOtpSerializer(serializers.Serializer):
    country_code = serializers.RegexField(r'^\+[1-9]\d{1,3}$', max_length=6)
    phone_number = serializers.RegexField(r'^\d{7,15}$', max_length=15)


class VerifyOtpSerializer(serializers.Serializer):
    country_code = serializers.RegexField(r'^\+[1-9]\d{1,3}$', max_length=6)
    phone_number = serializers.RegexField(r'^\d{7,15}$', max_length=15)
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
    country_code = serializers.RegexField(r'^\+[1-9]\d{1,3}$', max_length=6)
    phone_number = serializers.RegexField(r'^\d{7,15}$', max_length=15)
    pin = serializers.CharField(min_length=4, max_length=4)

    def validate_pin(self, value: str) -> str:
        if not re.fullmatch(r"\d{4}", value):
            raise serializers.ValidationError("PIN must be exactly 4 digits.")
        return value

    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Combine country_code and phone_number into E164 format."""
        internal = super().to_internal_value(data)
        internal['phone'] = f"{internal['country_code']}{internal['phone_number']}"
        return internal


class PhoneInputSerializer(serializers.Serializer):
    """Internal serializer for frontend PhoneInput component."""
    country_code = serializers.RegexField(r'^\+[1-9]\d{1,3}$', max_length=6)
    phone_number = serializers.RegexField(r'^\d{7,15}$', max_length=15)

    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Combine country_code and phone_number into E164 format."""
        internal = super().to_internal_value(data)
        internal['phone'] = f"{internal['country_code']}{internal['phone_number']}"
        return internal