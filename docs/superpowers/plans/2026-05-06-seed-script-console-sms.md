# Seed Script + Console SMS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a `manage.py seed_test_data` command and a console SMS backend so OTPs print to terminal during development.

**Architecture:** Factory pattern for SMS gateway selection (`get_sms_gateway()`). Management command creates users, identities, agreement, and optionally runs the full consent+seal flow. All creates are idempotent via `get_or_create`.

**Tech Stack:** Django management command, DRF Token, Redis cache, existing service layer (ConsentService, AgreementService).

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `infrastructure/sms/__init__.py` | Create | Export `get_sms_gateway()` factory |
| `infrastructure/sms/console_gateway.py` | Create | Print OTPs to stdout |
| `config/settings/base.py` | Modify | Add `SMS_BACKEND` setting |
| `apps/auth/services.py` | Modify | Use `get_sms_gateway()` |
| `apps/consent/services.py` | Modify | Use `get_sms_gateway()` |
| `apps/notifications/providers/sms_provider.py` | Modify | Use `get_sms_gateway()` |
| `apps/templates/management/commands/seed_test_data.py` | Create | Seed command |
| `.env.example` | Modify | Add `SMS_BACKEND` option |
| `apps/auth/tests/test_auth_service.py` | Modify | Add test for console gateway |
| `apps/templates/tests/test_seed_command.py` | Create | Tests for seed command |

---

### Task 1: Console SMS Gateway

**Files:**
- Create: `kotoku-backend/infrastructure/sms/__init__.py`
- Create: `kotoku-backend/infrastructure/sms/console_gateway.py`
- Modify: `kotoku-backend/config/settings/base.py` (line 129, after SMS settings)
- Modify: `kotoku-backend/apps/auth/services.py` (line 9, 29)
- Modify: `kotoku-backend/apps/consent/services.py` (line 21, 184, 251)
- Modify: `kotoku-backend/apps/notifications/providers/sms_provider.py` (line 1, 8)
- Modify: `kotoku-backend/.env.example` (after line 21)

- [ ] **Step 1: Create `infrastructure/sms/console_gateway.py`**

```python
import re
import sys


class ConsoleSmsGateway:
    def send(self, to: str, body: str) -> bool:
        otp_match = re.search(r"\b(\d{6,8})\b", body)
        otp_hint = f"   OTP: {otp_match.group(1)}" if otp_match else ""
        print(f"\U0001F4F1 SMS to {to}: \"{body}\"", file=sys.stdout)
        if otp_hint:
            print(otp_hint, file=sys.stdout)
        return True
```

- [ ] **Step 2: Create `infrastructure/sms/__init__.py`**

```python
from django.conf import settings

from infrastructure.sms.console_gateway import ConsoleSmsGateway
from infrastructure.sms.gateway import SmsGateway


def get_sms_gateway():
    if getattr(settings, "SMS_BACKEND", "africastalking") == "console":
        return ConsoleSmsGateway()
    return SmsGateway()
```

- [ ] **Step 3: Add `SMS_BACKEND` to `config/settings/base.py`**

After the existing SMS settings (line 129), add:

```python
SMS_BACKEND = os.getenv("SMS_BACKEND", "africastalking")
```

- [ ] **Step 4: Update `apps/auth/services.py`**

Change line 9 from:
```python
from infrastructure.sms.gateway import SmsGateway
```
to:
```python
from infrastructure.sms import get_sms_gateway
```

Change line 29 from:
```python
            SmsGateway().send(to=phone, body=f"Your Kotoku verification code is {otp_code}. Valid for 10 minutes.")
```
to:
```python
            get_sms_gateway().send(to=phone, body=f"Your Kotoku verification code is {otp_code}. Valid for 10 minutes.")
```

- [ ] **Step 5: Update `apps/consent/services.py`**

Change line 21 from:
```python
from infrastructure.sms.gateway import SmsGateway
```
to:
```python
from infrastructure.sms import get_sms_gateway
```

Change line 184 from:
```python
        gateway = SmsGateway()
```
to:
```python
        gateway = get_sms_gateway()
```

Change line 251 from:
```python
        gateway = SmsGateway()
```
to:
```python
        gateway = get_sms_gateway()
```

- [ ] **Step 6: Update `apps/notifications/providers/sms_provider.py`**

Change line 1 from:
```python
from infrastructure.sms.gateway import SmsGateway
```
to:
```python
from infrastructure.sms import get_sms_gateway
```

Change lines 7-8 from:
```python
    def __init__(self) -> None:
        self.gateway = SmsGateway()
```
to:
```python
    def __init__(self) -> None:
        self.gateway = get_sms_gateway()
```

- [ ] **Step 7: Update `.env.example`**

After line 21 (`SMS_SENDER_ID=KOTOKU`), add:

```
# SMS_BACKEND=console   # Print OTPs to terminal instead of Africa's Talking
```

- [ ] **Step 8: Run existing tests to verify nothing broke**

Run: `docker compose exec web pytest -x`
Expected: All tests PASS

- [ ] **Step 9: Commit**

```bash
git add infrastructure/sms/__init__.py infrastructure/sms/console_gateway.py config/settings/base.py apps/auth/services.py apps/consent/services.py apps/notifications/providers/sms_provider.py .env.example
git commit -m "feat: add console SMS backend for dev OTP printing"
```

---

### Task 2: Seed Command

**Files:**
- Create: `kotoku-backend/apps/templates/management/commands/seed_test_data.py`

- [ ] **Step 1: Create the seed command**

```python
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.accounts.models import Account, User
from apps.agreements.models import Agreement
from apps.agreements.services import AgreementService
from apps.consent.services import ConsentService, generate_otp, hash_otp, verify_otp_hash
from apps.evidence.models import EvidenceItem
from apps.identity.models import IdentityRecord
from apps.parties.models import Party


TEST_USERS = [
    {
        "phone": "+233500000001",
        "full_name": "Alice Test",
        "email": "alice@kotoku.test",
        "identity_ref": "GHA-000000001",
    },
    {
        "phone": "+233500000002",
        "full_name": "Bob Test",
        "email": "bob@kotoku.test",
        "identity_ref": "GHA-000000002",
    },
]


class Command(BaseCommand):
    help = "Seed repeatable test data (users, identities, agreement)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sealed",
            action="store_true",
            help="Run full consent flow and seal the agreement",
        )

    def handle(self, *args, **options):
        call_command("seed_templates", verbosity=0)

        accounts = []
        tokens = []
        identities = []
        for user_data in TEST_USERS:
            user, _ = User.objects.get_or_create(phone=user_data["phone"])
            account, _ = Account.objects.get_or_create(
                user=user,
                defaults={
                    "email": user_data["email"],
                    "phone": user_data["phone"],
                    "full_name": user_data["full_name"],
                },
            )
            identity, _ = IdentityRecord.objects.get_or_create(
                reference=user_data["identity_ref"],
                defaults={
                    "account": account,
                    "verification_type": IdentityRecord.VerificationType.GHANA_CARD,
                    "verified_at": timezone.now(),
                },
            )
            token, _ = Token.objects.get_or_create(user=user)
            accounts.append(account)
            tokens.append(token)
            identities.append(identity)

        agreement, created = Agreement.objects.get_or_create(
            title="Cash Sale - Toyota Corolla 2020",
            defaults={
                "description": "Test agreement for on-device testing",
                "scenario_template": "used_vehicle_sale",
                "status": Agreement.Status.DRAFT,
                "created_by": accounts[0],
            },
        )
        if created:
            Party.objects.get_or_create(
                agreement=agreement,
                role=Party.Role.BUYER,
                defaults={
                    "identity": identities[0],
                    "display_name": "Alice Test",
                    "phone": TEST_USERS[0]["phone"],
                    "id_type": Party.IdType.GHANA_CARD,
                    "id_number": TEST_USERS[0]["identity_ref"],
                },
            )
            Party.objects.get_or_create(
                agreement=agreement,
                role=Party.Role.SELLER,
                defaults={
                    "identity": identities[1],
                    "display_name": "Bob Test",
                    "phone": TEST_USERS[1]["phone"],
                    "id_type": Party.IdType.GHANA_CARD,
                    "id_number": TEST_USERS[1]["identity_ref"],
                },
            )

        if options["sealed"] and agreement.status == Agreement.Status.DRAFT:
            self._seal_agreement(agreement)

        self._print_summary(tokens, identities, agreement)

    def _seal_agreement(self, agreement):
        agreement.refresh_from_db()
        records = ConsentService.request_otp(agreement_id=agreement.pk)

        for record in records:
            record.refresh_from_db()
            parties = list(Party.objects.filter(agreement=agreement))
            for party in parties:
                ungranted = ConsentRecord.objects.filter(
                    agreement=agreement,
                    party=party,
                    granted=False,
                ).first()
                if ungranted is None:
                    continue
                for otp_attempt in range(10):
                    test_otp = f"{otp_attempt:08d}"
                    if verify_otp_hash(test_otp, ungranted.otp_code_hash):
                        ConsentService.confirm_by_phone(
                            agreement_id=agreement.pk,
                            party_phone=party.phone,
                            otp_code=test_otp,
                        )
                        break

        agreement.refresh_from_db()

        if agreement.status in (Agreement.Status.PENDING_CONSENT, Agreement.Status.ACTIVE):
            EvidenceItem.objects.get_or_create(
                agreement=agreement,
                evidence_type="signature",
                defaults={
                    "file_type": "photo",
                    "mime_type": "image/png",
                    "size_bytes": 0,
                    "file_key": "seed/test-signature.png",
                    "storage_url": "",
                    "original_name": "test-signature.png",
                    "upload_status": "confirmed",
                },
            )
            AgreementService.seal_agreement(agreement_id=agreement.pk)

    def _print_summary(self, tokens, identities, agreement):
        self.stdout.write(self.style.SUCCESS("Seeded test data"))
        self.stdout.write("=" * 40)
        for i, user_data in enumerate(TEST_USERS):
            self.stdout.write(f"\n{user_data['full_name']} ({user_data['phone']})")
            self.stdout.write(f"  Token: {tokens[i].key}")
            self.stdout.write(f"  Identity: {user_data['identity_ref']}")
        agreement.refresh_from_db()
        self.stdout.write(f"\nAgreement: \"{agreement.title}\" ({agreement.status})")
        self.stdout.write(f"  GET /api/agreements/{agreement.pk}/")
        self.stdout.write("=" * 40)
```

Note: The `_seal_agreement` method uses a brute-force OTP crack (10 attempts) because the OTP is generated with `secrets.choice` and the hash is stored — there's no way to retrieve the plaintext from the hash. Since `generate_otp` produces an 8-digit code (10^8 possibilities), brute-forcing won't work. Instead, we need to capture the OTP at generation time.

**Revised approach for `_seal_agreement`:** Monkey-patch `generate_otp` to capture generated OTPs during `ConsentService.request_otp`, then use them to confirm.

Replace the `_seal_agreement` method above with:

```python
    def _seal_agreement(self, agreement):
        from unittest.mock import patch

        agreement.refresh_from_db()

        captured_otp_by_phone = {}

        original_generate_otp = ConsentService.__module__

        import apps.consent.services as consent_module

        real_generate_otp = consent_module.generate_otp

        def capturing_generate_otp(length=8):
            otp = real_generate_otp(length)
            return otp

        otp_store = {}

        with patch.object(consent_module, "generate_otp", wraps=real_generate_otp) as mock_gen:
            mock_gen.side_effect = lambda length=8: real_generate_otp(length)
            records = ConsentService.request_otp(agreement_id=agreement.pk)

            party_phones = {
                record.party_id: Party.objects.get(pk=record.party_id).phone
                for record in records
            }

            generated_otp_calls = mock_gen.call_args_list
            for i, record in enumerate(records):
                if i < len(generated_otp_calls):
                    otp = generated_otp_calls[i][0][0] if generated_otp_calls[i][0] else generated_otp_calls[i][1].get("length", 8)
                    otp_store[party_phones[record.party_id]] = None

        for record in records:
            party = Party.objects.get(pk=record.party_id)
            ungranted_qs = ConsentRecord.objects.filter(
                agreement=agreement,
                party=party,
                granted=False,
            )
            if not ungranted_qs.exists():
                continue
            ungranted = ungranted_qs.first()
            for digit in range(100000000):
                test_otp = f"{digit:08d}"
                if verify_otp_hash(test_otp, ungranted.otp_code_hash):
                    ConsentService.confirm_by_phone(
                        agreement_id=agreement.pk,
                        party_phone=party.phone,
                        otp_code=test_otp,
                    )
                    break

        agreement.refresh_from_db()

        if agreement.status in (Agreement.Status.PENDING_CONSENT, Agreement.Status.ACTIVE):
            EvidenceItem.objects.get_or_create(
                agreement=agreement,
                evidence_type="signature",
                defaults={
                    "file_type": "photo",
                    "mime_type": "image/png",
                    "size_bytes": 0,
                    "file_key": "seed/test-signature.png",
                    "storage_url": "",
                    "original_name": "test-signature.png",
                    "upload_status": "confirmed",
                },
            )
            AgreementService.seal_agreement(agreement_id=agreement.pk)
```

**Wait — brute-forcing 10^8 OTPs is too slow.** The correct approach is to capture OTPs from `generate_otp` via `unittest.mock.patch`. Let me write the final correct version:

```python
    def _seal_agreement(self, agreement):
        from unittest.mock import patch
        import apps.consent.services as consent_module

        agreement.refresh_from_db()

        captured_otp_calls = []
        real_generate_otp = consent_module.generate_otp

        def capture_otp(length=8):
            otp = real_generate_otp(length)
            captured_otp_calls.append(otp)
            return otp

        with patch.object(consent_module, "generate_otp", side_effect=capture_otp):
            records = ConsentService.request_otp(agreement_id=agreement.pk)

        for i, record in enumerate(records):
            if i >= len(captured_otp_calls):
                break
            otp = captured_otp_calls[i]
            party = Party.objects.get(pk=record.party_id)
            ConsentService.confirm_by_phone(
                agreement_id=agreement.pk,
                party_phone=party.phone,
                otp_code=otp,
            )

        agreement.refresh_from_db()

        if agreement.status in (Agreement.Status.PENDING_CONSENT, Agreement.Status.ACTIVE):
            EvidenceItem.objects.get_or_create(
                agreement=agreement,
                evidence_type="signature",
                defaults={
                    "file_type": "photo",
                    "mime_type": "image/png",
                    "size_bytes": 0,
                    "file_key": "seed/test-signature.png",
                    "storage_url": "",
                    "original_name": "test-signature.png",
                    "upload_status": "confirmed",
                },
            )
            AgreementService.seal_agreement(agreement_id=agreement.pk)
```

- [ ] **Step 2: Verify the command runs inside Docker**

Run: `docker compose exec web python manage.py seed_test_data`
Expected: Output with tokens, identities, and agreement URL.

- [ ] **Step 3: Verify `--sealed` flag works**

Run: `docker compose exec web python manage.py seed_test_data --sealed`
Expected: Agreement status shows `sealed`.

- [ ] **Step 4: Run full test suite**

Run: `docker compose exec web pytest -x`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/templates/management/commands/seed_test_data.py
git commit -m "feat: add seed_test_data management command"
```

---

### Task 3: Verification

- [ ] **Step 1: Test idempotency — run seed command twice**

Run: `docker compose exec web python manage.py seed_test_data --sealed && docker compose exec web python manage.py seed_test_data --sealed`
Expected: No errors, same output both times.

- [ ] **Step 2: Test console SMS backend**

Set `SMS_BACKEND=console` in `.env`, restart Docker, then run the seed command with `--sealed`. Expected: OTP lines printed to stdout.

- [ ] **Step 3: Final test suite run**

Run: `docker compose exec web pytest`
Expected: All tests PASS.

- [ ] **Step 4: Commit final state if any fixes were needed**
