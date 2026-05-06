from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

from apps.accounts.models import Account, User
from apps.agreements.models import Agreement
from apps.agreements.services import AgreementService
from apps.consent.services import ConsentService
from apps.evidence.models import EvidenceItem
from apps.identity.models import IdentityRecord
from apps.parties.models import Party


class Command(BaseCommand):
    help = "Seed repeatable test data (users, accounts, identities, agreement)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sealed",
            action="store_true",
            help="Run the full consent + seal flow so the agreement ends as SEALED",
        )

    def handle(self, *args, **options):
        from django.core.management import call_command

        call_command("seed_templates")

        alice_phone = "+233500000001"
        bob_phone = "+233500000002"

        alice_user, _ = User.objects.get_or_create(phone=alice_phone)
        bob_user, _ = User.objects.get_or_create(phone=bob_phone)

        alice_account, _ = Account.objects.get_or_create(
            user=alice_user,
            defaults={
                "email": "alice@test.kotoku",
                "phone": alice_phone,
                "full_name": "Alice Mensah",
            },
        )
        bob_account, _ = Account.objects.get_or_create(
            user=bob_user,
            defaults={
                "email": "bob@test.kotoku",
                "phone": bob_phone,
                "full_name": "Bob Osei",
            },
        )

        alice_identity, _ = IdentityRecord.objects.get_or_create(
            reference="GHA-000000001",
            defaults={
                "account": alice_account,
                "verification_type": IdentityRecord.VerificationType.GHANA_CARD,
                "verified_at": alice_account.created_at,
            },
        )
        bob_identity, _ = IdentityRecord.objects.get_or_create(
            reference="GHA-000000002",
            defaults={
                "account": bob_account,
                "verification_type": IdentityRecord.VerificationType.GHANA_CARD,
                "verified_at": bob_account.created_at,
            },
        )

        alice_token, _ = Token.objects.get_or_create(user=alice_user)
        bob_token, _ = Token.objects.get_or_create(user=bob_user)

        agreement_title = "Cash Sale - Toyota Corolla 2020"
        agreement, created = Agreement.objects.get_or_create(
            title=agreement_title,
            defaults={
                "description": "Cash sale of a 2020 Toyota Corolla between Alice (buyer) and Bob (seller).",
                "scenario_template": "used_vehicle_sale",
                "created_by": alice_account,
            },
        )

        Party.objects.get_or_create(
            agreement=agreement,
            role=Party.Role.BUYER,
            defaults={
                "identity": alice_identity,
                "display_name": "Alice Mensah",
                "phone": alice_phone,
                "id_type": Party.IdType.GHANA_CARD,
                "id_number": "GHA-000000001",
            },
        )
        Party.objects.get_or_create(
            agreement=agreement,
            role=Party.Role.SELLER,
            defaults={
                "identity": bob_identity,
                "display_name": "Bob Osei",
                "phone": bob_phone,
                "id_type": Party.IdType.GHANA_CARD,
                "id_number": "GHA-000000002",
            },
        )

        agreement.refresh_from_db()

        if options["sealed"]:
            self._seal(agreement)

        agreement.refresh_from_db()
        status_label = agreement.status

        self.stdout.write("Seeded test data")
        self.stdout.write("=" * 40)
        self.stdout.write(f"Alice ({alice_phone})")
        self.stdout.write(f"  Token: {alice_token.key}")
        self.stdout.write(f"  Identity: {alice_identity.reference}")
        self.stdout.write("")
        self.stdout.write(f"Bob ({bob_phone})")
        self.stdout.write(f"  Token: {bob_token.key}")
        self.stdout.write(f"  Identity: {bob_identity.reference}")
        self.stdout.write("")
        self.stdout.write(f'Agreement: "{agreement.title}" ({status_label})')
        self.stdout.write(f"  GET /api/agreements/{agreement.pk}/")

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
