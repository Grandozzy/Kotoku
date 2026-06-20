from apps.consent.models import ConsentRecord
from apps.parties.models import Party


class ConsentSelector:
    @staticmethod
    def list_consent_for_agreement(
        *,
        agreement_id: int,
        purpose: str = ConsentRecord.Purpose.CONSENT,
    ):
        return ConsentRecord.objects.filter(
            agreement_id=agreement_id,
            purpose=purpose,
        ).select_related("party", "agreement")

    @staticmethod
    def pending_consent_count(
        *,
        agreement_id: int,
        purpose: str = ConsentRecord.Purpose.CONSENT,
    ) -> int:
        return ConsentRecord.objects.filter(
            agreement_id=agreement_id,
            purpose=purpose,
            granted=False,
        ).count()

    @staticmethod
    def all_parties_consented(
        *,
        agreement_id: int,
        purpose: str = ConsentRecord.Purpose.CONSENT,
    ) -> bool:
        party_count = Party.objects.filter(agreement_id=agreement_id).count()
        if party_count == 0:
            return False

        latest_records = {}
        records = (
            ConsentRecord.objects.filter(
                agreement_id=agreement_id,
                purpose=purpose,
            )
            .order_by("party_id", "-created_at", "-id")
            .values("party_id", "granted")
        )
        for record in records:
            latest_records.setdefault(record["party_id"], record["granted"])

        return (
            len(latest_records) == party_count
            and all(latest_records.values())
        )
