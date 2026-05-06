from django.conf import settings

from infrastructure.sms.console_gateway import ConsoleSmsGateway
from infrastructure.sms.gateway import SmsGateway


def get_sms_gateway():
    if getattr(settings, "SMS_BACKEND", "africastalking") == "console":
        return ConsoleSmsGateway()
    return SmsGateway()
