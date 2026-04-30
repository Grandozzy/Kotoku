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
from common.responses import ok


class VaultCollectionView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = VaultSelector.list_for_account(account_id=request.user.account.pk)
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

    def _get_entry(self, agreement_id: int, account_id: int) -> VaultEntry:
        try:
            return VaultSelector.get_for_agreement(
                agreement_id=agreement_id,
                account_id=account_id,
            )
        except VaultEntry.DoesNotExist:
            raise Http404 from None

    def get(self, request, agreement_id: int):
        entry = self._get_entry(agreement_id, request.user.account.pk)
        return ok({"vault_entry": VaultEntrySerializer(entry).data})


class VaultExportView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int):
        # Ownership check before triggering the export.
        try:
            VaultSelector.get_for_agreement(
                agreement_id=agreement_id,
                account_id=request.user.account.pk,
            )
        except VaultEntry.DoesNotExist:
            raise Http404 from None

        entry = VaultService.request_export(agreement_id=agreement_id)
        return ok({"vault_entry": VaultEntrySerializer(entry).data}, status_code=202)
