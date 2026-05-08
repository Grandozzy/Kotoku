from rest_framework import serializers

from apps.agreements.models import Agreement, AgreementRevision


class AgreementCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default="", allow_blank=True)
    scenario_id = serializers.CharField(
        max_length=128, required=False, default="", allow_blank=True, source="scenario_template"
    )


class AgreementUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    scenario_id = serializers.CharField(
        max_length=128, required=False, default="", allow_blank=True, source="scenario_template"
    )
    field_data = serializers.JSONField(required=False)


class PartySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    role = serializers.CharField()
    display_name = serializers.CharField()
    phone = serializers.CharField()
    id_type = serializers.CharField()
    id_number = serializers.CharField()


class AgreementListSerializer(serializers.ModelSerializer):
    parties = PartySerializer(many=True, read_only=True)

    class Meta:
        model = Agreement
        fields = ("id", "title", "status", "scenario_template", "field_data", "created_at", "updated_at", "parties")


class AgreementDetailSerializer(serializers.ModelSerializer):
    parties = PartySerializer(many=True, read_only=True)

    class Meta:
        model = Agreement
        fields = (
            "id",
            "title",
            "description",
            "status",
            "scenario_template",
            "field_data",
            "sealed_at",
            "seal_hash",
            "closed_at",
            "created_at",
            "updated_at",
            "parties",
        )


class AgreementRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgreementRevision
        fields = ("id", "revision_number", "seal_hash", "sealed_at", "created_at")
