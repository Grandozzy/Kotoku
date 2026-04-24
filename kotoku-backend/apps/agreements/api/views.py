from django.http import Http404
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.agreements.api.serializers import (
    AgreementCreateSerializer,
    AgreementDetailSerializer,
    AgreementListSerializer,
    AgreementUpdateSerializer,
)
from apps.agreements.models import Agreement
from apps.agreements.selectors import AgreementSelector
from apps.agreements.services import AgreementService
from common.pagination import DefaultPagination
from common.responses import ok


class AgreementCollectionView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = AgreementSelector.list_agreements(
            account_id=request.user.account.pk,
            status=request.query_params.get("status"),
        )
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AgreementListSerializer(page, many=True)
        return ok({
            "results": serializer.data,
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
        })

    def post(self, request):
        serializer = AgreementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = request.user.account
        agreement = AgreementService.create_draft(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            scenario_template=serializer.validated_data.get("scenario_template", ""),
            created_by=account,
        )
        return ok(
            {"agreement": AgreementDetailSerializer(agreement).data}, status_code=201
        )


class AgreementDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_agreement(self, agreement_id: int, account_id: int):
        try:
            return AgreementSelector.get_agreement_detail(
                agreement_id, account_id=account_id
            )
        except Agreement.DoesNotExist:
            raise Http404 from None

    def get(self, request, agreement_id: int):
        agreement = self._get_agreement(
            agreement_id, account_id=request.user.account.pk
        )
        return ok({"agreement": AgreementDetailSerializer(agreement).data})

    def patch(self, request, agreement_id: int):
        agreement = self._get_agreement(
            agreement_id, account_id=request.user.account.pk
        )
        serializer = AgreementUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        agreement = AgreementService.update_draft(
            agreement_id=agreement_id,
            **serializer.validated_data,
        )
        return ok({"agreement": AgreementDetailSerializer(agreement).data})
