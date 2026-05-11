from django.urls import path

from .views import DisputeCollectionView, DisputeRootView, DisputeLookupView

urlpatterns = [
    # Root-level: /api/disputes/ - list user's disputes
    path("", DisputeRootView.as_view(), name="dispute-root"),
    # Root-level: /api/disputes/mine/ - explicit alias
    path("mine/", DisputeRootView.as_view(), name="dispute-root-alias"),
    # Root-level: /api/disputes/{id}/ - get single dispute
    path("<int:dispute_id>/", DisputeLookupView.as_view(), name="dispute-lookup"),
    path("<int:dispute_id>/case_pack/", DisputeLookupView.as_view(), name="dispute-case-pack"),
]
