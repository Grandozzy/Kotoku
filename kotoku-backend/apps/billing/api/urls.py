from django.urls import path

from .views import CurrentPlanView

urlpatterns = [
    path("current-plan/", CurrentPlanView.as_view(), name="billing-current-plan"),
]
