from rest_framework import serializers

from apps.agreements.models import Agreement


class AgreementCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default="", allow_blank=True)
    scenario_template = serializers.CharField(
        max_length=128, required=False, default="", allow_blank=True
    )


class AgreementUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    scenario_template = serializers.CharField(
        max_length=128, required=False, allow_blank=True
    )


class PartySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    role = serializers.CharField()
    display_name = serializers.CharField()


class AgreementListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agreement
        fields = ("id", "title", "status", "scenario_template", "created_at", "updated_at")


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
            "sealed_at",
            "closed_at",
            "created_at",
            "updated_at",
            "parties",
        )
