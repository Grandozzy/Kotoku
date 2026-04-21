from apps.consent.models import ConsentRecord


class ConsentSelector:
    @staticmethod
    def list_consent_for_agreement(*, agreement_id: int):
        return ConsentRecord.objects.filter(
            agreement_id=agreement_id
        ).select_related("party", "agreement")

    @staticmethod
    def pending_consent_count(*, agreement_id: int) -> int:
        return ConsentRecord.objects.filter(
            agreement_id=agreement_id, granted=False
        ).count()

    @staticmethod
    def all_parties_consented(*, agreement_id: int) -> bool:
        return not ConsentRecord.objects.filter(
            agreement_id=agreement_id, granted=False
        ).exists()
