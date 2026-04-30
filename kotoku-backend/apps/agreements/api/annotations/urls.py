from django.urls import path

from .views import AnnotationCollectionView

urlpatterns = [
    path("", AnnotationCollectionView.as_view(), name="annotation-collection"),
]
