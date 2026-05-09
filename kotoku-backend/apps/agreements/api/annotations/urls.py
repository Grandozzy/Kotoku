from django.urls import path

from .views import AnnotationCollectionView, AnnotationDetailView

urlpatterns = [
    path("", AnnotationCollectionView.as_view(), name="annotation-collection"),
    path("<int:annotation_id>", AnnotationDetailView.as_view(), name="annotation-detail"),
]
