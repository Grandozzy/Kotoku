from django.urls import path

from .views import TemplateDetailView, TemplateListView

urlpatterns = [
    path("", TemplateListView.as_view(), name="template-list"),
    path("<str:slug>/", TemplateDetailView.as_view(), name="template-detail"),
]
