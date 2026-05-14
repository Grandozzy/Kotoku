from django.urls import path

from .views import (
    PinSetupView,
    PinVerifyView,
    RefreshTokenView,
    SendOtpView,
    SignOutAllView,
    SignOutView,
    VerifyOtpView,
)

urlpatterns = [
    path("send-otp/",       SendOtpView.as_view(),     name="auth-send-otp"),
    path("verify-otp/",     VerifyOtpView.as_view(),   name="auth-verify-otp"),
    path("token/refresh/",  RefreshTokenView.as_view(), name="auth-token-refresh"),
    path("pin/setup/",      PinSetupView.as_view(),    name="auth-pin-setup"),
    path("pin/verify/",     PinVerifyView.as_view(),   name="auth-pin-verify"),
    path("signout/",        SignOutView.as_view(),      name="auth-signout"),
    path("signout-all/",    SignOutAllView.as_view(),   name="auth-signout-all"),
]
