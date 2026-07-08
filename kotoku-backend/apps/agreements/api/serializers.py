from rest_framework import serializers

from apps.agreements.models import Agreement, AgreementRevision
from apps.parties.identity import build_party_identity_states


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
        max_length=128, required=False, default="", allow_blank=True
    )
    field_data = serializers.JSONField(required=False)


class PartySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    role = serializers.CharField()
    display_name = serializers.CharField()
    phone = serializers.CharField()
    id_type = serializers.CharField()
    id_number = serializers.CharField()
    ghana_card_front_uploaded = serializers.SerializerMethodField()
    ghana_card_back_uploaded = serializers.SerializerMethodField()
    ghana_card_front_view_url = serializers.SerializerMethodField()
    ghana_card_back_view_url = serializers.SerializerMethodField()

    def _identity_state(self, obj):
        states = self.context.get("party_identity_states", {})
        return states.get(obj.role)

    def get_ghana_card_front_uploaded(self, obj) -> bool:
        state = self._identity_state(obj)
        return bool(state and state.front_uploaded)

    def get_ghana_card_back_uploaded(self, obj) -> bool:
        state = self._identity_state(obj)
        return bool(state and state.back_uploaded)

    def get_ghana_card_front_view_url(self, obj) -> str | None:
        state = self._identity_state(obj)
        return state.front_view_url if state else None

    def get_ghana_card_back_view_url(self, obj) -> str | None:
        state = self._identity_state(obj)
        return state.back_view_url if state else None


class AgreementIdentitySerializerMixin:
    def _party_serializer_context(self, obj):
        context = dict(getattr(self, "context", {}) or {})
        context["party_identity_states"] = build_party_identity_states(
            parties=obj.parties.all(),
            evidence_items=obj.evidence_items.all(),
        )
        return context

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["parties"] = PartySerializer(
            instance.parties.all(),
            many=True,
            context=self._party_serializer_context(instance),
        ).data
        return representation


class AgreementListSerializer(AgreementIdentitySerializerMixin, serializers.ModelSerializer):
    parties = PartySerializer(many=True, read_only=True)

    class Meta:
        model = Agreement
        fields = ("id", "title", "status", "scenario_template", "field_data", "created_at", "updated_at", "parties")


class AgreementDetailSerializer(AgreementIdentitySerializerMixin, serializers.ModelSerializer):
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
