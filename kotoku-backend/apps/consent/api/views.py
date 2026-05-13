from django.http import Http404
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.agreements.models import Agreement
from apps.agreements.selectors import AgreementSelector
from apps.consent.api.serializers import (
    ConfirmConsentSerializer,
    ConsentRecordOutputSerializer,
    ConsentStatusOutputSerializer,
)
from apps.consent.selectors import ConsentSelector
from apps.consent.services import ConsentService
from common.exceptions import DomainError
from common.responses import ok


def _get_agreement_or_404(agreement_id: int, account_id: int) -> Agreement:
    try:
        return AgreementSelector.get_agreement_detail(agreement_id, account_id=account_id)
    except Agreement.DoesNotExist:
        raise Http404 from None


class RequestOtpView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int):
        _get_agreement_or_404(agreement_id, account_id=request.user.account.pk)
        records = ConsentService.request_otp(agreement_id=agreement_id)
        return ok(
            {
                "consent_records": ConsentRecordOutputSerializer(records, many=True).data,
                "parties_count": len(records),
            },
            status_code=201,
        )


class ConfirmConsentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int):
        _get_agreement_or_404(agreement_id, account_id=request.user.account.pk)
        serializer = ConfirmConsentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = ConsentService.confirm_by_phone(
            agreement_id=agreement_id,
            party_phone=serializer.validated_data["party_phone"],
            otp_code=serializer.validated_data["otp_code"],
        )
        return ok(
            {"consent_record": ConsentRecordOutputSerializer(record).data},
            status_code=200,
        )


class ConsentStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agreement_id: int):
        _get_agreement_or_404(agreement_id, account_id=request.user.account.pk)
        records = list(
            ConsentSelector.list_consent_for_agreement(agreement_id=agreement_id)
        )
        all_consented = ConsentSelector.all_parties_consented(agreement_id=agreement_id)
        return ok(
            ConsentStatusOutputSerializer(
                {
                    "agreement_id": agreement_id,
                    "all_consented": all_consented,
                    "records": records,
                }
            ).data
        )
