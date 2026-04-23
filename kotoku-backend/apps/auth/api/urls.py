from django.urls import path

from .views import SendOtpView, VerifyOtpView

urlpatterns = [
    path("send-otp/", SendOtpView.as_view(), name="auth-send-otp"),
    path("verify-otp/", VerifyOtpView.as_view(), name="auth-verify-otp"),
]
