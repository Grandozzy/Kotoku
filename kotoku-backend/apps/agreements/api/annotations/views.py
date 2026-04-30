from django.http import Http404
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.agreements.annotation_services import AnnotationSelector, AnnotationService
from apps.agreements.api.annotations.serializers import (
    AnnotationCreateSerializer,
    AnnotationSerializer,
)
from apps.agreements.models import Agreement
from apps.agreements.selectors import AgreementSelector
from common.responses import ok


class AnnotationCollectionView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_agreement(self, agreement_id: int, account_id: int):
        try:
            return AgreementSelector.get_agreement_detail(agreement_id, account_id=account_id)
        except Agreement.DoesNotExist:
            raise Http404 from None

    def get(self, request, agreement_id: int):
        self._get_agreement(agreement_id, request.user.account.pk)
        annotations = AnnotationSelector.list_for_agreement(agreement_id=agreement_id)
        return ok({"annotations": AnnotationSerializer(annotations, many=True).data})

    def post(self, request, agreement_id: int):
        self._get_agreement(agreement_id, request.user.account.pk)
        serializer = AnnotationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        annotation = AnnotationService.create(
            agreement_id=agreement_id,
            author_party_id=serializer.validated_data["author_party_id"],
            body=serializer.validated_data["body"],
        )
        return ok({"annotation": AnnotationSerializer(annotation).data}, status_code=201)
