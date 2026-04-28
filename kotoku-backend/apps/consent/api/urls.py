from django.urls import path

from .views import ConfirmConsentView, ConsentStatusView, RequestOtpView

urlpatterns = [
    path("request-otp/", RequestOtpView.as_view(), name="consent-request-otp"),
    path("confirm/", ConfirmConsentView.as_view(), name="consent-confirm"),
    path("status/", ConsentStatusView.as_view(), name="consent-status"),
]
