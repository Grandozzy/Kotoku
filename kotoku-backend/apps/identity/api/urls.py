from django.urls import path

from .views import LivenessResultView, LivenessSessionView

urlpatterns = [
    path(
        "<str:role>/liveness-session/",
        LivenessSessionView.as_view(),
        name="identity-liveness-session",
    ),
    path(
        "<str:role>/liveness-result/",
        LivenessResultView.as_view(),
        name="identity-liveness-result",
    ),
]
