from django.urls import path

from .views import DisputeCollectionView, DisputeDetailView

urlpatterns = [
    path("", DisputeCollectionView.as_view(), name="dispute-collection"),
    path("disputes/<int:dispute_id>/case_pack/", DisputeDetailView.as_view(), name="dispute-case-pack"),
    path("disputes/<int:dispute_id>/", DisputeDetailView.as_view(), name="dispute-detail"),
]
