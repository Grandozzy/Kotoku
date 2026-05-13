from rest_framework import serializers

from apps.vault.models import VaultEntry
from infrastructure.storage.s3 import S3StorageClient

_PDF_SIGNED_URL_TTL = 3600  # 1 hour


class PartySummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    role = serializers.CharField()
    display_name = serializers.CharField()
    phone = serializers.CharField()
    id_type = serializers.CharField(allow_null=True)
    id_number = serializers.CharField(allow_null=True)


class AgreementSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    status = serializers.CharField()
    scenario_template = serializers.CharField()
    sealed_at = serializers.DateTimeField()
    seal_hash = serializers.CharField()
    created_by_phone = serializers.CharField(source="created_by.phone")
    parties = PartySummarySerializer(source="parties.all", many=True, read_only=True)


class VaultEntrySerializer(serializers.ModelSerializer):
    agreement = AgreementSummarySerializer(read_only=True)
    # Presigned download URL generated on the fly — never a stored permanent URL.
    # Null when pdf_status is not READY or when no key is stored yet.
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = VaultEntry
        fields = (
            "id",
            "agreement",
            "pdf_status",
            "pdf_url",
            "retain_until",
            "archived",
            "created_at",
            "updated_at",
        )

    def get_pdf_url(self, obj: VaultEntry) -> str | None:
        if obj.pdf_status != VaultEntry.PdfStatus.READY or not obj.pdf_key:
            return None
        try:
            return S3StorageClient().generate_presigned_url(
                obj.pdf_key, expires_in=_PDF_SIGNED_URL_TTL
            )
        except Exception:
            return None
