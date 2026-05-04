from rest_framework import serializers

from apps.vault.models import VaultEntry


class PartyInlineSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    display_name = serializers.CharField()
    role = serializers.CharField()
    phone = serializers.SerializerMethodField()

    def get_phone(self, obj):
        if hasattr(obj, "identity") and hasattr(obj.identity, "account"):
            return obj.identity.account.phone
        return ""


class EvidenceInlineSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    file_type = serializers.CharField()
    original_name = serializers.CharField()
    file_hash = serializers.CharField()


class ConsentInlineSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    actor = serializers.SerializerMethodField()
    granted = serializers.BooleanField()
    granted_at = serializers.DateTimeField()

    def get_actor(self, obj):
        return obj.party.display_name if hasattr(obj, "party") else ""


class VaultListSerializer(serializers.ModelSerializer):
    agreement_id = serializers.IntegerField(source="agreement.pk")
    agreement_title = serializers.CharField(source="agreement.title")
    agreement_status = serializers.CharField(source="agreement.status")

    class Meta:
        model = VaultEntry
        fields = (
            "id",
            "agreement_id",
            "agreement_title",
            "agreement_status",
            "sealed_at",
            "export_status",
            "retention_until",
        )


class VaultDetailSerializer(serializers.ModelSerializer):
    agreement_id = serializers.IntegerField(source="agreement.pk")
    agreement_title = serializers.CharField(source="agreement.title")
    agreement_status = serializers.CharField(source="agreement.status")
    agreement_description = serializers.CharField(
        source="agreement.description", default=""
    )
    parties = PartyInlineSerializer(many=True, source="agreement.parties.all")
    evidence_items = EvidenceInlineSerializer(
        many=True, source="agreement.evidence_items.all"
    )
    consent_records = ConsentInlineSerializer(
        many=True, source="agreement.consent_records.all"
    )
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = VaultEntry
        fields = (
            "id",
            "agreement_id",
            "agreement_title",
            "agreement_status",
            "agreement_description",
            "sealed_at",
            "export_status",
            "retention_until",
            "is_free_retention",
            "parties",
            "evidence_items",
            "consent_records",
            "pdf_url",
        )

    def get_pdf_url(self, obj):
        if obj.pdf_storage_key:
            from infrastructure.storage.urls import build_storage_url

            return build_storage_url(obj.pdf_storage_key)
        return None


class ExportTriggerResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    pdf_url = serializers.CharField(required=False, allow_null=True)
