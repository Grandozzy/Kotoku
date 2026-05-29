from rest_framework import serializers

from apps.billing.constants import PLAN_MAP


class InitiateSerializer(serializers.Serializer):
    plan_id = serializers.ChoiceField(choices=list(PLAN_MAP.keys()))
    # Web clients pass their own callback URL; mobile clients omit this and
    # fall back to PAYSTACK_CALLBACK_URL in settings (the deep-link scheme).
    callback_url = serializers.URLField(required=False, allow_blank=True, default="")
