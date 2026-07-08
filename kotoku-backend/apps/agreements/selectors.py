from django.db.models import Q

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from common.phone_numbers import phone_lookup_values

_PARTICIPANT_VISIBLE_STATUSES = (
    AgreementStatus.PENDING_CONSENT,
    AgreementStatus.ACTIVE,
    AgreementStatus.SEALED,
    AgreementStatus.REOPEN_REQUESTED,
    AgreementStatus.CLOSED,
)


class AgreementSelector:
    @staticmethod
    def _visibility_q(*, account_id: int, account_phone: str | None):
        owner_q = Q(created_by_id=account_id)
        if not account_phone:
            return owner_q
        participant_q = Q(parties__phone__in=phone_lookup_values(account_phone)) & Q(
            status__in=_PARTICIPANT_VISIBLE_STATUSES
        )
        return owner_q | participant_q

    @staticmethod
    def list_agreements(*, account_id=None, account_phone=None, status=None):
        qs = (
            Agreement.objects.select_related("created_by")
            .prefetch_related("parties", "evidence_items")
            .order_by("-created_at")
        )
        if account_id is not None and account_phone is not None:
            qs = qs.filter(
                AgreementSelector._visibility_q(
                    account_id=account_id,
                    account_phone=account_phone,
                )
            ).distinct()
        elif account_id is not None:
            qs = qs.filter(created_by_id=account_id)
        if status is not None:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_agreement_detail(
        agreement_id: int, *, account_id: int = None, account_phone: str = None
    ) -> Agreement:
        qs = Agreement.objects.prefetch_related(
            "parties__identity",
            "evidence_items",
            "consent_records",
        ).select_related("created_by")
        if account_id is not None and account_phone is not None:
            qs = qs.filter(
                AgreementSelector._visibility_q(
                    account_id=account_id,
                    account_phone=account_phone,
                )
            )
        elif account_id is not None:
            qs = qs.filter(created_by_id=account_id)
        return qs.distinct().get(pk=agreement_id)

    @staticmethod
    def get_owned_agreement_detail(agreement_id: int, *, account_id: int) -> Agreement:
        return (
            Agreement.objects.prefetch_related(
                "parties__identity",
                "evidence_items",
                "consent_records",
            )
            .select_related("created_by")
            .get(pk=agreement_id, created_by_id=account_id)
        )

    @staticmethod
    def list_party_agreements(party_id: int):
        return (
            Agreement.objects.filter(parties__pk=party_id)
            .select_related("created_by")
            .order_by("-created_at")
            .distinct()
        )
