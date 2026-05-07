from rest_framework import serializers

from apps.vault.models import VaultEntry


class AgreementSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    status = serializers.CharField()
    scenario_template = serializers.CharField()
    sealed_at = serializers.DateTimeField()
    seal_hash = serializers.CharField()
    created_by_phone = serializers.CharField(source="created_by.phone")


class VaultEntrySerializer(serializers.ModelSerializer):
    agreement = AgreementSummarySerializer(read_only=True)

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
