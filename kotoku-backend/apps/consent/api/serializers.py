from rest_framework import serializers

_E164_PATTERN = r"^\+[1-9]\d{7,14}$"


class RequestOtpSerializer(serializers.Serializer):
    pass  # No body; agreement_id comes from the URL.


class ConfirmConsentSerializer(serializers.Serializer):
    party_phone = serializers.RegexField(_E164_PATTERN, max_length=20)
    otp_code = serializers.CharField(max_length=6, min_length=6)


class ConsentRecordOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    party_id = serializers.IntegerField(source="party.pk")
    party_phone = serializers.CharField(source="party.phone")
    channel = serializers.CharField()
    granted = serializers.BooleanField()
    granted_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()


class ConsentStatusOutputSerializer(serializers.Serializer):
    """Summary of consent status for an agreement."""
    agreement_id = serializers.IntegerField()
    all_consented = serializers.BooleanField()
    records = ConsentRecordOutputSerializer(many=True)
