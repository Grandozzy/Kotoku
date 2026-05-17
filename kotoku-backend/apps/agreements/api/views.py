import logging

from django.http import Http404
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

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
from common.responses import ok

logger = logging.getLogger("kotoku")


class AgreementCollectionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        status_filter = request.query_params.get("status")
        logger.info(
            "[DRAFT] list_agreements account=%s status_filter=%s",
            request.user.account.pk,
            status_filter,
        )
        qs = AgreementSelector.list_agreements(
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
            status=status_filter,
        )
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AgreementListSerializer(page, many=True)
        logger.info(
            "[DRAFT] list_agreements result count=%s page_size=%s",
            paginator.page.paginator.count,
            len(serializer.data),
        )
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
        scenario_template = serializer.validated_data.get("scenario_template", "")
        logger.info(
            "[DRAFT] create_draft account=%s title=%s scenario_template='%s'",
            account.pk,
            serializer.validated_data["title"],
            scenario_template,
        )
        agreement = AgreementService.create_draft(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            scenario_template=scenario_template,
            created_by=account,
        )
        logger.info(
            "[DRAFT] create_draft success id=%s status=%s",
            agreement.pk,
            agreement.status,
        )
        return ok(
            {"agreement": AgreementDetailSerializer(agreement).data}, status_code=201
        )


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
        logger.info(
            "[DRAFT] get_agreement_detail id=%s account=%s",
            agreement_id,
            request.user.account.pk,
        )
        agreement = self._get_agreement(
            agreement_id,
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
        )
        logger.info(
            "[DRAFT] get_agreement_detail id=%s status=%s scenario_template='%s' step_index=%s parties=%s field_data_keys=%s",
            agreement.pk,
            agreement.status,
            agreement.scenario_template,
            agreement.step_index,
            len(agreement.parties.all()),
            list(agreement.field_data.keys()) if agreement.field_data else [],
        )
        return ok({"agreement": AgreementDetailSerializer(agreement).data})

    def patch(self, request, agreement_id: int):
        agreement = self._get_agreement(
            agreement_id,
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
        )
        serializer = AgreementUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        update_keys = [k for k, v in serializer.validated_data.items() if v is not None]
        logger.info(
            "[DRAFT] update_agreement id=%s status=%s fields=%s",
            agreement_id,
            agreement.status,
            update_keys,
        )
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
        logger.info(
            "[DRAFT] update_agreement success id=%s scenario_template='%s' step_index=%s",
            agreement.pk,
            agreement.scenario_template,
            agreement.step_index,
        )
        return ok({"agreement": AgreementDetailSerializer(agreement).data})

    def delete(self, request, agreement_id: int):
        agreement = self._get_agreement(
            agreement_id,
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
        )
        logger.info(
            "[DRAFT] discard_draft id=%s status=%s account=%s",
            agreement_id,
            agreement.status,
            request.user.account.pk,
        )
        try:
            AgreementService.discard_draft(agreement_id=agreement_id)
        except DomainError as exc:
            from rest_framework.response import Response
            return Response({"detail": str(exc)}, status=400)
        logger.info(
            "[DRAFT] discard_draft success id=%s",
            agreement_id,
        )
        from rest_framework.response import Response
        return Response(status=204)


class ValidateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int):
        try:
            agreement = AgreementSelector.get_agreement_detail(
                agreement_id,
                account_id=request.user.account.pk,
                account_phone=request.user.account.phone,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None
        logger.info(
            "[DRAFT] validate id=%s status=%s scenario_template='%s'",
            agreement_id,
            agreement.status,
            agreement.scenario_template,
        )
        result = validate_agreement(agreement)
        logger.info(
            "[DRAFT] validate result valid=%s errors=%s",
            result.valid,
            len(result.errors),
        )
        return ok(
            {
                "valid": result.valid,
                "errors": [
                    {"code": e.code, "message": e.message, "field": e.field}
                    for e in result.errors
                ],
            }
        )


class SealView(APIView):
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
            AgreementSelector.get_agreement_detail(
                agreement_id,
                account_id=request.user.account.pk,
                account_phone=request.user.account.phone,
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
            AgreementSelector.get_agreement_detail(
                agreement_id,
                account_id=request.user.account.pk,
                account_phone=request.user.account.phone,
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

        record = ConsentService.confirm_reopen_by_phone(
            agreement_id=agreement_id,
            party_phone=phone,
            otp_code=otp_code,
        )
        agreement = AgreementSelector.get_agreement_detail(
            agreement_id,
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
        )
        return ok({
            "granted": record.granted,
            "agreement_status": agreement.status,
        })


class PendingActionsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        account = request.user.account
        phone = account.phone

        logger.info(
            "[DRAFT] pending_actions account=%s phone=%s",
            account.pk,
            phone,
        )

        drafts = list(
            Agreement.objects.filter(
                created_by=account,
                status=AgreementStatus.DRAFT,
            )
            .prefetch_related("parties")
            .order_by("-updated_at")
        )

        logger.info(
            "[DRAFT] pending_actions drafts_found=%s ids=%s",
            len(drafts),
            [d.pk for d in drafts],
        )

        pending_consent_qs = (
            Agreement.objects.filter(
                status=AgreementStatus.PENDING_CONSENT,
                parties__phone=phone,
                consent_records__party__phone=phone,
                consent_records__purpose=ConsentRecord.Purpose.CONSENT,
                consent_records__granted=False,
            )
            .distinct()
            .order_by("-updated_at")
        )

        reopen_requested_qs = (
            Agreement.objects.filter(
                status=AgreementStatus.REOPEN_REQUESTED,
                parties__phone=phone,
                consent_records__party__phone=phone,
                consent_records__purpose=ConsentRecord.Purpose.REOPEN,
                consent_records__granted=False,
            )
            .distinct()
            .order_by("-updated_at")
        )

        action_required = list(pending_consent_qs) + list(reopen_requested_qs)

        logger.info(
            "[DRAFT] pending_actions action_required=%s (pending_consent=%s, reopen_requested=%s)",
            len(action_required),
            len(pending_consent_qs),
            len(reopen_requested_qs),
        )

        return ok({
            "action_required": AgreementListSerializer(action_required, many=True).data,
            "drafts": AgreementListSerializer(drafts, many=True).data,
        })
