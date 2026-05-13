from django.http import Http404
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agreements.annotation_services import AnnotationSelector, AnnotationService
from common.exceptions import DomainError
from apps.agreements.api.annotations.serializers import (
    AnnotationCreateSerializer,
    AnnotationSerializer,
)
from apps.agreements.models import Agreement
from apps.agreements.selectors import AgreementSelector
from common.responses import ok


class AnnotationCollectionView(APIView):
    authentication_classes = [JWTAuthentication]
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


class AnnotationDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_agreement(self, agreement_id: int, account_id: int):
        try:
            return AgreementSelector.get_agreement_detail(agreement_id, account_id=account_id)
        except Agreement.DoesNotExist:
            raise Http404 from None

    def delete(self, request, agreement_id: int, annotation_id: int):
        self._get_agreement(agreement_id, request.user.account.pk)
        party_id = request.query_params.get("party_id")
        if not party_id:
            return Response({"status": "error", "message": "party_id required"}, status=400)
        try:
            AnnotationService.delete(annotation_id, int(party_id))
        except DomainError as e:
            return Response({"status": "error", "message": str(e)}, status=400)
        return ok(None)

    def put(self, request, agreement_id: int, annotation_id: int):
        self._get_agreement(agreement_id, request.user.account.pk)
        party_id = request.query_params.get("party_id")
        if not party_id:
            return Response({"status": "error", "message": "party_id required"}, status=400)
        body = request.data.get("body")
        if not body:
            return Response({"status": "error", "message": "body required"}, status=400)
        try:
            annotation = AnnotationService.update(
                annotation_id=annotation_id,
                actor_party_id=int(party_id),
                body=body,
            )
        except DomainError as e:
            return Response({"status": "error", "message": str(e)}, status=400)
        return ok({"annotation": AnnotationSerializer(annotation).data})
