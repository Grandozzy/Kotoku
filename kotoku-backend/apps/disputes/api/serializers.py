from rest_framework import serializers

from apps.disputes.models import Dispute


class DisputeCreateSerializer(serializers.Serializer):
    raised_by_party_id = serializers.IntegerField()
    reason = serializers.CharField(min_length=10, max_length=2000)


class DisputeSerializer(serializers.ModelSerializer):
    raised_by_party_id = serializers.IntegerField(source="raised_by.pk", read_only=True)
    raised_by_display_name = serializers.CharField(
        source="raised_by.display_name", read_only=True
    )
    agreement_id = serializers.IntegerField(source="agreement.pk", read_only=True)
    agreement_type = serializers.CharField(source="agreement.scenario_template", read_only=True)
    agreement_sealed_at = serializers.DateTimeField(source="agreement.sealed_at", read_only=True)

    class Meta:
        model = Dispute
        fields = (
            "id",
            "raised_by_party_id",
            "raised_by_display_name",
            "reason",
            "status",
            "resolution",
            "resolved_at",
            "created_at",
            "updated_at",
            "agreement_id",
            "agreement_type",
            "agreement_sealed_at",
        )
