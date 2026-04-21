from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.domain.policies import can_reopen, can_request_consent, can_seal
from apps.agreements.models import Agreement
from apps.identity.models import IdentityRecord
from apps.parties.models import Party

_seq = 0


def _make_account(email):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=f"+233{_seq:09d}")
    return Account.objects.create(user=user, email=email, phone=user.phone)


def _make_agreement(status=AgreementStatus.DRAFT, **kwargs):
    defaults = {
        "title": "Test Agreement",
        "created_by": _make_account("owner@test.com"),
    }
    defaults.update(kwargs)
    return Agreement.objects.create(status=status, **defaults)


def _make_party(agreement, role=Party.Role.BUYER):
    identity = IdentityRecord.objects.create(
        account=agreement.created_by,
        reference=f"ref-{agreement.pk}-{role}",
        verification_type="ghana_card",
    )
    return Party.objects.create(
        agreement=agreement,
        identity=identity,
        role=role,
        display_name=f"Test {role}",
    )


class TestCanRequestConsent:
    def test_returns_true_when_draft_with_two_parties(self, db):
        agreement = _make_agreement()
        _make_party(agreement, Party.Role.BUYER)
        _make_party(agreement, Party.Role.SELLER)
        assert can_request_consent(agreement) is True

    def test_returns_false_when_draft_with_one_party(self, db):
        agreement = _make_agreement()
        _make_party(agreement, Party.Role.BUYER)
        assert can_request_consent(agreement) is False

    def test_returns_false_when_draft_with_no_parties(self, db):
        agreement = _make_agreement()
        assert can_request_consent(agreement) is False

    def test_returns_false_when_not_draft(self, db):
        account = _make_account("owner2@test.com")
        agreement = _make_agreement(
            status=AgreementStatus.PENDING_CONSENT, created_by=account
        )
        _make_party(agreement, Party.Role.BUYER)
        _make_party(agreement, Party.Role.SELLER)
        assert can_request_consent(agreement) is False


class TestCanSeal:
    def test_returns_true_when_active_with_evidence(self, db):
        agreement = _make_agreement(status=AgreementStatus.ACTIVE)
        party = _make_party(agreement)
        from apps.evidence.models import EvidenceItem

        EvidenceItem.objects.create(
            agreement=agreement,
            uploaded_by=party,
            file_type=EvidenceItem.FileType.PHOTO,
            file_hash="abc123",
        )
        assert can_seal(agreement) is True

    def test_returns_false_when_active_without_evidence(self, db):
        agreement = _make_agreement(status=AgreementStatus.ACTIVE)
        assert can_seal(agreement) is False

    def test_returns_false_when_not_active(self, db):
        agreement = _make_agreement(status=AgreementStatus.DRAFT)
        assert can_seal(agreement) is False


class TestCanReopen:
    def test_returns_true_when_sealed_within_24h(self, db):
        agreement = _make_agreement(status=AgreementStatus.SEALED)
        agreement.sealed_at = timezone.now() - timedelta(hours=23, minutes=59)
        agreement.save(update_fields=["sealed_at"])
        assert can_reopen(agreement) is True

    def test_returns_false_when_sealed_over_24h(self, db):
        agreement = _make_agreement(status=AgreementStatus.SEALED)
        agreement.sealed_at = timezone.now() - timedelta(hours=24, minutes=1)
        agreement.save(update_fields=["sealed_at"])
        assert can_reopen(agreement) is False

    def test_returns_false_when_not_sealed(self, db):
        agreement = _make_agreement(status=AgreementStatus.ACTIVE)
        assert can_reopen(agreement) is False

    def test_returns_false_when_sealed_at_is_null(self, db):
        agreement = _make_agreement(status=AgreementStatus.SEALED)
        agreement.sealed_at = None
        agreement.save(update_fields=["sealed_at"])
        assert can_reopen(agreement) is False
