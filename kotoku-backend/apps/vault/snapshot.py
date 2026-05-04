import hashlib
import json

from apps.agreements.models import Agreement


def build_export_snapshot(agreement_id: int) -> dict:
    agreement = Agreement.objects.prefetch_related(
        "parties__identity__account", "evidence_items", "consent_records"
    ).get(pk=agreement_id)

    parties = [
        {
            "display_name": p.display_name,
            "role": p.role,
            "phone": p.identity.account.phone if hasattr(p, "identity") else "",
        }
        for p in agreement.parties.all()
    ]

    evidence_items = [
        {
            "file_type": e.file_type,
            "original_name": e.original_name,
            "file_hash": e.file_hash,
        }
        for e in agreement.evidence_items.all()
    ]

    consent_records = [
        {
            "actor": cr.party.display_name,
            "consented_at": cr.granted_at.isoformat() if cr.granted_at else None,
        }
        for cr in agreement.consent_records.all()
    ]

    snapshot = {
        "agreement_id": agreement.pk,
        "title": agreement.title,
        "scenario_template": agreement.scenario_template,
        "sealed_at": agreement.sealed_at.isoformat() if agreement.sealed_at else None,
        "parties": parties,
        "evidence_items": evidence_items,
        "consent_records": consent_records,
    }

    raw = json.dumps(snapshot, sort_keys=True, default=str)
    snapshot["snapshot_hash"] = hashlib.sha256(raw.encode()).hexdigest()

    return snapshot
