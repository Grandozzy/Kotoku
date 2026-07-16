from django.conf import settings

from infrastructure.sms.console_gateway import ConsoleSmsGateway
from infrastructure.sms.gateway import SmsGateway


def get_sms_gateway():
    backend = getattr(settings, "SMS_BACKEND", "infobip")
    if backend == "console":
        return ConsoleSmsGateway()
    if backend == "africastalking":
        return SmsGateway()
    # Default: infobip (primary) — imported lazily so AT/console paths stay fast
    from infrastructure.sms.infobip_gateway import InfobipSmsGateway
    return InfobipSmsGateway()
