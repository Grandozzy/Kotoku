from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.agreements.models import Agreement
from apps.audit.models import AuditLog
from apps.identity.models import IdentityRecord, PartyIdentityVerification
from apps.identity.selectors import IdentitySelector
from apps.identity.services import (
    IdentityService,
    _assert_liveness_attempt_allowed,
    _classify_liveness_result,
    _record_liveness_failure,
)
from apps.identity.tasks import cleanup_expired_liveness_references
from apps.parties.models import Party
from common.exceptions import DomainError


def _account(phone: str, email: str) -> Account:
    user = User.objects.create_user(phone=phone)
    return Account.objects.create(user=user, phone=phone, email=email)


def _party(account: Account) -> Party:
    agreement = Agreement.objects.create(title="Identity review", created_by=account)
    return Party.objects.create(
        agreement=agreement,
        role=Party.Role.BUYER,
        display_name="Ama Mensah",
        phone=account.phone,
        id_type=Party.IdType.GHANA_CARD,
        id_number="GHA-123456789-0",
    )


@pytest.mark.django_db
class TestIdentityService:
    def test_create_identity_record(self):
        account = _account("+233700000001", "id1@test.com")
        identity = IdentityService.create_identity_record(
            account=account,
            reference="GHA-1234",
            verification_type=IdentityRecord.VerificationType.GHANA_CARD,
        )
        assert identity.account == account
        assert identity.reference == "GHA-1234"
        assert identity.verified_at is None

    def test_mark_verified_sets_timestamp(self):
        account = _account("+233700000002", "id2@test.com")
        identity = IdentityService.create_identity_record(
            account=account,
            reference="PHONE-1234",
            verification_type=IdentityRecord.VerificationType.PHONE,
        )
        verified = IdentityService.mark_verified(identity_record=identity)
        assert verified.verified_at is not None


@pytest.mark.django_db
class TestIdentitySelector:
    def test_list_for_account_returns_only_matching_records(self):
        account = _account("+233700000003", "id3@test.com")
        other = _account("+233700000004", "id4@test.com")
        IdentityService.create_identity_record(
            account=account,
            reference="GHA-1",
            verification_type=IdentityRecord.VerificationType.GHANA_CARD,
        )
        IdentityService.create_identity_record(
            account=other,
            reference="GHA-2",
            verification_type=IdentityRecord.VerificationType.GHANA_CARD,
        )
        result = list(IdentitySelector.list_for_account(account.pk))
        assert len(result) == 1
        assert result[0].account_id == account.pk

    def test_get_for_account_scopes_to_owner(self):
        account = _account("+233700000005", "id5@test.com")
        identity = IdentityService.create_identity_record(
            account=account,
            reference="GHA-5",
            verification_type=IdentityRecord.VerificationType.GHANA_CARD,
        )
        result = IdentitySelector.get_for_account(
            identity_id=identity.pk,
            account_id=account.pk,
        )
        assert result.pk == identity.pk

    def test_get_verified_for_reference_returns_verified_record(self):
        account = _account("+233700000006", "id6@test.com")
        identity = IdentityService.create_identity_record(
            account=account,
            reference="GHA-6",
            verification_type=IdentityRecord.VerificationType.GHANA_CARD,
        )
        IdentityService.mark_verified(identity_record=identity)
        result = IdentitySelector.get_verified_for_reference("GHA-6")
        assert result.pk == identity.pk


class TestLivenessPolicy:
    @override_settings(
        AWS_REKOGNITION_LIVENESS_THRESHOLD=80.0,
        AWS_REKOGNITION_LIVENESS_REVIEW_THRESHOLD=70.0,
    )
    def test_classifies_scores_at_configured_boundaries(self):
        assert _classify_liveness_result(aws_status="SUCCEEDED", confidence=80.0) == "passed"
        assert (
            _classify_liveness_result(aws_status="SUCCEEDED", confidence=79.99) == "manual_review"
        )
        assert _classify_liveness_result(aws_status="SUCCEEDED", confidence=69.99) == "failed"

    @override_settings(
        AWS_REKOGNITION_LIVENESS_THRESHOLD=80.0,
        AWS_REKOGNITION_LIVENESS_REVIEW_THRESHOLD=70.0,
    )
    def test_preserves_non_terminal_and_expired_aws_states(self):
        assert _classify_liveness_result(aws_status="IN_PROGRESS", confidence=0) == "processing"
        assert _classify_liveness_result(aws_status="EXPIRED", confidence=0) == "expired"
        assert _classify_liveness_result(aws_status="FAILED", confidence=99) == "failed"

    @override_settings(
        AWS_REKOGNITION_LIVENESS_THRESHOLD=70.0,
        AWS_REKOGNITION_LIVENESS_REVIEW_THRESHOLD=80.0,
    )
    def test_rejects_inverted_threshold_configuration(self):
        with pytest.raises(RuntimeError, match="Invalid Rekognition"):
            _classify_liveness_result(aws_status="SUCCEEDED", confidence=90)

    @override_settings(
        AWS_REKOGNITION_LIVENESS_MAX_FAILURES=2,
        AWS_REKOGNITION_LIVENESS_FAILURE_WINDOW_SECONDS=180,
        AWS_REKOGNITION_LIVENESS_COOLDOWN_SECONDS=1800,
    )
    def test_repeated_session_result_is_idempotent_and_failures_trigger_cooldown(self):
        cache.clear()
        _record_liveness_failure(party_id=81, session_id="session-1")
        _record_liveness_failure(party_id=81, session_id="session-1")
        _assert_liveness_attempt_allowed(party_id=81)

        _record_liveness_failure(party_id=81, session_id="session-2")
        with pytest.raises(DomainError, match="Too many unsuccessful"):
            _assert_liveness_attempt_allowed(party_id=81)
        cache.clear()

    @override_settings(
        AWS_REKOGNITION_LIVENESS_THRESHOLD=80.0,
        AWS_REKOGNITION_LIVENESS_REVIEW_THRESHOLD=70.0,
        AWS_REKOGNITION_LIVENESS_MAX_FAILURES=5,
        AWS_REKOGNITION_LIVENESS_FAILURE_WINDOW_SECONDS=180,
        AWS_REKOGNITION_LIVENESS_COOLDOWN_SECONDS=1800,
    )
    @patch("apps.identity.services.RekognitionClient")
    @patch("apps.identity.services.IdentityService.ensure_party_verification")
    @pytest.mark.django_db
    def test_result_contract_does_not_expose_biometric_score(
        self,
        ensure_verification,
        rekognition_client,
    ):
        cache.clear()
        verification = MagicMock(
            liveness_session_id="session-private-score",
            status="pending",
        )
        ensure_verification.return_value = verification
        rekognition_client.return_value.get_face_liveness_session_results.return_value = {
            "status": "SUCCEEDED",
            "confidence": 65.5,
            "reference_image_bytes": b"",
        }
        party = MagicMock(pk=91, role="buyer")

        with patch.object(
            PartyIdentityVerification.objects,
            "select_for_update",
        ) as select_for_update:
            select_for_update.return_value.filter.return_value.first.return_value = None
            result = IdentityService.process_liveness_result(party=party)

        assert result == {
            "status": "failed",
            "detail": (
                "Face check did not pass. Remove face coverings and retry in clear, even lighting."
            ),
        }
        assert "confidence" not in result
        cache.clear()


@pytest.mark.django_db
class TestManualIdentityReview:
    def test_face_match_review_can_be_approved_and_is_audited(self):
        account = _account("+233700000020", "review@test.com")
        verification = PartyIdentityVerification.objects.create(
            party=_party(account),
            status=PartyIdentityVerification.Status.MANUAL_REVIEW_REQUIRED,
            failure_codes=["face_match_manual_review"],
            front_evidence_id=10,
            back_evidence_id=11,
        )

        decision = IdentityService.resolve_manual_review(
            verification_id=verification.pk,
            approved=True,
            actor="admin:7",
        )

        verification.refresh_from_db()
        assert decision == "approved_identity"
        assert verification.status == PartyIdentityVerification.Status.VERIFIED
        assert AuditLog.objects.filter(
            event_type="identity.manual_review_resolved",
            actor="admin:7",
        ).exists()

    def test_liveness_review_requires_retained_reference(self):
        account = _account("+233700000021", "expired-review@test.com")
        verification = PartyIdentityVerification.objects.create(
            party=_party(account),
            status=PartyIdentityVerification.Status.MANUAL_REVIEW_REQUIRED,
            failure_codes=["liveness_manual_review"],
        )

        with pytest.raises(DomainError, match="reference has expired"):
            IdentityService.resolve_manual_review(
                verification_id=verification.pk,
                approved=True,
                actor="admin:7",
            )


@pytest.mark.django_db
def test_cleanup_expired_liveness_reference():
    account = _account("+233700000022", "cleanup@test.com")
    verification = PartyIdentityVerification.objects.create(
        party=_party(account),
        liveness_reference_s3_key="identity/reference.jpg",
        liveness_reference_delete_after=timezone.now() - timedelta(minutes=1),
    )

    with patch("infrastructure.storage.s3.S3StorageClient.delete_object") as delete_object:
        result = cleanup_expired_liveness_references()

    verification.refresh_from_db()
    assert result == {"deleted": 1}
    delete_object.assert_called_once_with("identity/reference.jpg")
    assert verification.liveness_reference_s3_key == ""
    assert verification.liveness_reference_delete_after is None
