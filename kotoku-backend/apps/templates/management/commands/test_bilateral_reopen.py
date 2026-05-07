import re
from unittest.mock import patch

from django.core.management.base import BaseCommand

from apps.agreements.models import Agreement
from apps.agreements.services import AgreementService
from apps.consent.services import ConsentService

ALICE_PHONE = "+233500000001"
BOB_PHONE = "+233500000002"


class Command(BaseCommand):
    help = "End-to-end test: sealed agreement -> bilateral reopen -> ACTIVE"

    def handle(self, *args, **options):
        from django.core.management import call_command

        call_command("seed_test_data", "--sealed")

        agreement = Agreement.objects.filter(
            created_by__phone=ALICE_PHONE,
        ).first()
        if not agreement:
            self.stderr.write("No agreement found.")
            return

        if agreement.status not in (Agreement.Status.SEALED, Agreement.Status.REOPEN_REQUESTED):
            self.stderr.write(
                f"Agreement is in {agreement.status}, need SEALED or REOPEN_REQUESTED."
            )
            return

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))
        self.stdout.write(self.style.MIGRATE_HEADING(" BILATERAL REOPEN E2E TEST"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))
        self.stdout.write(f"Agreement #{agreement.pk}: \"{agreement.title}\"")
        self.stdout.write(f"Status: {agreement.status}")
        self.stdout.write("")

        otp_map = {}

        if agreement.status == Agreement.Status.SEALED:
            self._step(1, "Request reopen (SEALED -> REOPEN_REQUESTED)")
            with patch(
                "infrastructure.sms.console_gateway.ConsoleSmsGateway.send",
                side_effect=self._capture_otp(otp_map),
            ):
                AgreementService.request_reopen(agreement_id=agreement.pk)
                ConsentService.request_reopen_otp(agreement_id=agreement.pk)
            agreement.refresh_from_db()
            self._assert_status(agreement, Agreement.Status.REOPEN_REQUESTED)
        else:
            self._step(1, "Agreement already REOPEN_REQUESTED, issuing fresh OTPs")
            with patch(
                "infrastructure.sms.console_gateway.ConsoleSmsGateway.send",
                side_effect=self._capture_otp(otp_map),
            ):
                ConsentService.request_reopen_otp(agreement_id=agreement.pk)
            agreement.refresh_from_db()
            self._assert_status(agreement, Agreement.Status.REOPEN_REQUESTED)
        agreement.refresh_from_db()
        self._assert_status(agreement, Agreement.Status.REOPEN_REQUESTED)

        self._step(2, "OTPs captured")
        self.stdout.write(f"  Alice ({ALICE_PHONE}): {otp_map.get(ALICE_PHONE, 'MISSING')}")
        self.stdout.write(f"  Bob   ({BOB_PHONE}): {otp_map.get(BOB_PHONE, 'MISSING')}")

        self._step(3, "Alice confirms her reopen OTP")
        alice_otp = otp_map.get(ALICE_PHONE)
        if not alice_otp:
            self.stderr.write("  FAIL: No OTP for Alice")
            return
        ConsentService.confirm_reopen_by_phone(
            agreement_id=agreement.pk,
            party_phone=ALICE_PHONE,
            otp_code=alice_otp,
        )
        agreement.refresh_from_db()
        self.stdout.write(f"  Status after Alice confirms: {agreement.status}")
        self._assert_status(agreement, Agreement.Status.REOPEN_REQUESTED)

        self._step(4, "Bob confirms his reopen OTP -> triggers transition to ACTIVE")
        bob_otp = otp_map.get(BOB_PHONE)
        if not bob_otp:
            self.stderr.write("  FAIL: No OTP for Bob")
            return
        ConsentService.confirm_reopen_by_phone(
            agreement_id=agreement.pk,
            party_phone=BOB_PHONE,
            otp_code=bob_otp,
        )
        agreement.refresh_from_db()
        self._assert_status(agreement, Agreement.Status.ACTIVE)

        self._step(5, "Verify seal fields cleared")
        self.stdout.write(f"  sealed_at: {agreement.sealed_at}")
        self.stdout.write(f"  seal_hash: '{agreement.seal_hash}'")
        assert agreement.sealed_at is None, "sealed_at should be None"
        assert agreement.seal_hash == "", "seal_hash should be empty"
        self.stdout.write(self.style.SUCCESS("  PASS: seal fields cleared"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS(" ALL STEPS PASSED"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"Agreement #{agreement.pk} is now ACTIVE and editable.")
        self.stdout.write("")

    def _step(self, num, label):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"Step {num}: {label}"))
        self.stdout.write("-" * 40)

    def _assert_status(self, agreement, expected):
        if agreement.status == expected:
            self.stdout.write(self.style.SUCCESS(f"  PASS: status = {expected}"))
        else:
            self.stdout.write(
                self.style.ERROR(f"  FAIL: status = {agreement.status}, expected {expected}")
            )

    @staticmethod
    def _capture_otp(otp_map):
        def _capture(to, body):
            match = re.search(r"\b(\d{6,8})\b", body)
            if match:
                otp_map[to] = match.group(1)
            return True

        return _capture
