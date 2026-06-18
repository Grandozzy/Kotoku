from django.conf import settings
from rest_framework import serializers

from apps.evidence.models import EvidenceItem
from infrastructure.storage.s3 import S3StorageClient

_ALLOWED_MIME_TYPES = [
    "image/jpeg",
    "image/png",
    "audio/wav",
    "audio/ogg",
    "audio/mpeg",
    "application/pdf",
]
_SHA256_HEX = r"^[a-f0-9]{64}$"


class UploadUrlRequestSerializer(serializers.Serializer):
    evidence_type = serializers.RegexField(
        r"^[a-z][a-z0-9_]{1,126}$",
        help_text="Semantic slot name, e.g. 'vehicle_photo_front'.",
    )
    mime_type = serializers.ChoiceField(choices=_ALLOWED_MIME_TYPES)
    size_bytes = serializers.IntegerField(min_value=1)
    checksum_sha256 = serializers.RegexField(
        _SHA256_HEX,
        help_text="Lowercase SHA-256 hex digest of the file bytes.",
    )


class UploadUrlResponseSerializer(serializers.Serializer):
    upload_url = serializers.URLField()
    file_key = serializers.CharField()
    headers = serializers.DictField(child=serializers.CharField())
    evidence_id = serializers.IntegerField()


class ConfirmUploadSerializer(serializers.Serializer):
    evidence_id = serializers.IntegerField(required=False, min_value=1)
    file_key = serializers.CharField(max_length=512)
    evidence_type = serializers.RegexField(r"^[a-z][a-z0-9_]{1,126}$")
    mime_type = serializers.ChoiceField(choices=_ALLOWED_MIME_TYPES)
    checksum_sha256 = serializers.RegexField(_SHA256_HEX)


class EvidenceItemSerializer(serializers.ModelSerializer):
    uploaded_by_role = serializers.SerializerMethodField()
    view_url = serializers.SerializerMethodField()

    class Meta:
        model = EvidenceItem
        fields = (
            "id",
            "evidence_type",
            "file_type",
            "mime_type",
            "size_bytes",
            "view_url",
            "upload_status",
            "uploaded_by_role",
            "created_at",
        )

    def get_uploaded_by_role(self, obj) -> str | None:
        return obj.uploaded_by.role if obj.uploaded_by_id else None

    def get_view_url(self, obj) -> str | None:
        if obj.upload_status != EvidenceItem.UploadStatus.CONFIRMED or not obj.file_key:
            return None
        return S3StorageClient().generate_presigned_view_url(
            obj.file_key,
            content_type=obj.mime_type,
            expires_in=settings.EVIDENCE_VIEW_URL_TTL_SECONDS,
        )
