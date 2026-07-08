from rest_framework import serializers

from apps.billing.constants import PLAN_MAP


class InitiateSerializer(serializers.Serializer):
    plan_id = serializers.ChoiceField(choices=list(PLAN_MAP.keys()))
    # Web/mobile clients may pass an explicit public callback URL. If omitted,
    # the backend falls back to PAYSTACK_CALLBACK_URL from settings.
    callback_url = serializers.URLField(required=False, allow_blank=True, default="")

    def validate_callback_url(self, value: str) -> str:
        if not value:
            return value
        lowered = value.lower()
        if not (lowered.startswith("http://") or lowered.startswith("https://")):
            raise serializers.ValidationError(
                "callback_url must be a public http:// or https:// URL."
            )
        return value
