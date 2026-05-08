# PDF Generation Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix stuck PDF generation, add real-time WebSocket status push, auto-generate on seal, and enrich PDF content.

**Architecture:** Celery task with bulletproof error handling + WebSocket push notifications via existing `send_to_user()` helper. PDF auto-triggers on seal. Beat task recovers stuck entries. Frontend receives status changes via WebSocket instead of polling.

**Tech Stack:** Django, Celery, ReportLab, Django Channels (Redis), boto3/S3

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `apps/vault/services.py` | Modify | Add `retry_export()`, auto-trigger in `create_for_agreement()`, add `_push_vault_event()` helper |
| `apps/vault/tasks.py` | Modify | Bulletproof try/except, `on_failure` handler, timeouts, WS pushes, stuck recovery task |
| `apps/vault/pdf.py` | Modify | Add field_data, full seal hash, revision history, annotations sections |
| `apps/vault/api/views.py` | Modify | Add `VaultRetryExportView` |
| `apps/vault/api/urls.py` | Modify | Add retry URL route |
| `config/settings/base.py` | Modify | Add Beat schedule for stuck recovery |
| `apps/vault/tests/test_vault_api.py` | Modify | Add tests for retry, auto-generate, stuck recovery |

---

### Task 1: Add WS push helper to VaultService

**Files:**
- Modify: `kotoku-backend/apps/vault/services.py`

- [ ] **Step 1: Add `_push_vault_event` static method to VaultService**

Add import and method at the top of `services.py` after existing imports (after line 9):

```python
from apps.agreements.models import Party
from apps.notifications.push import send_to_user
```

Add this method inside `VaultService` class (after `mark_pdf_failed`, around line 90):

```python
    @staticmethod
    def _push_vault_event(*, agreement_id: int, event_type: str, payload: dict | None = None):
        parties = Party.objects.filter(agreement_id=agreement_id).select_related("account")
        for p in parties:
            if p.phone:
                send_to_user(p.phone, event_type, payload or {"agreement_id": agreement_id})
```

- [ ] **Step 2: Commit**

```bash
git add kotoku-backend/apps/vault/services.py
git commit -m "feat: add _push_vault_event helper to VaultService"
```

---

### Task 2: Bulletproof Celery task with WS pushes and on_failure

**Files:**
- Modify: `kotoku-backend/apps/vault/tasks.py`

- [ ] **Step 1: Replace entire `generate_pdf_export` task with hardened version**

Replace the task decorator and function (lines 9-36) with:

```python
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=120,
    soft_time_limit=90,
)
def generate_pdf_export(self, vault_entry_id: int) -> None:
    from apps.vault.models import VaultEntry
    from apps.vault.pdf import render_vault_pdf
    from apps.vault.services import VaultService
    from infrastructure.storage.s3 import S3StorageClient

    try:
        entry = VaultEntry.objects.select_related("agreement").get(pk=vault_entry_id)
        agreement_id = entry.agreement_id

        VaultService._push_vault_event(
            agreement_id=agreement_id,
            event_type="vault.pdf_generating",
        )

        pdf_bytes = render_vault_pdf(vault_entry_id)
        key = f"exports/agreement-{entry.agreement_id}-vault-{vault_entry_id}.pdf"
        pdf_url = S3StorageClient().upload(key, pdf_bytes, content_type="application/pdf")

        VaultService.mark_pdf_ready(vault_entry_id=vault_entry_id, pdf_url=pdf_url)
        VaultService._push_vault_event(
            agreement_id=agreement_id,
            event_type="vault.pdf_ready",
            payload={"agreement_id": agreement_id, "pdf_url": pdf_url},
        )
        logger.info("PDF generated for vault_entry=%s -> %s", vault_entry_id, pdf_url)
    except Exception as exc:
        logger.exception("PDF generation failed for vault_entry=%s", vault_entry_id)
        try:
            VaultService.mark_pdf_failed(vault_entry_id=vault_entry_id)
            entry = VaultEntry.objects.select_related("agreement").get(pk=vault_entry_id)
            VaultService._push_vault_event(
                agreement_id=entry.agreement_id,
                event_type="vault.pdf_failed",
            )
        except Exception:
            logger.exception("Could not mark vault_entry=%s as failed", vault_entry_id)
        raise self.retry(exc=exc)

    @classmethod
    def on_failure(cls, exc, task_id, args, kwargs, einfo):
        vault_entry_id = args[0] if args else None
        if vault_entry_id is None:
            return
        try:
            from apps.vault.models import VaultEntry
            from apps.vault.services import VaultService

            VaultService.mark_pdf_failed(vault_entry_id=vault_entry_id)
            entry = VaultEntry.objects.select_related("agreement").get(pk=vault_entry_id)
            VaultService._push_vault_event(
                agreement_id=entry.agreement_id,
                event_type="vault.pdf_failed",
            )
        except Exception:
            logger.exception("on_failure: could not process vault_entry=%s", vault_entry_id)
```

- [ ] **Step 2: Commit**

```bash
git add kotoku-backend/apps/vault/tasks.py
git commit -m "feat: harden generate_pdf_export with timeouts, WS pushes, on_failure"
```

---

### Task 3: Auto-generate PDF on seal

**Files:**
- Modify: `kotoku-backend/apps/vault/services.py`

- [ ] **Step 1: Update `create_for_agreement` to auto-trigger PDF generation**

Replace the `create_for_agreement` method (lines 16-36) with:

```python
    @staticmethod
    def create_for_agreement(*, agreement_id: int) -> VaultEntry:
        agreement = Agreement.objects.get(pk=agreement_id)
        if agreement.status != AgreementStatus.SEALED:
            raise DomainError("Vault entries can only be created for sealed agreements.")

        entry, created = VaultEntry.objects.get_or_create(
            agreement=agreement,
            defaults={"retain_until": VaultEntry.default_retain_until()},
        )

        should_generate = (
            created
            or entry.pdf_status in (VaultEntry.PdfStatus.PENDING, VaultEntry.PdfStatus.FAILED)
        )
        if should_generate:
            entry.pdf_status = VaultEntry.PdfStatus.PENDING
            entry.pdf_url = ""
            entry.save(update_fields=["pdf_status", "pdf_url", "updated_at"])

            from apps.vault.tasks import generate_pdf_export
            generate_pdf_export.delay(entry.pk)

        if created:
            AuditService.record_event(
                event_type="vault.entry_created",
                entity_type="vault_entry",
                entity_id=str(entry.pk),
                metadata={"agreement_id": agreement_id},
            )
        return entry
```

- [ ] **Step 2: Commit**

```bash
git add kotoku-backend/apps/vault/services.py
git commit -m "feat: auto-generate PDF on vault entry creation"
```

---

### Task 4: Add retry export endpoint

**Files:**
- Modify: `kotoku-backend/apps/vault/services.py`
- Modify: `kotoku-backend/apps/vault/api/views.py`
- Modify: `kotoku-backend/apps/vault/api/urls.py`

- [ ] **Step 1: Add `retry_export` method to VaultService**

Add after `mark_pdf_failed` method (after the `_push_vault_event` method added in Task 1):

```python
    @staticmethod
    @transaction.atomic
    def retry_export(*, agreement_id: int) -> VaultEntry:
        try:
            entry = VaultEntry.objects.select_for_update().get(agreement_id=agreement_id)
        except VaultEntry.DoesNotExist:
            raise DomainError("No vault entry found for this agreement.") from None

        if entry.pdf_status != VaultEntry.PdfStatus.FAILED:
            raise DomainError("Can only retry failed PDF generation.")

        entry.pdf_status = VaultEntry.PdfStatus.PENDING
        entry.save(update_fields=["pdf_status", "updated_at"])

        from apps.vault.tasks import generate_pdf_export
        generate_pdf_export.delay(entry.pk)

        AuditService.record_event(
            event_type="vault.export_retry_requested",
            entity_type="vault_entry",
            entity_id=str(entry.pk),
            metadata={"agreement_id": agreement_id},
        )
        return entry
```

- [ ] **Step 2: Add `VaultRetryExportView` to views.py**

Add after `VaultExportView` class (after line 76):

```python
class VaultRetryExportView(APIView):
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

        entry = VaultService.retry_export(agreement_id=agreement_id)
        return ok({"vault_entry": VaultEntrySerializer(entry).data}, status_code=202)
```

- [ ] **Step 3: Update urls.py**

Replace entire file:

```python
from django.urls import path

from .views import (
    VaultAuditLogView,
    VaultCollectionView,
    VaultDetailView,
    VaultExportView,
    VaultRetryExportView,
)

urlpatterns = [
    path("", VaultCollectionView.as_view(), name="vault-collection"),
    path("<int:agreement_id>/", VaultDetailView.as_view(), name="vault-detail"),
    path("<int:agreement_id>/export/", VaultExportView.as_view(), name="vault-export"),
    path("<int:agreement_id>/retry-export/", VaultRetryExportView.as_view(), name="vault-retry-export"),
    path("<int:agreement_id>/audit-log/", VaultAuditLogView.as_view(), name="vault-audit-log"),
]
```

- [ ] **Step 4: Commit**

```bash
git add kotoku-backend/apps/vault/services.py kotoku-backend/apps/vault/api/views.py kotoku-backend/apps/vault/api/urls.py
git commit -m "feat: add retry-export endpoint for failed PDF generation"
```

---

### Task 5: Add stuck task recovery Beat task

**Files:**
- Modify: `kotoku-backend/apps/vault/tasks.py`
- Modify: `kotoku-backend/config/settings/base.py`

- [ ] **Step 1: Add `recover_stuck_pdf_generating` task to tasks.py**

Add after the `generate_pdf_export` task and before `archive_expired_vault_entries`:

```python
@shared_task
def recover_stuck_pdf_generating() -> dict:
    from apps.vault.models import VaultEntry
    from apps.vault.services import VaultService

    cutoff = timezone.now() - timezone.timedelta(minutes=5)
    stuck = VaultEntry.objects.filter(
        pdf_status=VaultEntry.PdfStatus.GENERATING,
        updated_at__lt=cutoff,
    )
    entry_ids = list(stuck.values_list("pk", flat=True))

    if not entry_ids:
        return {"recovered": 0}

    for entry_id in entry_ids:
        try:
            VaultService.mark_pdf_failed(vault_entry_id=entry_id)
            entry = VaultEntry.objects.select_related("agreement").get(pk=entry_id)
            VaultService._push_vault_event(
                agreement_id=entry.agreement_id,
                event_type="vault.pdf_failed",
            )
        except Exception:
            logger.exception("recover_stuck: failed for vault_entry=%s", entry_id)

    logger.info("recover_stuck_pdf_generating: recovered %d entries", len(entry_ids))
    return {"recovered": len(entry_ids)}
```

- [ ] **Step 2: Add Beat schedule entry in base.py**

Add to `CELERY_BEAT_SCHEDULE` dict (after the existing `archive-expired-vault-entries` entry, around line 113):

```python
    "recover-stuck-pdf-generating": {
        "task": "apps.vault.tasks.recover_stuck_pdf_generating",
        "schedule": 300,  # every 5 minutes
    },
```

- [ ] **Step 3: Commit**

```bash
git add kotoku-backend/apps/vault/tasks.py kotoku-backend/config/settings/base.py
git commit -m "feat: add stuck PDF generation recovery Beat task"
```

---

### Task 6: Enrich PDF content

**Files:**
- Modify: `kotoku-backend/apps/vault/pdf.py`

- [ ] **Step 1: Update queryset to prefetch revisions and annotations**

In `render_vault_pdf`, replace the queryset (lines 79-83) with:

```python
    entry = (
        VaultEntry.objects.select_related("agreement", "agreement__created_by")
        .prefetch_related(
            "agreement__parties",
            "agreement__evidence_items",
            "agreement__revisions",
            "agreement__annotations",
        )
        .get(pk=entry_id)
    )
```

- [ ] **Step 2: Update body font size**

Change `_BODY` style fontSize from `10` to `10.5` (line 43):

```python
    fontSize=10.5,
```

- [ ] **Step 3: Add monospace style for hash display**

Add after `_SMALL` style definition (after line 51):

```python
_MONO = ParagraphStyle(
    "KotokuMono",
    parent=_STYLES["Normal"],
    fontSize=8,
    leading=11,
    fontName="Courier",
    textColor=colors.HexColor("#333333"),
)
```

- [ ] **Step 4: Add section label style**

Add after `_MONO`:

```python
_SECTION = ParagraphStyle(
    "KotokuSection",
    parent=_STYLES["Heading2"],
    fontSize=11,
    spaceBefore=14,
    spaceAfter=4,
    textColor=colors.HexColor("#1a1a2e"),
)
```

- [ ] **Step 5: Replace subheading style references with section style**

In the `render_vault_pdf` function, replace all `_SUBHEADING` with `_SECTION` for section headings:
- Line 113: `Paragraph("Parties", _SUBHEADING)` → `Paragraph("Parties", _SECTION)`
- Line 132: `Paragraph("Evidence", _SUBHEADING)` → `Paragraph("Evidence", _SECTION)`

Change spacer after core fields from `0.3 * cm` to `0.5 * cm` (line 110):

```python
    story.append(Spacer(1, 0.5 * cm))
```

- [ ] **Step 6: Show full seal hash in evidence table**

Replace the evidence hash display (line 142):

```python
                e.file_hash if e.file_hash else "—",
```

- [ ] **Step 7: Add field_data section after evidence, before integrity**

Insert after the evidence section (after line 148) and before the integrity section (line 150):

```python
    # ── Agreement Details (field_data) ──────────────────────────────────── #
    if agreement.field_data:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Agreement Details", _SECTION))
        fd_rows = [["Field", "Value"]]
        for key, value in agreement.field_data.items():
            label = key.replace("_", " ").title()
            fd_rows.append([label, str(value)])
        fd_table = Table(fd_rows, colWidths=[5 * cm, 11 * cm])
        fd_table.setStyle(_TABLE_STYLE)
        story.append(fd_table)

    # ── Revision History ────────────────────────────────────────────────── #
    revisions = list(agreement.revisions.all())
    if revisions:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Revision History", _SECTION))
        rev_data = [["#", "Sealed At", "Seal Hash"]]
        for rev in revisions:
            rev_data.append([
                str(rev.revision_number),
                _fmt_dt(rev.sealed_at),
                rev.seal_hash,
            ])
        rev_table = Table(rev_data, colWidths=[1.5 * cm, 4.5 * cm, 10 * cm])
        rev_table.setStyle(_TABLE_STYLE)
        story.append(rev_table)

    # ── Annotations ─────────────────────────────────────────────────────── #
    annotations = list(agreement.annotations.select_related("author_party").all())
    if annotations:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Notes", _SECTION))
        ann_data = [["Author", "Note", "Date"]]
        for ann in annotations:
            ann_data.append([
                ann.author_party.display_name,
                ann.body[:200],
                _fmt_dt(ann.created_at),
            ])
        ann_table = Table(ann_data, colWidths=[3.5 * cm, 9 * cm, 3.5 * cm])
        ann_table.setStyle(_TABLE_STYLE)
        story.append(ann_table)
```

- [ ] **Step 8: Update integrity footer to use monospace for seal hash**

Replace the seal hash paragraph (line 154-156) with:

```python
    story.append(Paragraph(
        f"<b>Seal hash (SHA-256):</b>",
        _SMALL,
    ))
    story.append(Paragraph(
        agreement.seal_hash or "—",
        _MONO,
    ))
```

- [ ] **Step 9: Commit**

```bash
git add kotoku-backend/apps/vault/pdf.py
git commit -m "feat: enrich PDF with field_data, revisions, annotations, full seal hash"
```

---

### Task 7: Update tests for auto-generate and retry

**Files:**
- Modify: `kotoku-backend/apps/vault/tests/test_vault_api.py`

- [ ] **Step 1: Add retry path constant**

Add after line 28 (`_EXPORT_PATH`):

```python
_RETRY_PATH = "/api/vault/{id}/retry-export/"
```

- [ ] **Step 2: Update `_sealed_agreement_with_vault` to account for auto-generate**

The helper now auto-triggers PDF generation. Wrap the auto-trigger in a patch for tests that don't want eager execution. Replace the helper function (lines 44-89) with:

```python
def _sealed_agreement_with_vault(account, initiator_phone, second_phone):
    agreement = Agreement.objects.create(
        title="Vault Test",
        created_by=account,
        scenario_template="used_vehicle_sale",
    )
    PartyService.set_parties(
        agreement_id=agreement.pk,
        initiator_account=account,
        parties_data=[
            {"role": "seller", "full_name": "Kofi", "phone": initiator_phone,
             "id_type": "ghana_card", "id_number": "GHA-S"},
            {"role": "buyer", "full_name": "Ama", "phone": second_phone,
             "id_type": "ghana_card", "id_number": "GHA-B"},
        ],
    )
    EvidenceItem.objects.create(
        agreement=agreement,
        file_type=EvidenceItem.FileType.PHOTO,
        evidence_type="vehicle_photo_front",
        mime_type="image/jpeg",
        upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        storage_url="https://storage.kotoku/fake/photo.jpg",
    )
    agreement.status = AgreementStatus.PENDING_CONSENT
    agreement.save()
    now = timezone.now()
    ConsentRecord.objects.bulk_create([
        ConsentRecord(
            agreement=agreement,
            party=p,
            otp_code_hash="fakehash",
            channel=ConsentRecord.Channel.SMS,
            granted=True,
            granted_at=now,
            expires_at=now + timedelta(minutes=10),
        )
        for p in agreement.parties.all()
    ])
    from apps.agreements.services import AgreementService
    agreement = AgreementService.seal_agreement(agreement_id=agreement.pk)

    fake_pdf = b"%PDF-fake"
    fake_url = "https://storage.kotoku/exports/test.pdf"
    with patch("apps.vault.pdf.render_vault_pdf", return_value=fake_pdf), \
         patch("infrastructure.storage.s3.S3StorageClient.upload", return_value=fake_url):
        entry = VaultService.create_for_agreement(agreement_id=agreement.pk)

    return agreement, entry
```

- [ ] **Step 3: Add test class for retry endpoint**

Add at the end of the file:

```python
@pytest.mark.django_db
class TestVaultRetryExport:
    def test_retry_failed_returns_202(self):
        client, acct = _make_client("+233700500001")
        agreement, entry = _sealed_agreement_with_vault(acct, acct.phone, "+233700500002")
        entry.pdf_status = VaultEntry.PdfStatus.FAILED
        entry.save()

        fake_pdf = b"%PDF-fake"
        fake_url = "https://storage.kotoku/exports/retry.pdf"
        with patch("apps.vault.pdf.render_vault_pdf", return_value=fake_pdf), \
             patch("infrastructure.storage.s3.S3StorageClient.upload", return_value=fake_url):
            resp = client.post(_RETRY_PATH.format(id=agreement.pk))

        assert resp.status_code == 202
        data = resp.json()["data"]["vault_entry"]
        assert data["pdf_status"] in (VaultEntry.PdfStatus.READY, VaultEntry.PdfStatus.PENDING)

    def test_retry_non_failed_returns_400(self):
        client, acct = _make_client("+233700500003")
        agreement, entry = _sealed_agreement_with_vault(acct, acct.phone, "+233700500004")

        resp = client.post(_RETRY_PATH.format(id=agreement.pk))
        assert resp.status_code == 400

    def test_auto_generate_on_seal(self):
        client, acct = _make_client("+233700500005")
        agreement = Agreement.objects.create(
            title="Auto PDF Test",
            created_by=acct,
            scenario_template="used_vehicle_sale",
        )
        PartyService.set_parties(
            agreement_id=agreement.pk,
            initiator_account=acct,
            parties_data=[
                {"role": "seller", "full_name": "Auto", "phone": acct.phone,
                 "id_type": "ghana_card", "id_number": "GHA-A"},
                {"role": "buyer", "full_name": "Test", "phone": "+233700500006",
                 "id_type": "ghana_card", "id_number": "GHA-T"},
            ],
        )
        agreement.status = AgreementStatus.PENDING_CONSENT
        agreement.save()
        now = timezone.now()
        ConsentRecord.objects.bulk_create([
            ConsentRecord(
                agreement=agreement,
                party=p,
                otp_code_hash="fakehash",
                channel=ConsentRecord.Channel.SMS,
                granted=True,
                granted_at=now,
                expires_at=now + timedelta(minutes=10),
            )
            for p in agreement.parties.all()
        ])

        from apps.agreements.services import AgreementService
        AgreementService.seal_agreement(agreement_id=agreement.pk)

        fake_pdf = b"%PDF-auto"
        fake_url = "https://storage.kotoku/exports/auto.pdf"
        with patch("apps.vault.pdf.render_vault_pdf", return_value=fake_pdf), \
             patch("infrastructure.storage.s3.S3StorageClient.upload", return_value=fake_url):
            entry = VaultService.create_for_agreement(agreement_id=agreement.pk)

        assert entry.pdf_status == VaultEntry.PdfStatus.READY
        assert entry.pdf_url == fake_url

    def test_retry_returns_404_for_other_users_agreement(self):
        client, acct = _make_client("+233700500007")
        _, other_acct = _make_client("+233700500008")
        agreement, entry = _sealed_agreement_with_vault(other_acct, other_acct.phone, "+233700500009")
        entry.pdf_status = VaultEntry.PdfStatus.FAILED
        entry.save()

        resp = client.post(_RETRY_PATH.format(id=agreement.pk))
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self):
        resp = APIClient().post(_RETRY_PATH.format(id=1))
        assert resp.status_code == 401
```

- [ ] **Step 4: Run tests**

Run: `cd kotoku-backend && python -m pytest apps/vault/tests/test_vault_api.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add kotoku-backend/apps/vault/tests/test_vault_api.py
git commit -m "feat: add tests for retry endpoint and auto-generate on seal"
```

---

### Task 8: Run full test suite and verify

**Files:** None (verification only)

- [ ] **Step 1: Run vault tests**

Run: `cd kotoku-backend && python -m pytest apps/vault/tests/ -v`
Expected: All PASS

- [ ] **Step 2: Run full test suite**

Run: `cd kotoku-backend && python -m pytest --tb=short -q`
Expected: All PASS, no regressions

- [ ] **Step 3: Run linting**

Run: `cd kotoku-backend && ruff check . --fix`
Expected: No errors

---

## Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| Bulletproof try/except in Celery task | Task 2 |
| Task timeouts (time_limit/soft_time_limit) | Task 2 |
| on_failure handler | Task 2 |
| WS push: vault.pdf_generating | Task 2 |
| WS push: vault.pdf_ready | Task 2 |
| WS push: vault.pdf_failed | Task 2 |
| Auto-generate on seal | Task 3 |
| Retry endpoint | Task 4 |
| Stuck task recovery Beat task | Task 5 |
| PDF: field_data table | Task 6 |
| PDF: full seal hash | Task 6 |
| PDF: revision history | Task 6 |
| PDF: annotations | Task 6 |
| PDF: typography improvements | Task 6 |
| Tests for all new features | Task 7 |
