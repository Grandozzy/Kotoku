from rest_framework import serializers

from apps.billing.constants import PLAN_MAP


class InitiateSerializer(serializers.Serializer):
    MODE_SUBSCRIPTION = "subscription"
    MODE_RECOVERY = "recovery"
    CHANNEL_CARD = "card"
    CHANNEL_MOBILE_MONEY = "mobile_money"

    plan_id = serializers.ChoiceField(choices=list(PLAN_MAP.keys()))
    mode = serializers.ChoiceField(
        choices=[MODE_SUBSCRIPTION, MODE_RECOVERY],
        required=False,
        default=MODE_SUBSCRIPTION,
    )
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=[CHANNEL_CARD, CHANNEL_MOBILE_MONEY]),
        required=False,
        allow_empty=False,
    )
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

    def validate(self, attrs: dict) -> dict:
        mode = attrs.get("mode", self.MODE_SUBSCRIPTION)
        channels = attrs.get("channels")

        if mode == self.MODE_SUBSCRIPTION and channels:
            raise serializers.ValidationError({
                "channels": "channels can only be set for recovery payments."
            })

        if mode == self.MODE_RECOVERY and not channels:
            attrs["channels"] = [self.CHANNEL_CARD, self.CHANNEL_MOBILE_MONEY]

        return attrs
