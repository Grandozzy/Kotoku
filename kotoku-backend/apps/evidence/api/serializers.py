from rest_framework import serializers

from apps.evidence.models import EvidenceItem

_ALLOWED_MIME_TYPES = [
    "image/jpeg",
    "image/png",
    "audio/wav",
    "audio/ogg",
    "audio/mpeg",
    "application/pdf",
]


class UploadUrlRequestSerializer(serializers.Serializer):
    evidence_type = serializers.RegexField(
        r"^[a-z][a-z0-9_]{1,126}$",
        help_text="Semantic slot name, e.g. 'vehicle_photo_front'.",
    )
    mime_type = serializers.ChoiceField(choices=_ALLOWED_MIME_TYPES)
    size_bytes = serializers.IntegerField(min_value=1)


class UploadUrlResponseSerializer(serializers.Serializer):
    upload_url = serializers.URLField()
    file_key = serializers.CharField()
    headers = serializers.DictField(child=serializers.CharField())
    evidence_id = serializers.IntegerField()


class ConfirmUploadSerializer(serializers.Serializer):
    file_key = serializers.CharField(max_length=512)
    evidence_type = serializers.RegexField(r"^[a-z][a-z0-9_]{1,126}$")
    mime_type = serializers.ChoiceField(choices=_ALLOWED_MIME_TYPES)


class EvidenceItemSerializer(serializers.ModelSerializer):
    uploaded_by_role = serializers.SerializerMethodField()

    class Meta:
        model = EvidenceItem
        fields = (
            "id",
            "evidence_type",
            "file_type",
            "mime_type",
            "size_bytes",
            "file_key",
            "storage_url",
            "upload_status",
            "uploaded_by_role",
            "created_at",
        )

    def get_uploaded_by_role(self, obj) -> str | None:
        return obj.uploaded_by.role if obj.uploaded_by_id else None
