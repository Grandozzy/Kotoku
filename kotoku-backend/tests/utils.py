"""Shared test utilities."""

from apps.evidence.models import EvidenceItem
from apps.identity.models import PartyIdentityVerification
from apps.parties.models import Party


def stamp_all_parties_verified(agreement):
    """Create the minimum evidence + verification records so validate_agreement passes.

    Covers:
    - Ghana Card front/back/selfie evidence + PartyIdentityVerification(VERIFIED)
      for every non-witness party.
    - Scenario minimum evidence (3 vehicle photos for used_vehicle_sale, 2
      property photos for room_rental).
    """
    for party in Party.objects.filter(agreement=agreement):
        if party.role == "witness":
            continue
        role = party.role
        for side in ("front", "back"):
            EvidenceItem.objects.get_or_create(
                agreement=agreement,
                evidence_type=f"{role}_ghana_card_{side}",
                defaults={
                    "file_type": EvidenceItem.FileType.PHOTO,
                    "mime_type": "image/jpeg",
                    "upload_status": EvidenceItem.UploadStatus.CONFIRMED,
                    "uploaded_by": party,
                },
            )
        EvidenceItem.objects.get_or_create(
            agreement=agreement,
            evidence_type=f"{role}_selfie",
            defaults={
                "file_type": EvidenceItem.FileType.PHOTO,
                "mime_type": "image/jpeg",
                "upload_status": EvidenceItem.UploadStatus.CONFIRMED,
                "uploaded_by": party,
            },
        )
        PartyIdentityVerification.objects.update_or_create(
            party=party,
            defaults={
                "status": PartyIdentityVerification.Status.VERIFIED,
                "entered_pin": party.id_number or "",
                "entered_full_name": party.display_name,
                "ocr_pin": party.id_number or "",
                "ocr_full_name": party.display_name.upper(),
                "detail": "Verified in test.",
            },
        )

    scenario = getattr(agreement, "scenario_template", None)
    if scenario == "used_vehicle_sale":
        existing = EvidenceItem.objects.filter(
            agreement=agreement,
            evidence_type__startswith="vehicle_photo",
            upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        ).count()
        for i in range(max(0, 3 - existing)):
            EvidenceItem.objects.create(
                agreement=agreement,
                file_type=EvidenceItem.FileType.PHOTO,
                evidence_type=f"vehicle_photo_stamp_{i}",
                mime_type="image/jpeg",
                upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            )
    elif scenario == "room_rental":
        existing = EvidenceItem.objects.filter(
            agreement=agreement,
            evidence_type__startswith="property_photo",
            upload_status=EvidenceItem.UploadStatus.CONFIRMED,
        ).count()
        for i in range(max(0, 2 - existing)):
            EvidenceItem.objects.create(
                agreement=agreement,
                file_type=EvidenceItem.FileType.PHOTO,
                evidence_type=f"property_photo_stamp_{i}",
                mime_type="image/jpeg",
                upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            )
