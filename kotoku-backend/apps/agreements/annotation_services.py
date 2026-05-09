import logging

from django.db.models import QuerySet

from apps.agreements.domain.policies import can_annotate
from apps.agreements.models import Agreement, Annotation
from apps.audit.services import AuditService
from apps.parties.models import Party
from common.exceptions import DomainError

logger = logging.getLogger(__name__)


class AnnotationService:
    @staticmethod
    def create(
        *,
        agreement_id: int,
        author_party_id: int,
        body: str,
    ) -> Annotation:
        """Add a post-seal annotation to a sealed (or reopen-requested) agreement."""
        agreement = Agreement.objects.get(pk=agreement_id)
        if not can_annotate(agreement):
            raise DomainError(
                "Annotations can only be added to sealed or reopen-requested agreements."
            )
        try:
            party = Party.objects.get(pk=author_party_id, agreement_id=agreement_id)
        except Party.DoesNotExist:
            raise DomainError("The author must be a party on this agreement.") from None

        annotation = Annotation.objects.create(
            agreement=agreement,
            author_party=party,
            body=body,
        )
        AuditService.record_event(
            event_type="agreement.annotation_added",
            entity_type="annotation",
            entity_id=str(annotation.pk),
            actor=str(party.pk),
            metadata={"agreement_id": agreement_id},
        )
        return annotation

    @staticmethod
    def delete(annotation_id: int, actor_party_id: int) -> None:
        """Delete an annotation. Only the author can delete their own annotation."""
        try:
            annotation = Annotation.objects.select_related("author_party").get(pk=annotation_id)
        except Annotation.DoesNotExist:
            raise DomainError("Annotation not found.")

        if annotation.author_party_id != actor_party_id:
            raise DomainError("You can only delete your own annotations.")

        annotation.delete()

    @staticmethod
    def update(*, annotation_id: int, actor_party_id: int, body: str) -> Annotation:
        """Update an annotation. Only the author can edit their own annotation."""
        try:
            annotation = Annotation.objects.select_related("author_party").get(pk=annotation_id)
        except Annotation.DoesNotExist:
            raise DomainError("Annotation not found.")

        if annotation.author_party_id != actor_party_id:
            raise DomainError("You can only edit your own annotations.")

        annotation.body = body
        annotation.save()

        AuditService.record_event(
            event_type="agreement.annotation_updated",
            entity_type="annotation",
            entity_id=str(annotation.pk),
            actor=str(actor_party_id),
            metadata={"agreement_id": annotation.agreement_id},
        )
        return annotation


class AnnotationSelector:
    @staticmethod
    def list_for_agreement(*, agreement_id: int) -> QuerySet:
        return (
            Annotation.objects.filter(agreement_id=agreement_id)
            .select_related("author_party")
            .order_by("created_at")
        )
