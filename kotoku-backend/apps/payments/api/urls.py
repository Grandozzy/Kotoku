from django.urls import path

from .views import (
    CancelCheckoutView,
    CancelView,
    CheckoutStatusView,
    ConfigView,
    InitiateView,
    SubscriptionView,
    WebhookView,
)

urlpatterns = [
    path("config/", ConfigView.as_view(), name="payments-config"),
    path("initiate/", InitiateView.as_view(), name="payments-initiate"),
    path("subscription/", SubscriptionView.as_view(), name="payments-subscription"),
    path("checkout-status/", CheckoutStatusView.as_view(), name="payments-checkout-status"),
    path("cancel/", CancelView.as_view(), name="payments-cancel"),
    path("checkout/cancel/", CancelCheckoutView.as_view(), name="payments-checkout-cancel"),
    path("webhook/", WebhookView.as_view(), name="payments-webhook"),
]
