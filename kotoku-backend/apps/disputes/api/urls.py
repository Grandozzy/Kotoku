from django.urls import path

from .views import DisputeCollectionView, DisputeRootView, DisputeLookupView

urlpatterns = [
    path("", DisputeCollectionView.as_view(), name="dispute-collection"),
    path("mine/", DisputeRootView.as_view(), name="dispute-root"),
    path("<int:dispute_id>/", DisputeLookupView.as_view(), name="dispute-lookup"),
    path("<int:dispute_id>/case_pack/", DisputeLookupView.as_view(), name="dispute-case-pack"),
]
