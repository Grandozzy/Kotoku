from django.urls import path

from .views import CancelView, ConfigView, InitiateView, SubscriptionView, WebhookView

urlpatterns = [
    path("config/", ConfigView.as_view(), name="payments-config"),
    path("initiate/", InitiateView.as_view(), name="payments-initiate"),
    path("subscription/", SubscriptionView.as_view(), name="payments-subscription"),
    path("cancel/", CancelView.as_view(), name="payments-cancel"),
    path("webhook/", WebhookView.as_view(), name="payments-webhook"),
]
