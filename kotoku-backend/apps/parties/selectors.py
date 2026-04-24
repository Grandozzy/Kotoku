from apps.parties.models import Party


class PartySelector:
    @staticmethod
    def list_parties(*, agreement_id: int) -> list[Party]:
        return list(
            Party.objects.filter(agreement_id=agreement_id).order_by("created_at")
        )
