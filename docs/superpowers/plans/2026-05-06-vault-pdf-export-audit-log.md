# Vault PDF Export + Audit Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get the full seal flow → PDF export working end-to-end, add the missing audit-log endpoint, and upgrade seed data with real evidence files in MinIO.

**Architecture:** The PDF pipeline already exists (Celery task → ReportLab → MinIO). We verify it works, add the missing `GET /api/vault/{id}/audit-log/` endpoint that the frontend calls, and upgrade the seed command to upload a real image to MinIO.

**Tech Stack:** Django, DRF, ReportLab, Celery, MinIO (S3-compatible), pytest

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Modify | `apps/vault/api/views.py` | Add `VaultAuditLogView` |
| Modify | `apps/vault/api/urls.py` | Register audit-log route |
| Create | `apps/vault/api/audit.py` | Audit event serializer + aggregation logic |
| Modify | `apps/templates/management/commands/seed_test_data.py` | Upload real PNG to MinIO |
| Create | `apps/templates/management/commands/test_vault_export.py` | Smoke test command |
| Modify | `apps/vault/tests/test_vault_api.py` | Add audit-log tests |

---

### Task 1: Add Audit-Log Endpoint

**Files:**
- Create: `kotoku-backend/apps/vault/api/audit.py`
- Modify: `kotoku-backend/apps/vault/api/views.py`
- Modify: `kotoku-backend/apps/vault/api/urls.py`

- [ ] **Step 1: Create audit event serializer and builder**

```python
# apps/vault/api/audit.py
from rest_framework import serializers

from apps.agreements.models import Annotation
from apps.consent.models import ConsentRecord
from apps.disputes.models import Dispute
from apps.evidence.models import EvidenceItem
from apps.parties.models import Party


class AuditEventSerializer(serializers.Serializer):
    type = serializers.CharField()
    timestamp = serializers.DateTimeField()
    actor = serializers.CharField(allow_blank=True)
    description = serializers.CharField()


def build_audit_timeline(agreement) -> list[dict]:
    events = []

    events.append({
        "type": "agreement_created",
        "timestamp": agreement.created_at,
        "actor": agreement.created_by.full_name if hasattr(agreement.created_by, "full_name") else "",
        "description": f"Agreement created by {agreement.created_by}",
    })

    for party in agreement.parties.all().order_by("created_at"):
        events.append({
            "type": "party_added",
            "timestamp": party.created_at,
            "actor": party.display_name,
            "description": f"{party.display_name} added as {party.get_role_display()}",
        })

    for item in agreement.evidence_items.all().order_by("created_at"):
        events.append({
            "type": "evidence_uploaded",
            "timestamp": item.created_at,
            "actor": item.uploaded_by.display_name if item.uploaded_by else "",
            "description": f"Evidence uploaded: {item.evidence_type or item.get_file_type_display()}",
        })

    for record in agreement.consent_records.all().order_by("created_at"):
        events.append({
            "type": "consent_requested",
            "timestamp": record.created_at,
            "actor": record.party.display_name,
            "description": f"Consent OTP sent to {record.party.phone}",
        })
        if record.granted and record.granted_at:
            events.append({
                "type": "consent_confirmed",
                "timestamp": record.granted_at,
                "actor": record.party.display_name,
                "description": f"{record.party.display_name} confirmed consent",
            })

    if agreement.sealed_at:
        events.append({
            "type": "sealed",
            "timestamp": agreement.sealed_at,
            "actor": "",
            "description": "Agreement sealed",
        })

    for ann in agreement.annotations.all().order_by("created_at"):
        events.append({
            "type": "annotation_added",
            "timestamp": ann.created_at,
            "actor": ann.author_party.display_name,
            "description": f"Note added by {ann.author_party.display_name}",
        })

    for dispute in agreement.disputes.all().order_by("created_at"):
        events.append({
            "type": "dispute_raised",
            "timestamp": dispute.created_at,
            "actor": dispute.raised_by.display_name,
            "description": f"Dispute raised by {dispute.raised_by.display_name}",
        })

    events.sort(key=lambda e: e["timestamp"])
    return events
```

- [ ] **Step 2: Add VaultAuditLogView to views.py**

Append to `apps/vault/api/views.py`:

```python
from apps.vault.api.audit import AuditEventSerializer, build_audit_timeline


class VaultAuditLogView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agreement_id: int):
        try:
            entry = VaultSelector.get_for_agreement(
                agreement_id=agreement_id,
                account_id=request.user.account.pk,
            )
        except VaultEntry.DoesNotExist:
            raise Http404 from None

        events = build_audit_timeline(entry.agreement)
        serializer = AuditEventSerializer(events, many=True)
        return ok({"events": serializer.data})
```

Note: the import of `VaultSelector` already exists in the file. The new import `from apps.vault.api.audit import ...` should be added to the top import block.

- [ ] **Step 3: Register the route in urls.py**

```python
from .views import VaultAuditLogView, VaultCollectionView, VaultDetailView, VaultExportView

urlpatterns = [
    path("", VaultCollectionView.as_view(), name="vault-collection"),
    path("<int:agreement_id>/", VaultDetailView.as_view(), name="vault-detail"),
    path("<int:agreement_id>/export/", VaultExportView.as_view(), name="vault-export"),
    path("<int:agreement_id>/audit-log/", VaultAuditLogView.as_view(), name="vault-audit-log"),
]
```

- [ ] **Step 4: Run existing tests to verify nothing broke**

Run: `cd kotoku-backend && python -m pytest apps/vault/tests/test_vault_api.py -v`
Expected: All existing tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/vault/api/audit.py apps/vault/api/views.py apps/vault/api/urls.py
git commit -m "feat: add vault audit-log endpoint"
```

---

### Task 2: Add Audit-Log Tests

**Files:**
- Modify: `kotoku-backend/apps/vault/tests/test_vault_api.py`

- [ ] **Step 1: Add audit-log test class**

Append to `apps/vault/tests/test_vault_api.py`:

```python
from apps.vault.api.audit import build_audit_timeline


_AUDIT_PATH = "/api/vault/{id}/audit-log/"


@pytest.mark.django_db
class TestVaultAuditLog:
    def test_returns_200_with_events(self):
        client, acct = _make_client("+233700400001")
        agreement, _ = _sealed_agreement_with_vault(acct, acct.phone, "+233700400002")
        resp = client.get(_AUDIT_PATH.format(id=agreement.pk))
        assert resp.status_code == 200
        events = resp.json()["data"]["events"]
        assert len(events) >= 1
        types = [e["type"] for e in events]
        assert "agreement_created" in types
        assert "sealed" in types

    def test_events_include_parties_and_evidence(self):
        client, acct = _make_client("+233700400003")
        agreement, _ = _sealed_agreement_with_vault(acct, acct.phone, "+233700400004")
        resp = client.get(_AUDIT_PATH.format(id=agreement.pk))
        types = [e["type"] for e in resp.json()["data"]["events"]]
        assert "party_added" in types
        assert "evidence_uploaded" in types

    def test_returns_404_for_other_users_agreement(self):
        client, acct = _make_client("+233700400005")
        _, other_acct = _make_client("+233700400006")
        agreement, _ = _sealed_agreement_with_vault(other_acct, other_acct.phone, "+233700400007")
        resp = client.get(_AUDIT_PATH.format(id=agreement.pk))
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self):
        resp = APIClient().get(_AUDIT_PATH.format(id=1))
        assert resp.status_code == 401

    def test_build_audit_timeline_includes_consent(self):
        client, acct = _make_client("+233700400008")
        agreement, _ = _sealed_agreement_with_vault(acct, acct.phone, "+233700400009")
        events = build_audit_timeline(agreement)
        types = [e["type"] for e in events]
        assert "consent_requested" in types
        assert "consent_confirmed" in types

    def test_build_audit_timeline_sorted_by_timestamp(self):
        client, acct = _make_client("+233700400010")
        agreement, _ = _sealed_agreement_with_vault(acct, acct.phone, "+233700400011")
        events = build_audit_timeline(agreement)
        timestamps = [e["timestamp"] for e in events]
        assert timestamps == sorted(timestamps)
```

- [ ] **Step 2: Run tests**

Run: `cd kotoku-backend && python -m pytest apps/vault/tests/test_vault_api.py -v`
Expected: All tests pass (old + new).

- [ ] **Step 3: Commit**

```bash
git add apps/vault/tests/test_vault_api.py
git commit -m "feat: add audit-log endpoint tests"
```

---

### Task 3: Upgrade Seed Data with Real Evidence File

**Files:**
- Modify: `kotoku-backend/apps/templates/management/commands/seed_test_data.py`

- [ ] **Step 1: Update the `_seal` method to upload a real PNG to MinIO**

Replace the `EvidenceItem.objects.get_or_create(...)` block in the `_seal` method with:

```python
        import hashlib

        from infrastructure.storage.s3 import S3StorageClient

        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        file_hash = hashlib.sha256(png_bytes).hexdigest()
        file_key = "test-data/vehicle_front.png"
        storage_url = S3StorageClient().upload(
            file_key, png_bytes, content_type="image/png"
        )

        EvidenceItem.objects.get_or_create(
            agreement=agreement,
            evidence_type="vehicle_photo_front",
            defaults={
                "file_type": EvidenceItem.FileType.PHOTO,
                "mime_type": "image/png",
                "size_bytes": len(png_bytes),
                "file_key": file_key,
                "file_hash": file_hash,
                "storage_url": storage_url,
                "original_name": "vehicle_front.png",
                "upload_status": EvidenceItem.UploadStatus.CONFIRMED,
            },
        )
```

The full `_seal` method becomes:

```python
    def _seal(self, agreement):
        from unittest.mock import patch

        import apps.consent.services as consent_module

        if agreement.status != Agreement.Status.DRAFT:
            self.stdout.write(f"Agreement already in {agreement.status}, skipping seal.")
            return

        captured_otps = []
        real_generate_otp = consent_module.generate_otp

        def capture_otp(length=8):
            otp = real_generate_otp(length)
            captured_otps.append(otp)
            return otp

        with patch.object(consent_module, "generate_otp", side_effect=capture_otp):
            records = ConsentService.request_otp(agreement_id=agreement.pk)

        phone_to_otp = {}
        for record, otp in zip(records, captured_otps):
            phone_to_otp[record.party.phone] = otp

        for phone, otp in phone_to_otp.items():
            ConsentService.confirm_by_phone(
                agreement_id=agreement.pk,
                party_phone=phone,
                otp_code=otp,
            )

        import hashlib

        from infrastructure.storage.s3 import S3StorageClient

        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        file_hash = hashlib.sha256(png_bytes).hexdigest()
        file_key = "test-data/vehicle_front.png"
        storage_url = S3StorageClient().upload(
            file_key, png_bytes, content_type="image/png"
        )

        EvidenceItem.objects.get_or_create(
            agreement=agreement,
            evidence_type="vehicle_photo_front",
            defaults={
                "file_type": EvidenceItem.FileType.PHOTO,
                "mime_type": "image/png",
                "size_bytes": len(png_bytes),
                "file_key": file_key,
                "file_hash": file_hash,
                "storage_url": storage_url,
                "original_name": "vehicle_front.png",
                "upload_status": EvidenceItem.UploadStatus.CONFIRMED,
            },
        )

        AgreementService.seal_agreement(agreement_id=agreement.pk)

        from apps.vault.services import VaultService

        VaultService.create_for_agreement(agreement_id=agreement.pk)
```

- [ ] **Step 2: Run the seed command to verify**

Run: `cd kotoku-backend && python manage.py seed_test_data --sealed`
Expected: Output includes seeded data with tokens, no errors about S3 upload.

- [ ] **Step 3: Commit**

```bash
git add apps/templates/management/commands/seed_test_data.py
git commit -m "feat: upgrade seed data with real MinIO evidence file"
```

---

### Task 4: Add Smoke Test Management Command

**Files:**
- Create: `kotoku-backend/apps/templates/management/commands/test_vault_export.py`

- [ ] **Step 1: Create the smoke test command**

```python
from django.core.management.base import BaseCommand
from django.test import override_settings

from apps.vault.models import VaultEntry


class Command(BaseCommand):
    help = "Smoke test: generate PDF for a sealed vault entry and verify it succeeds"

    def add_arguments(self, parser):
        parser.add_argument(
            "--entry-id",
            type=int,
            help="Specific VaultEntry ID to test (defaults to the most recent sealed entry)",
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def handle(self, *args, **options):
        from apps.vault.tasks import generate_pdf_export

        entry_id = options.get("entry_id")
        if not entry_id:
            entry = (
                VaultEntry.objects.filter(
                    agreement__status="sealed",
                    pdf_status__in=["pending", "failed"],
                )
                .order_by("-created_at")
                .first()
            )
            if not entry:
                self.stdout.write(self.style.ERROR("No sealed vault entry found to test."))
                return
            entry_id = entry.pk

        self.stdout.write(f"Testing PDF export for vault entry {entry_id}...")

        try:
            generate_pdf_export.apply(kwargs={"vault_entry_id": entry_id})
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Task failed: {exc}"))
            return

        entry = VaultEntry.objects.get(pk=entry_id)
        if entry.pdf_status == VaultEntry.PdfStatus.READY and entry.pdf_url:
            self.stdout.write(self.style.SUCCESS(f"PDF export succeeded!"))
            self.stdout.write(f"  pdf_status: {entry.pdf_status}")
            self.stdout.write(f"  pdf_url:    {entry.pdf_url}")
        else:
            self.stdout.write(self.style.ERROR(
                f"PDF export did not complete. Status: {entry.pdf_status}"
            ))
```

- [ ] **Step 2: Run the smoke test**

Run: `cd kotoku-backend && python manage.py test_vault_export`
Expected: "PDF export succeeded!" with a MinIO URL.

- [ ] **Step 3: Commit**

```bash
git add apps/templates/management/commands/test_vault_export.py
git commit -m "feat: add vault PDF export smoke test command"
```

---

### Task 5: Run Full Test Suite

**Files:** None (verification only)

- [ ] **Step 1: Run all vault tests**

Run: `cd kotoku-backend && python -m pytest apps/vault/tests/ -v`
Expected: All tests pass.

- [ ] **Step 2: Run the full test suite to check for regressions**

Run: `cd kotoku-backend && python -m pytest --tb=short -q`
Expected: All tests pass.
