import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.audit.services import AuditService
from apps.parties.models import Party, PartyInvite
from common.exceptions import DomainError
from common.phone_numbers import normalize_phone_for_compare

logger = logging.getLogger("kotoku")

_INVITE_EXPIRY_DAYS = 7


class PartyInviteService:
    @staticmethod
    @transaction.atomic
    def create_and_send(*, party: Party) -> PartyInvite:
        """Replace any existing invite for this party slot, generate a new token, and send SMS.

        The token is embedded in a deep link sent to party.phone. Sending is async (Celery).
        Creating a new invite invalidates any previously sent link.
        """
        if not party.phone:
            raise DomainError("Cannot invite a party with no phone number.")

        deep_link_base = (
            getattr(settings, "PARTY_INVITE_DEEP_LINK_BASE", "kotoku://invite/").rstrip("/") + "/"
        )

        PartyInvite.objects.filter(party=party).delete()
        invite = PartyInvite.objects.create(
            party=party,
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=_INVITE_EXPIRY_DAYS),
        )

        link = f"{deep_link_base}{invite.token}"
        agreement = party.agreement
        body = (
            f'You have been invited to verify your identity for "{agreement.title}" on Kotoku. '
            f"Open the Kotoku app and tap: {link}"
        )

        def _send() -> None:
            from apps.notifications.tasks import send_sms_message

            try:
                send_sms_message.delay(to=party.phone, body=body)
                PartyInvite.objects.filter(pk=invite.pk).update(sent_at=timezone.now())
                logger.info(
                    "[INVITE] sms_queued party_id=%s role=%s agreement_id=%s",
                    party.pk,
                    party.role,
                    agreement.pk,
                )
            except Exception:
                logger.exception(
                    "[INVITE] sms_queue_failed party_id=%s role=%s", party.pk, party.role
                )

        transaction.on_commit(_send)

        AuditService.record_event(
            event_type="party.invite_created",
            entity_type="party",
            entity_id=str(party.pk),
            actor=str(agreement.created_by_id),
            metadata={"role": party.role, "agreement_id": agreement.pk},
        )

        return invite

    @staticmethod
    def get_detail(*, token: str) -> dict:
        """Return invite metadata for an unauthenticated deep-link preview.

        Only raises for expired invites. A claimed-but-incomplete invite still returns
        metadata so Party B can re-enter the flow after abandoning. The token itself
        (UUID) is the access gate for this unauthenticated endpoint.
        """
        try:
            invite = (
                PartyInvite.objects.select_related("party__agreement")
                .get(token=token)
            )
        except PartyInvite.DoesNotExist:
            raise DomainError("This invite link is not valid.")

        if invite.is_expired():
            raise DomainError(
                "This invite link has expired. Ask the agreement creator to resend.",
                code="invite_expired",
            )

        party = invite.party
        agreement = party.agreement
        return {
            "agreement_id": agreement.pk,
            "agreement_title": agreement.title,
            "role": party.role,
            "party_name": party.display_name,
            "expires_at": invite.expires_at.isoformat(),
        }

    @staticmethod
    @transaction.atomic
    def claim(*, token: str, account) -> dict:
        """Mark invite as accepted after verifying authenticated account phone matches party phone.

        Fails closed: if phone does not match, raises DomainError — no fallback.
        """
        try:
            invite = (
                PartyInvite.objects.select_related("party__agreement")
                .select_for_update()
                .get(token=token)
            )
        except PartyInvite.DoesNotExist:
            raise DomainError("This invite link is not valid.")

        if invite.is_expired():
            raise DomainError(
                "This invite link has expired. Ask the agreement creator to resend.",
                code="invite_expired",
            )

        party = invite.party

        if invite.is_claimed():
            # Idempotent re-entry: same phone may re-claim after abandoning the flow.
            # A different phone attempting to claim a used invite gets phone_mismatch below.
            if normalize_phone_for_compare(account.phone) == normalize_phone_for_compare(party.phone):
                return {"agreement_id": party.agreement_id, "role": party.role}

        if normalize_phone_for_compare(account.phone) != normalize_phone_for_compare(party.phone):
            raise DomainError(
                "This invite was sent to a different phone number. "
                "Log in with the phone number that received the invitation.",
                code="phone_mismatch",
            )

        invite.accepted_at = timezone.now()
        invite.save(update_fields=["accepted_at", "updated_at"])

        AuditService.record_event(
            event_type="party.invite_claimed",
            entity_type="party",
            entity_id=str(party.pk),
            actor=str(account.pk),
            metadata={"role": party.role, "agreement_id": party.agreement_id},
        )

        logger.info(
            "[INVITE] claimed party_id=%s role=%s agreement_id=%s account=%s",
            party.pk,
            party.role,
            party.agreement_id,
            account.pk,
        )

        return {"agreement_id": party.agreement_id, "role": party.role}

    @staticmethod
    def get_agreement_for_claimed_invite(agreement_id: int, *, account_phone: str):
        """Return the Agreement if account_phone has a claimed invite for a party in it.

        Bypasses _PARTICIPANT_VISIBLE_STATUSES so invited participants can access DRAFT
        agreements. Fails closed: accepted_at must be set, meaning the claim step already
        verified the phone match.
        """
        from apps.agreements.models import Agreement
        from common.phone_numbers import phone_lookup_values

        has_invite = PartyInvite.objects.filter(
            party__agreement_id=agreement_id,
            party__phone__in=phone_lookup_values(account_phone),
            accepted_at__isnull=False,
        ).exists()

        if not has_invite:
            raise Agreement.DoesNotExist

        return (
            Agreement.objects.prefetch_related(
                "parties__identity",
                "evidence_items",
                "consent_records",
            )
            .select_related("created_by")
            .get(pk=agreement_id)
        )
