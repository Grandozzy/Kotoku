from django.urls import path

from .views import DisputeCollectionView, DisputeRootView, DisputeDetailView

urlpatterns = [
    path("", DisputeRootView.as_view(), name="dispute-root"),
    path("<int:dispute_id>/", DisputeDetailView.as_view(), name="dispute-detail"),
    path("<int:dispute_id>/case_pack/", DisputeDetailView.as_view(), name="dispute-case-pack"),
]
