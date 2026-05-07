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
    help = "Seed repeatable test data (users, accounts, identities, agreements)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sealed",
            action="store_true",
            help="Run the full consent + seal flow so sealed agreements end as SEALED",
        )

    def handle(self, *args, **options):
        from django.core.management import call_command

        call_command("seed_templates")

        alice_phone = "+233500000001"
        bob_phone = "+233500000002"
        carlos_phone = "+233500000003"
        diana_phone = "+233500000004"

        alice_user, _ = User.objects.get_or_create(phone=alice_phone)
        bob_user, _ = User.objects.get_or_create(phone=bob_phone)
        carlos_user, _ = User.objects.get_or_create(phone=carlos_phone)
        diana_user, _ = User.objects.get_or_create(phone=diana_phone)

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
        carlos_account, _ = Account.objects.get_or_create(
            user=carlos_user,
            defaults={
                "email": "carlos@test.kotoku",
                "phone": carlos_phone,
                "full_name": "Carlos Boateng",
            },
        )
        diana_account, _ = Account.objects.get_or_create(
            user=diana_user,
            defaults={
                "email": "diana@test.kotoku",
                "phone": diana_phone,
                "full_name": "Diana Asante",
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
        carlos_identity, _ = IdentityRecord.objects.get_or_create(
            reference="GHA-000000003",
            defaults={
                "account": carlos_account,
                "verification_type": IdentityRecord.VerificationType.GHANA_CARD,
                "verified_at": carlos_account.created_at,
            },
        )
        diana_identity, _ = IdentityRecord.objects.get_or_create(
            reference="GHA-000000004",
            defaults={
                "account": diana_account,
                "verification_type": IdentityRecord.VerificationType.GHANA_CARD,
                "verified_at": diana_account.created_at,
            },
        )

        alice_token, _ = Token.objects.get_or_create(user=alice_user)
        bob_token, _ = Token.objects.get_or_create(user=bob_user)
        carlos_token, _ = Token.objects.get_or_create(user=carlos_user)
        diana_token, _ = Token.objects.get_or_create(user=diana_user)

        agreements = []

        agreement_1, _ = Agreement.objects.get_or_create(
            title="Cash Sale - Toyota Corolla 2020",
            defaults={
                "description": (
                    "Cash sale of a 2020 Toyota Corolla between Alice (buyer) and Bob (seller). "
                    "Vehicle VIN: JTDBR32E760062789. Sale price: GHS 85,000. "
                    "Payment via mobile money on or before 15 June 2026."
                ),
                "scenario_template": "used_vehicle_sale",
                "field_data": {
                    "vehicle_type": "car",
                    "make": "Toyota",
                    "model": "Corolla",
                    "year_of_manufacture": 2020,
                    "registration_number": "GR-1234-20",
                    "vin_or_chassis": "JTDBR32E760062789",
                    "current_mileage": 45200,
                    "colour": "Silver",
                    "seller_is_owner_confirmed": True,
                    "overall_condition": "good",
                    "total_price_amount": 85000,
                    "payment_type": "mobile_money",
                    "payment_timing": "on_the_spot",
                    "agreement_date": "2026-06-01",
                },
                "created_by": alice_account,
            },
        )
        Party.objects.get_or_create(
            agreement=agreement_1,
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
            agreement=agreement_1,
            role=Party.Role.SELLER,
            defaults={
                "identity": bob_identity,
                "display_name": "Bob Osei",
                "phone": bob_phone,
                "id_type": Party.IdType.GHANA_CARD,
                "id_number": "GHA-000000002",
            },
        )
        agreements.append(("Toyota Corolla Sale", agreement_1))

        agreement_2, _ = Agreement.objects.get_or_create(
            title="Rental - 2BR Apartment at East Legon",
            defaults={
                "description": (
                    "Rental agreement for a 2-bedroom apartment at 14 Oxford Street, East Legon, Accra. "
                    "Landlord: Carlos Boateng. Tenant: Alice Mensah. "
                    "Monthly rent: GHS 3,500. Security deposit: GHS 7,000. "
                    "Lease period: 1 July 2026 to 30 June 2027."
                ),
                "scenario_template": "rental_agreement",
                "field_data": {
                    "property_type": "apartment",
                    "property_address": "14 Oxford Street, East Legon, Accra",
                    "property_description": "2-bedroom apartment, en-suite master bedroom, shared bath, fitted kitchen",
                    "rent_amount": 3500,
                    "rent_period": "per_month",
                    "deposit_amount": 7000,
                    "tenancy_start_date": "2026-07-01",
                    "tenancy_end_date": "2027-06-30",
                    "deposit_paid": True,
                    "deposit_paid_amount": 7000,
                },
                "created_by": carlos_account,
            },
        )
        Party.objects.get_or_create(
            agreement=agreement_2,
            role=Party.Role.LANDLORD,
            defaults={
                "identity": carlos_identity,
                "display_name": "Carlos Boateng",
                "phone": carlos_phone,
                "id_type": Party.IdType.GHANA_CARD,
                "id_number": "GHA-000000003",
            },
        )
        Party.objects.get_or_create(
            agreement=agreement_2,
            role=Party.Role.TENANT,
            defaults={
                "identity": alice_identity,
                "display_name": "Alice Mensah",
                "phone": alice_phone,
                "id_type": Party.IdType.GHANA_CARD,
                "id_number": "GHA-000000001",
            },
        )
        agreements.append(("East Legon Rental", agreement_2))

        agreement_3, _ = Agreement.objects.get_or_create(
            title="Cash Sale - Honda Civic 2019",
            defaults={
                "description": (
                    "Cash sale of a 2019 Honda Civic between Diana (buyer) and Bob (seller). "
                    "Vehicle VIN: 2HGFC2F59KH558321. Sale price: GHS 72,000. "
                    "Payment via bank transfer within 7 days of sealing."
                ),
                "scenario_template": "used_vehicle_sale",
                "field_data": {
                    "vehicle_type": "car",
                    "make": "Honda",
                    "model": "Civic",
                    "year_of_manufacture": 2019,
                    "registration_number": "GR-5678-19",
                    "vin_or_chassis": "2HGFC2F59KH558321",
                    "current_mileage": 62100,
                    "colour": "Black",
                    "seller_is_owner_confirmed": True,
                    "overall_condition": "good",
                    "total_price_amount": 72000,
                    "payment_type": "bank_transfer",
                    "payment_timing": "on_the_spot",
                    "agreement_date": "2026-06-15",
                },
                "created_by": diana_account,
            },
        )
        Party.objects.get_or_create(
            agreement=agreement_3,
            role=Party.Role.BUYER,
            defaults={
                "identity": diana_identity,
                "display_name": "Diana Asante",
                "phone": diana_phone,
                "id_type": Party.IdType.GHANA_CARD,
                "id_number": "GHA-000000004",
            },
        )
        Party.objects.get_or_create(
            agreement=agreement_3,
            role=Party.Role.SELLER,
            defaults={
                "identity": bob_identity,
                "display_name": "Bob Osei",
                "phone": bob_phone,
                "id_type": Party.IdType.GHANA_CARD,
                "id_number": "GHA-000000002",
            },
        )
        agreements.append(("Honda Civic Sale", agreement_3))

        agreement_4, _ = Agreement.objects.get_or_create(
            title="Used Vehicle Sale - Nissan Patrol 2021",
            defaults={
                "description": (
                    "Sale of a 2021 Nissan Patrol between Carlos (buyer) and Diana (seller). "
                    "Vehicle VIN: JN1TANT61Z0012345. Sale price: GHS 150,000. "
                    "Payment via bank transfer. Odometer: 42,300 km."
                ),
                "scenario_template": "used_vehicle_sale",
                "field_data": {
                    "vehicle_type": "car",
                    "make": "Nissan",
                    "model": "Patrol",
                    "year_of_manufacture": 2021,
                    "registration_number": "GR-9012-21",
                    "vin_or_chassis": "JN1TANT61Z0012345",
                    "current_mileage": 42300,
                    "colour": "White",
                    "seller_is_owner_confirmed": True,
                    "overall_condition": "excellent",
                    "total_price_amount": 150000,
                    "payment_type": "cash",
                    "payment_timing": "on_the_spot",
                    "agreement_date": "2026-06-10",
                },
                "created_by": carlos_account,
            },
        )
        Party.objects.get_or_create(
            agreement=agreement_4,
            role=Party.Role.BUYER,
            defaults={
                "identity": carlos_identity,
                "display_name": "Carlos Boateng",
                "phone": carlos_phone,
                "id_type": Party.IdType.GHANA_CARD,
                "id_number": "GHA-000000003",
            },
        )
        Party.objects.get_or_create(
            agreement=agreement_4,
            role=Party.Role.SELLER,
            defaults={
                "identity": diana_identity,
                "display_name": "Diana Asante",
                "phone": diana_phone,
                "id_type": Party.IdType.GHANA_CARD,
                "id_number": "GHA-000000004",
            },
        )
        agreements.append(("Nissan Patrol Sale", agreement_4))

        for label, agreement in agreements:
            agreement.refresh_from_db()

        if options["sealed"]:
            self._seal(agreement_1, label="Toyota Corolla Sale")
            self._seal(agreement_2, label="East Legon Rental")
            agreement_3.refresh_from_db()
            if agreement_3.status == Agreement.Status.DRAFT:
                AgreementService.request_consent(agreement_id=agreement_3.pk)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Seeded test data"))
        self.stdout.write("=" * 50)

        self.stdout.write("")
        self.stdout.write(f"Alice ({alice_phone})")
        self.stdout.write(f"  Token: {alice_token.key}")
        self.stdout.write(f"  Identity: {alice_identity.reference}")
        self.stdout.write("")
        self.stdout.write(f"Bob ({bob_phone})")
        self.stdout.write(f"  Token: {bob_token.key}")
        self.stdout.write(f"  Identity: {bob_identity.reference}")
        self.stdout.write("")
        self.stdout.write(f"Carlos ({carlos_phone})")
        self.stdout.write(f"  Token: {carlos_token.key}")
        self.stdout.write(f"  Identity: {carlos_identity.reference}")
        self.stdout.write("")
        self.stdout.write(f"Diana ({diana_phone})")
        self.stdout.write(f"  Token: {diana_token.key}")
        self.stdout.write(f"  Identity: {diana_identity.reference}")

        self.stdout.write("")
        self.stdout.write("Agreements:")
        for label, agreement in agreements:
            agreement.refresh_from_db()
            self.stdout.write(f"  [{agreement.status}] {agreement.title}")
            self.stdout.write(f"    GET /api/agreements/{agreement.pk}/")

    def _seal(self, agreement, label=""):
        from unittest.mock import patch

        import apps.consent.services as consent_module

        agreement.refresh_from_db()
        if agreement.status != Agreement.Status.DRAFT:
            self.stdout.write(f"  {label}: already {agreement.status}, skipping seal.")
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

        evidence_items = self._evidence_for_agreement(agreement)
        for ev in evidence_items:
            png_bytes = self._make_png()
            file_hash = hashlib.sha256(png_bytes).hexdigest()
            file_key = f"test-data/{ev['file_name']}"
            try:
                storage_url = S3StorageClient().upload(
                    file_key, png_bytes, content_type="image/png"
                )
            except Exception:
                storage_url = f"https://test-bucket.example.com/{file_key}"
            EvidenceItem.objects.get_or_create(
                agreement=agreement,
                evidence_type=ev["evidence_type"],
                defaults={
                    "file_type": ev["file_type"],
                    "mime_type": "image/png",
                    "size_bytes": len(png_bytes),
                    "file_key": file_key,
                    "file_hash": file_hash,
                    "storage_url": storage_url,
                    "original_name": ev["file_name"],
                    "upload_status": EvidenceItem.UploadStatus.CONFIRMED,
                },
            )

        AgreementService.seal_agreement(agreement_id=agreement.pk)

        from apps.vault.services import VaultService

        VaultService.create_for_agreement(agreement_id=agreement.pk)
        self.stdout.write(f"  {label}: sealed ✓")

    def _evidence_for_agreement(self, agreement):
        template = agreement.scenario_template
        if template == "used_vehicle_sale":
            return [
                {
                    "evidence_type": "vehicle_photo_front",
                    "file_type": EvidenceItem.FileType.PHOTO,
                    "file_name": "vehicle_front.png",
                },
                {
                    "evidence_type": "vehicle_photo_rear",
                    "file_type": EvidenceItem.FileType.PHOTO,
                    "file_name": "vehicle_rear.png",
                },
                {
                    "evidence_type": "vehicle_odometer",
                    "file_type": EvidenceItem.FileType.PHOTO,
                    "file_name": "odometer_reading.png",
                },
                {
                    "evidence_type": "seller_id_photo",
                    "file_type": EvidenceItem.FileType.PHOTO,
                    "file_name": "seller_id.png",
                },
            ]
        elif template == "rental_agreement":
            return [
                {
                    "evidence_type": "property_front",
                    "file_type": EvidenceItem.FileType.PHOTO,
                    "file_name": "property_front.png",
                },
                {
                    "evidence_type": "property_interior",
                    "file_type": EvidenceItem.FileType.PHOTO,
                    "file_name": "property_interior.png",
                },
                {
                    "evidence_type": "landlord_id_photo",
                    "file_type": EvidenceItem.FileType.PHOTO,
                    "file_name": "landlord_id.png",
                },
            ]
        return [
            {
                "evidence_type": "general_evidence",
                "file_type": EvidenceItem.FileType.PHOTO,
                "file_name": "evidence.png",
            },
        ]

    @staticmethod
    def _make_png():
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
