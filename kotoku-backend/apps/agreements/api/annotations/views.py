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


def _caller_party(agreement_id: int, phone: str):
    from apps.parties.models import Party  # noqa: PLC0415

    return Party.objects.filter(agreement_id=agreement_id, phone=phone).first()


class AnnotationCollectionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_agreement(self, agreement_id: int, account_id: int, account_phone: str):
        try:
            return AgreementSelector.get_agreement_detail(
                agreement_id,
                account_id=account_id,
                account_phone=account_phone,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None

    def get(self, request, agreement_id: int):
        self._get_agreement(
            agreement_id,
            request.user.account.pk,
            request.user.account.phone,
        )
        annotations = AnnotationSelector.list_for_agreement(agreement_id=agreement_id)
        return ok({"annotations": AnnotationSerializer(annotations, many=True).data})

    def post(self, request, agreement_id: int):
        self._get_agreement(
            agreement_id,
            request.user.account.pk,
            request.user.account.phone,
        )
        serializer = AnnotationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        caller_party = _caller_party(agreement_id, request.user.account.phone)
        if caller_party is None:
            return Response(
                {"status": "error", "message": "Authenticated user is not a verified party on this agreement."},
                status=403,
            )
        if serializer.validated_data["author_party_id"] != caller_party.pk:
            return Response(
                {"status": "error", "message": "Annotations can only be created for the authenticated party."},
                status=403,
            )
        annotation = AnnotationService.create(
            agreement_id=agreement_id,
            author_party_id=caller_party.pk,
            body=serializer.validated_data["body"],
        )
        return ok({"annotation": AnnotationSerializer(annotation).data}, status_code=201)


class AnnotationDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_agreement(self, agreement_id: int, account_id: int, account_phone: str):
        try:
            return AgreementSelector.get_agreement_detail(
                agreement_id,
                account_id=account_id,
                account_phone=account_phone,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None

    def delete(self, request, agreement_id: int, annotation_id: int):
        self._get_agreement(
            agreement_id,
            request.user.account.pk,
            request.user.account.phone,
        )
        caller_party = _caller_party(agreement_id, request.user.account.phone)
        if caller_party is None:
            return Response(
                {"status": "error", "message": "Authenticated user is not a verified party on this agreement."},
                status=403,
            )
        try:
            AnnotationService.delete(annotation_id, caller_party.pk)
        except DomainError as e:
            return Response({"status": "error", "message": str(e)}, status=400)
        return ok(None)

    def put(self, request, agreement_id: int, annotation_id: int):
        self._get_agreement(
            agreement_id,
            request.user.account.pk,
            request.user.account.phone,
        )
        caller_party = _caller_party(agreement_id, request.user.account.phone)
        if caller_party is None:
            return Response(
                {"status": "error", "message": "Authenticated user is not a verified party on this agreement."},
                status=403,
            )
        body = request.data.get("body")
        if not body:
            return Response({"status": "error", "message": "body required"}, status=400)
        try:
            annotation = AnnotationService.update(
                annotation_id=annotation_id,
                actor_party_id=caller_party.pk,
                body=body,
            )
        except DomainError as e:
            return Response({"status": "error", "message": str(e)}, status=400)
        return ok({"annotation": AnnotationSerializer(annotation).data})
