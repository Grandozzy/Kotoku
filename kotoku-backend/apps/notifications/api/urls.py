from django.urls import path

from apps.notifications.api.views import InfobipDlrWebhookView

urlpatterns = [
    path("infobip/dlr/", InfobipDlrWebhookView.as_view(), name="infobip-dlr-webhook"),
]
