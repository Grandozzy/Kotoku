from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import SendOtpView, VerifyOtpView

urlpatterns = [
    path("send-otp/", SendOtpView.as_view(), name="auth-send-otp"),
    path("verify-otp/", VerifyOtpView.as_view(), name="auth-verify-otp"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
