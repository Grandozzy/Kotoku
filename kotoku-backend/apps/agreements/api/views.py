from django.db import transaction
from django.http import Http404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.agreements.api.serializers import (
    AgreementCreateSerializer,
    AgreementDetailSerializer,
    AgreementListSerializer,
    AgreementUpdateSerializer,
)
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.domain.validators import validate_agreement
from apps.agreements.models import Agreement
from apps.agreements.selectors import AgreementSelector
from apps.agreements.services import AgreementService
from apps.consent.models import ConsentRecord
from apps.consent.services import ConsentService
from apps.vault.services import VaultService
from common.exceptions import DomainError
from common.pagination import DefaultPagination
from common.phone_numbers import phone_lookup_values, same_phone
from common.responses import ok


class AgreementCollectionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = AgreementSelector.list_agreements(
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
            status=request.query_params.get("status"),
        )
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AgreementListSerializer(page, many=True)
        return ok(
            {
                "results": serializer.data,
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
            }
        )

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
        return ok({"agreement": AgreementDetailSerializer(agreement).data}, status_code=201)


class AgreementDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_agreement(self, agreement_id: int, account_id: int, account_phone: str):
        try:
            return AgreementSelector.get_agreement_detail(
                agreement_id, account_id=account_id, account_phone=account_phone
            )
        except Agreement.DoesNotExist:
            raise Http404 from None

    def get(self, request, agreement_id: int):
        agreement = self._get_agreement(
            agreement_id,
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
        )
        return ok({"agreement": AgreementDetailSerializer(agreement).data})

    def delete(self, request, agreement_id: int):
        try:
            agreement = AgreementSelector.get_owned_agreement_detail(
                agreement_id,
                account_id=request.user.account.pk,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None
        deletable_statuses = {
            AgreementStatus.DRAFT,
            AgreementStatus.PENDING_CONSENT,
        }
        if agreement.status not in deletable_statuses:
            raise DomainError(
                "Only draft or pending-consent agreements can be deleted."
            )
        agreement.delete()
        return ok({})

    def patch(self, request, agreement_id: int):
        try:
            agreement = AgreementSelector.get_owned_agreement_detail(
                agreement_id,
                account_id=request.user.account.pk,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None
        serializer = AgreementUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if agreement.status == AgreementStatus.DRAFT:
            agreement = AgreementService.update_draft(
                agreement_id=agreement_id,
                **serializer.validated_data,
            )
        elif agreement.status == AgreementStatus.ACTIVE:
            agreement = AgreementService.update_active(
                agreement_id=agreement_id,
                **serializer.validated_data,
            )
        else:
            raise DomainError("Cannot update agreement in this status")
        return ok({"agreement": AgreementDetailSerializer(agreement).data})


class ValidateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int):
        try:
            agreement = AgreementSelector.get_owned_agreement_detail(
                agreement_id,
                account_id=request.user.account.pk,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None
        result = validate_agreement(agreement)
        return ok(
            {
                "valid": result.valid,
                "errors": [
                    {"code": e.code, "message": e.message, "field": e.field} for e in result.errors
                ],
            }
        )


class SealView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int):
        try:
            AgreementSelector.get_owned_agreement_detail(
                agreement_id,
                account_id=request.user.account.pk,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None
        with transaction.atomic():
            agreement = AgreementService.seal_agreement(agreement_id=agreement_id)
            VaultService.create_for_agreement(agreement_id=agreement_id)
        return ok({"agreement": AgreementDetailSerializer(agreement).data})


# ── Sprint 6: Bilateral reopen flow ────────────────────────────────────────── #


class ReopenRequestView(APIView):
    """POST /agreements/{id}/reopen-request/

    Transitions a SEALED agreement to REOPEN_REQUESTED and immediately
    issues reopen-consent OTPs to all parties.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int):
        try:
            AgreementSelector.get_owned_agreement_detail(
                agreement_id,
                account_id=request.user.account.pk,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None

        agreement = AgreementService.request_reopen(agreement_id=agreement_id)
        ConsentService.request_reopen_otp(agreement_id=agreement_id)
        return ok({"agreement": AgreementDetailSerializer(agreement).data})


class ReopenOtpRequestView(APIView):
    """POST /agreements/{id}/reopen-consent/request-otp/

    Re-issues reopen OTPs to all parties (e.g. after expiry).
    Agreement must already be in REOPEN_REQUESTED status.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int):
        try:
            AgreementSelector.get_owned_agreement_detail(
                agreement_id,
                account_id=request.user.account.pk,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None

        ConsentService.request_reopen_otp(agreement_id=agreement_id)
        return ok({"detail": "Reopen OTPs issued to all parties."})


class ReopenOtpConfirmView(APIView):
    """POST /agreements/{id}/reopen-consent/confirm/

    Body: { "phone": "+233...", "otp_code": "12345678" }

    A party confirms their reopen OTP. When the last party confirms, the
    agreement automatically transitions REOPEN_REQUESTED → ACTIVE.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int):
        try:
            AgreementSelector.get_agreement_detail(
                agreement_id,
                account_id=request.user.account.pk,
                account_phone=request.user.account.phone,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None

        phone = request.data.get("phone", "").strip()
        otp_code = request.data.get("otp_code", "").strip()
        if not phone or not otp_code:
            from common.exceptions import DomainError as _DomainError  # noqa: PLC0415

            raise _DomainError("Both 'phone' and 'otp_code' are required.")
        account_phone = request.user.account.phone
        if not same_phone(phone, account_phone):
            raise PermissionDenied("Reopen confirmation must match the authenticated phone.")

        record = ConsentService.confirm_reopen_by_phone(
            agreement_id=agreement_id,
            party_phone=account_phone,
            otp_code=otp_code,
        )
        agreement = AgreementSelector.get_agreement_detail(
            agreement_id,
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
        )
        return ok(
            {
                "granted": record.granted,
                "agreement_status": agreement.status,
            }
        )


class PendingActionsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        account = request.user.account
        phone = account.phone
        phone_values = phone_lookup_values(phone)

        drafts = list(
            Agreement.objects.filter(
                created_by=account,
                status=AgreementStatus.DRAFT,
            )
            .prefetch_related("parties")
            .order_by("-updated_at")
        )

        pending_consent_qs = (
            Agreement.objects.filter(
                status=AgreementStatus.PENDING_CONSENT,
                parties__phone__in=phone_values,
                consent_records__party__phone__in=phone_values,
                consent_records__purpose=ConsentRecord.Purpose.CONSENT,
                consent_records__granted=False,
            )
            .distinct()
            .order_by("-updated_at")
        )

        reopen_requested_qs = (
            Agreement.objects.filter(
                status=AgreementStatus.REOPEN_REQUESTED,
                parties__phone__in=phone_values,
                consent_records__party__phone__in=phone_values,
                consent_records__purpose=ConsentRecord.Purpose.REOPEN,
                consent_records__granted=False,
            )
            .distinct()
            .order_by("-updated_at")
        )

        action_required = list(pending_consent_qs) + list(reopen_requested_qs)

        return ok(
            {
                "action_required": AgreementListSerializer(action_required, many=True).data,
                "drafts": AgreementListSerializer(drafts, many=True).data,
            }
        )
