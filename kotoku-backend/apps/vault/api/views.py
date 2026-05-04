from django.http import Http404
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.vault.api.serializers import (
    ExportTriggerResponseSerializer,
    VaultDetailSerializer,
    VaultListSerializer,
)
from apps.vault.models import VaultEntry
from apps.vault.selectors import VaultSelector
from apps.vault.services import VaultService
from common.pagination import DefaultPagination
from common.responses import ok


class VaultCollectionView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = VaultSelector.list_entries(
            account_id=request.user.account.pk,
            export_status=request.query_params.get("export_status"),
            archived=request.query_params.get("archived", "").lower() == "true",
        )
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = VaultListSerializer(page, many=True)
        return ok({
            "results": serializer.data,
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
        })


class VaultDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agreement_id: int):
        try:
            vault_entry = VaultSelector.get_detail(
                agreement_id, account_id=request.user.account.pk
            )
        except VaultEntry.DoesNotExist:
            raise Http404 from None
        return ok({"vault_entry": VaultDetailSerializer(vault_entry).data})


class VaultExportView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int):
        try:
            vault_entry = VaultSelector.get_detail(
                agreement_id, account_id=request.user.account.pk
            )
        except VaultEntry.DoesNotExist:
            raise Http404 from None

        result = VaultService.trigger_export(
            vault_entry_id=vault_entry.pk,
            actor=request.user.account,
        )

        response_data = {"status": result["status"]}
        if result["status"] == "completed":
            from infrastructure.storage.urls import build_storage_url

            response_data["pdf_url"] = build_storage_url(
                vault_entry.pdf_storage_key
            )
            serializer = ExportTriggerResponseSerializer(response_data)
            return ok({"export": serializer.data})

        serializer = ExportTriggerResponseSerializer(response_data)
        return ok({"export": serializer.data}, status_code=202)


class VaultAuditLogView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agreement_id: int):
        try:
            VaultSelector.get_detail(
                agreement_id, account_id=request.user.account.pk
            )
        except VaultEntry.DoesNotExist:
            raise Http404 from None

        events = AuditLog.objects.filter(
            entity_type="agreement",
            entity_id=str(agreement_id),
        ).order_by("-created_at")

        data = [
            {
                "id": e.pk,
                "event_type": e.event_type,
                "actor": e.actor,
                "metadata": e.metadata,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]
        return ok({"events": data})
