from rest_framework import serializers

from apps.billing.constants import PLAN_MAP


class InitiateSerializer(serializers.Serializer):
    plan_id = serializers.ChoiceField(choices=list(PLAN_MAP.keys()))
