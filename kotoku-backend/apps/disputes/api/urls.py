from django.urls import path

from .views import DisputeCollectionView

urlpatterns = [
    path("", DisputeCollectionView.as_view(), name="dispute-collection"),
]
