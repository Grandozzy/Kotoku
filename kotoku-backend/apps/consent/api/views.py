from django.http import Http404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.agreements.models import Agreement
from apps.agreements.selectors import AgreementSelector
from apps.consent.api.serializers import (
    ConfirmConsentSerializer,
    ConsentRecordOutputSerializer,
    ConsentStatusOutputSerializer,
)
from apps.consent.selectors import ConsentSelector
from apps.consent.services import ConsentService
from common.responses import ok


def _get_agreement_or_404(
    agreement_id: int,
    account_id: int,
    account_phone: str | None = None,
    owner_only: bool = False,
) -> Agreement:
    try:
        if owner_only:
            return AgreementSelector.get_owned_agreement_detail(
                agreement_id,
                account_id=account_id,
            )
        return AgreementSelector.get_agreement_detail(
            agreement_id,
            account_id=account_id,
            account_phone=account_phone,
        )
    except Agreement.DoesNotExist:
        raise Http404 from None


class RequestOtpView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int):
        _get_agreement_or_404(
            agreement_id,
            account_id=request.user.account.pk,
            owner_only=True,
        )
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
        _get_agreement_or_404(
            agreement_id,
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
        )
        serializer = ConfirmConsentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account_phone = request.user.account.phone
        if serializer.validated_data["party_phone"] != account_phone:
            raise PermissionDenied("Consent confirmation must match the authenticated phone.")
        record = ConsentService.confirm_by_phone(
            agreement_id=agreement_id,
            party_phone=account_phone,
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
        _get_agreement_or_404(
            agreement_id,
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
        )
        records = list(ConsentSelector.list_consent_for_agreement(agreement_id=agreement_id))
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
