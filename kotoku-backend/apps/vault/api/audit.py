from rest_framework import serializers


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
