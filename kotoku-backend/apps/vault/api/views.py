from django.http import Http404
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.vault.api.serializers import VaultEntrySerializer
from apps.vault.models import VaultEntry
from apps.vault.selectors import VaultSelector
from apps.vault.services import VaultService
from common.exceptions import DomainError
from common.pagination import DefaultPagination
from apps.vault.api.audit import AuditEventSerializer, build_audit_timeline
from common.responses import ok


class VaultCollectionView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = VaultSelector.list_for_account(
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
        )
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = VaultEntrySerializer(page, many=True)
        return ok({
            "results": serializer.data,
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
        })


class VaultDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_entry(
        self, agreement_id: int, account_id: int, account_phone: str
    ) -> VaultEntry:
        try:
            return VaultSelector.get_for_agreement(
                agreement_id=agreement_id,
                account_id=account_id,
                account_phone=account_phone,
            )
        except VaultEntry.DoesNotExist:
            raise Http404 from None

    def get(self, request, agreement_id: int):
        entry = self._get_entry(
            agreement_id,
            request.user.account.pk,
            request.user.account.phone,
        )
        return ok({"vault_entry": VaultEntrySerializer(entry).data})


class VaultExportView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int):
        try:
            VaultSelector.get_for_agreement(
                agreement_id=agreement_id,
                account_id=request.user.account.pk,
                account_phone=request.user.account.phone,
            )
        except VaultEntry.DoesNotExist:
            raise Http404 from None

        entry = VaultService.request_export(agreement_id=agreement_id)
        return ok({"vault_entry": VaultEntrySerializer(entry).data}, status_code=202)


class VaultAuditLogView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agreement_id: int):
        try:
            entry = VaultSelector.get_for_agreement(
                agreement_id=agreement_id,
                account_id=request.user.account.pk,
                account_phone=request.user.account.phone,
            )
        except VaultEntry.DoesNotExist:
            raise Http404 from None

        events = build_audit_timeline(entry.agreement)
        serializer = AuditEventSerializer(events, many=True)
        return ok({"events": serializer.data})
