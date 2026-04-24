from rest_framework import serializers

from apps.parties.models import Party

_E164 = r"^\+[1-9]\d{7,14}$"


class PartyInputSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Party.Role.choices)
    full_name = serializers.CharField(max_length=255)
    phone = serializers.RegexField(_E164, max_length=20)
    id_type = serializers.ChoiceField(choices=Party.IdType.choices)
    id_number = serializers.CharField(max_length=128)


class PartiesSetSerializer(serializers.Serializer):
    parties = PartyInputSerializer(many=True)


class PartyPatchSerializer(serializers.Serializer):
    """role identifies the party to update; all other fields are optional."""
    role = serializers.ChoiceField(choices=Party.Role.choices)
    full_name = serializers.CharField(max_length=255, required=False)
    phone = serializers.RegexField(_E164, max_length=20, required=False)
    id_type = serializers.ChoiceField(choices=Party.IdType.choices, required=False)
    id_number = serializers.CharField(max_length=128, required=False)


class PartiesPatchSerializer(serializers.Serializer):
    parties = PartyPatchSerializer(many=True)


class PartyOutputSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="display_name")

    class Meta:
        model = Party
        fields = (
            "id",
            "role",
            "full_name",
            "phone",
            "id_type",
            "id_number",
            "created_at",
            "updated_at",
        )
