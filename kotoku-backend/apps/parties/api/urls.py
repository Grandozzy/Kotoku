from django.urls import path

from .views import PartiesView

urlpatterns = [
    path("", PartiesView.as_view(), name="agreement-parties"),
]
