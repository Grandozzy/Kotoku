from django.urls import path

from .views import HealthCheckView, ReadinessView

urlpatterns = [
    path("", HealthCheckView.as_view(), name="health-check"),
    path("readiness/", ReadinessView.as_view(), name="readiness-check"),
]
