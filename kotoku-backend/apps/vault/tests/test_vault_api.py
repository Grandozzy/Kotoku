from unittest.mock import patch

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.evidence.models import EvidenceItem
from apps.identity.models import IdentityRecord
from apps.parties.models import Party
from apps.vault.models import VaultEntry


def _user_account(email, phone):
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(user=user, email=email, phone=phone)
    return user, account


def _sealed(account):
    agreement = Agreement.objects.create(
        title="Vault API Test",
        scenario_template="cash_sale",
        created_by=account,
        status=AgreementStatus.ACTIVE,
    )
    id1 = IdentityRecord.objects.create(
        account=account, reference="GC-API-1", verification_type="ghana_card"
    )
    id2 = IdentityRecord.objects.create(
        account=account, reference="GC-API-2", verification_type="ghana_card"
    )
    p1 = Party.objects.create(
        agreement=agreement, identity=id1, role="buyer", display_name="Alice"
    )
    Party.objects.create(
        agreement=agreement, identity=id2, role="seller", display_name="Bob"
    )
    EvidenceItem.objects.create(
        agreement=agreement,
        uploaded_by=p1,
        file_type="photo",
        file_hash="abc123",
        original_name="photo.jpg",
    )
    from apps.agreements.services import AgreementService

    with patch("apps.vault.services.generate_vault_pdf.delay"):
        return AgreementService.seal_agreement(agreement_id=agreement.pk)


@pytest.fixture()
def auth_client():
    user, account = _user_account("vaultapi@test.com", "+233600000001")
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client, account


@pytest.fixture()
def other_client():
    user, account = _user_account("other@vaultapi.com", "+233600000002")
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client, account


@pytest.mark.django_db
class TestVaultListApi:
    def test_list_returns_200(self, auth_client):
        client, account = auth_client
        _sealed(account)
        response = client.get("/api/vault/", format="json")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "results" in data
        assert data["count"] == 1
        entry = data["results"][0]
        assert entry["agreement_title"] == "Vault API Test"
        assert entry["export_status"] == "pending"

    def test_list_unauthenticated_returns_401(self):
        response = APIClient().get("/api/vault/", format="json")
        assert response.status_code == 401

    def test_list_filter_by_export_status(self, auth_client):
        client, account = auth_client
        _sealed(account)
        response = client.get("/api/vault/?export_status=completed", format="json")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 0

    def test_list_excludes_archived_by_default(self, auth_client):
        client, account = auth_client
        _sealed(account)
        VaultEntry.objects.update(archived=True)
        response = client.get("/api/vault/", format="json")
        assert response.json()["data"]["count"] == 0

    def test_list_includes_archived_when_param(self, auth_client):
        client, account = auth_client
        _sealed(account)
        VaultEntry.objects.update(archived=True)
        response = client.get("/api/vault/?archived=true", format="json")
        assert response.json()["data"]["count"] == 1

    def test_list_ownership_isolation(self, auth_client, other_client):
        client1, acc1 = auth_client
        client2, _ = other_client
        _sealed(acc1)
        resp1 = client1.get("/api/vault/", format="json")
        resp2 = client2.get("/api/vault/", format="json")
        assert resp1.json()["data"]["count"] == 1
        assert resp2.json()["data"]["count"] == 0


@pytest.mark.django_db
class TestVaultDetailApi:
    def test_detail_returns_200(self, auth_client):
        client, account = auth_client
        agreement = _sealed(account)
        response = client.get(f"/api/vault/{agreement.pk}/", format="json")
        assert response.status_code == 200
        data = response.json()["data"]["vault_entry"]
        assert data["agreement_id"] == agreement.pk
        assert data["export_status"] == "pending"
        assert len(data["parties"]) == 2
        assert len(data["evidence_items"]) == 1
        assert data["pdf_url"] is None

    def test_detail_other_user_returns_404(self, auth_client, other_client):
        _, acc1 = auth_client
        other, _ = other_client
        agreement = _sealed(acc1)
        response = other.get(f"/api/vault/{agreement.pk}/", format="json")
        assert response.status_code == 404

    def test_detail_nonexistent_returns_404(self, auth_client):
        client, _ = auth_client
        response = client.get("/api/vault/99999/", format="json")
        assert response.status_code == 404

    def test_detail_shows_pdf_url_when_completed(self, auth_client):
        client, account = auth_client
        agreement = _sealed(account)
        entry = VaultEntry.objects.get(agreement=agreement)
        entry.export_status = VaultEntry.ExportStatus.COMPLETED
        entry.pdf_storage_key = "vault/1/test.pdf"
        entry.save()
        response = client.get(f"/api/vault/{agreement.pk}/", format="json")
        data = response.json()["data"]["vault_entry"]
        assert data["pdf_url"] is not None
        assert "test.pdf" in data["pdf_url"]


@pytest.mark.django_db
class TestVaultExportApi:
    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_export_pending_returns_202(self, mock_delay, auth_client):
        client, account = auth_client
        agreement = _sealed(account)
        response = client.post(f"/api/vault/{agreement.pk}/export", format="json")
        assert response.status_code == 202
        data = response.json()["data"]["export"]
        assert data["status"] == "pending"

    def test_export_completed_returns_200(self, auth_client):
        client, account = auth_client
        agreement = _sealed(account)
        entry = VaultEntry.objects.get(agreement=agreement)
        entry.export_status = VaultEntry.ExportStatus.COMPLETED
        entry.pdf_storage_key = "vault/1/test.pdf"
        entry.save()
        response = client.post(f"/api/vault/{agreement.pk}/export", format="json")
        assert response.status_code == 200
        data = response.json()["data"]["export"]
        assert data["status"] == "completed"
        assert "test.pdf" in data["pdf_url"]

    @patch("apps.vault.services.generate_vault_pdf.delay")
    def test_export_failed_retries(self, mock_delay, auth_client):
        client, account = auth_client
        agreement = _sealed(account)
        entry = VaultEntry.objects.get(agreement=agreement)
        entry.export_status = VaultEntry.ExportStatus.FAILED
        entry.save()
        mock_delay.reset_mock()
        response = client.post(f"/api/vault/{agreement.pk}/export", format="json")
        assert response.status_code == 202
        mock_delay.assert_called_once()

    def test_export_other_user_returns_404(self, auth_client, other_client):
        _, acc1 = auth_client
        other, _ = other_client
        agreement = _sealed(acc1)
        response = other.post(f"/api/vault/{agreement.pk}/export", format="json")
        assert response.status_code == 404


@pytest.mark.django_db
class TestVaultAuditLogApi:
    def test_audit_log_returns_200(self, auth_client):
        client, account = auth_client
        agreement = _sealed(account)
        response = client.get(f"/api/vault/{agreement.pk}/audit-log/", format="json")
        assert response.status_code == 200
        events = response.json()["data"]["events"]
        event_types = [e["event_type"] for e in events]
        assert "agreement.sealed" in event_types
        assert len(events) > 0

    def test_audit_log_empty_when_no_events(self, auth_client):
        client, account = auth_client
        agreement = _sealed(account)
        from apps.audit.models import AuditLog

        AuditLog.objects.all().delete()
        response = client.get(f"/api/vault/{agreement.pk}/audit-log/", format="json")
        assert response.status_code == 200
        assert response.json()["data"]["events"] == []

    def test_audit_log_other_user_returns_404(self, auth_client, other_client):
        _, acc1 = auth_client
        other, _ = other_client
        agreement = _sealed(acc1)
        response = other.get(f"/api/vault/{agreement.pk}/audit-log/", format="json")
        assert response.status_code == 404
