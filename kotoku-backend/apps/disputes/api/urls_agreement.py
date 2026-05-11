from django.urls import path

from .views import DisputeCollectionView, DisputeLookupView

urlpatterns = [
    path("", DisputeCollectionView.as_view(), name="dispute-collection"),
    path("<int:dispute_id>/", DisputeLookupView.as_view(), name="dispute-detail"),
    path("<int:dispute_id>/case_pack/", DisputeLookupView.as_view(), name="dispute-case-pack"),
]