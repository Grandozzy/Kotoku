from rest_framework import serializers

_E164_PATTERN = r"^\+[1-9]\d{7,14}$"


class RequestOtpSerializer(serializers.Serializer):
    pass  # No body; agreement_id comes from the URL.


class ConfirmConsentSerializer(serializers.Serializer):
    party_phone = serializers.RegexField(_E164_PATTERN, max_length=20)
    otp_code = serializers.CharField(max_length=8, min_length=1)


class PublicConsentConfirmSerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=8, min_length=1)


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


class PublicConsentPartySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    role = serializers.CharField()
    display_name = serializers.CharField()
    phone = serializers.CharField()


class PublicConsentAgreementSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    scenario_template = serializers.CharField()
    status = serializers.CharField()
    field_data = serializers.DictField()


class PublicConsentEvidenceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    evidence_type = serializers.CharField()
    file_type = serializers.CharField()
    mime_type = serializers.CharField()
    size_bytes = serializers.IntegerField(allow_null=True)
    original_name = serializers.CharField()
    upload_status = serializers.CharField()
    uploaded_by_role = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    view_url = serializers.URLField(allow_null=True)


class PublicConsentContextSerializer(serializers.Serializer):
    agreement = PublicConsentAgreementSerializer()
    party = PublicConsentPartySerializer()
    parties = PublicConsentPartySerializer(many=True)
    evidence = PublicConsentEvidenceSerializer(many=True)
    consent_record = ConsentRecordOutputSerializer(allow_null=True)
    all_consented = serializers.BooleanField()
