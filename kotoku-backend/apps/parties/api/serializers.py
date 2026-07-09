from rest_framework import serializers

from apps.parties.identity import build_party_identity_states
from apps.parties.models import Party

_E164 = r"^\+[1-9]\d{7,14}$"


class PartyInputSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Party.Role.choices)
    full_name = serializers.CharField(max_length=255)
    phone = serializers.RegexField(_E164, max_length=20)
    id_type = serializers.ChoiceField(choices=Party.IdType.choices)
    id_number = serializers.CharField(max_length=128, allow_blank=False, trim_whitespace=True)


class PartiesSetSerializer(serializers.Serializer):
    parties = PartyInputSerializer(many=True)


class PartyPatchSerializer(serializers.Serializer):
    """role identifies the party to update; all other fields are optional."""

    role = serializers.ChoiceField(choices=Party.Role.choices)
    full_name = serializers.CharField(max_length=255, required=False)
    phone = serializers.RegexField(_E164, max_length=20, required=False)
    id_type = serializers.ChoiceField(choices=Party.IdType.choices, required=False)
    id_number = serializers.CharField(
        max_length=128,
        required=False,
        allow_blank=False,
        trim_whitespace=True,
    )


class PartiesPatchSerializer(serializers.Serializer):
    parties = PartyPatchSerializer(many=True)


class PartyOutputSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="display_name")
    ghana_card_front_uploaded = serializers.SerializerMethodField()
    ghana_card_back_uploaded = serializers.SerializerMethodField()
    identity_selfie_uploaded = serializers.SerializerMethodField()
    ghana_card_front_view_url = serializers.SerializerMethodField()
    ghana_card_back_view_url = serializers.SerializerMethodField()
    identity_selfie_view_url = serializers.SerializerMethodField()
    identity_verification_status = serializers.SerializerMethodField()
    identity_verification_detail = serializers.SerializerMethodField()
    identity_verification_failure_codes = serializers.SerializerMethodField()

    def _identity_state(self, obj):
        states = self.context.get("party_identity_states", {})
        return states.get(obj.role)

    def get_ghana_card_front_uploaded(self, obj) -> bool:
        state = self._identity_state(obj)
        return bool(state and state.front_uploaded)

    def get_ghana_card_back_uploaded(self, obj) -> bool:
        state = self._identity_state(obj)
        return bool(state and state.back_uploaded)

    def get_identity_selfie_uploaded(self, obj) -> bool:
        state = self._identity_state(obj)
        return bool(state and state.selfie_uploaded)

    def get_ghana_card_front_view_url(self, obj) -> str | None:
        state = self._identity_state(obj)
        return state.front_view_url if state else None

    def get_ghana_card_back_view_url(self, obj) -> str | None:
        state = self._identity_state(obj)
        return state.back_view_url if state else None

    def get_identity_selfie_view_url(self, obj) -> str | None:
        state = self._identity_state(obj)
        return state.selfie_view_url if state else None

    def get_identity_verification_status(self, obj) -> str:
        state = self._identity_state(obj)
        return state.verification_status if state else "pending"

    def get_identity_verification_detail(self, obj) -> str:
        state = self._identity_state(obj)
        return state.verification_detail if state else "Awaiting Ghana Card verification."

    def get_identity_verification_failure_codes(self, obj) -> list[str]:
        state = self._identity_state(obj)
        return list(state.verification_failure_codes) if state else []

    @staticmethod
    def context_for_parties(parties) -> dict:
        parties = list(parties)
        agreement = parties[0].agreement if parties else None
        evidence_items = agreement.evidence_items.all() if agreement else []
        return {
            "party_identity_states": build_party_identity_states(
                parties=parties,
                evidence_items=evidence_items,
            )
        }

    class Meta:
        model = Party
        fields = (
            "id",
            "role",
            "full_name",
            "phone",
            "id_type",
            "id_number",
            "ghana_card_front_uploaded",
            "ghana_card_back_uploaded",
            "identity_selfie_uploaded",
            "ghana_card_front_view_url",
            "ghana_card_back_view_url",
            "identity_selfie_view_url",
            "identity_verification_status",
            "identity_verification_detail",
            "identity_verification_failure_codes",
            "created_at",
            "updated_at",
        )
