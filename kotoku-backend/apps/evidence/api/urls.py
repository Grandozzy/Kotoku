from django.urls import path

from .views import EvidenceCollectionView, EvidenceUploadUrlView

urlpatterns = [
    path("", EvidenceCollectionView.as_view(), name="agreement-evidence"),
    path("upload-url/", EvidenceUploadUrlView.as_view(), name="agreement-evidence-upload-url"),
]
