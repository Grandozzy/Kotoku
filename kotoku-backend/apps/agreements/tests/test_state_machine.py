import pytest

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.domain.state_machine import next_state, valid_actions
from common.exceptions import DomainError


class TestNextState:
    def test_draft_add_party_stays_draft(self):
        assert next_state(AgreementStatus.DRAFT, "add_party") == AgreementStatus.DRAFT

    def test_draft_request_consent_goes_to_pending(self):
        assert (
            next_state(AgreementStatus.DRAFT, "request_consent")
            == AgreementStatus.PENDING_CONSENT
        )

    def test_sealed_request_reopen_goes_to_reopen_requested(self):
        assert (
            next_state(AgreementStatus.SEALED, "request_reopen")
            == AgreementStatus.REOPEN_REQUESTED
        )

    def test_reopen_requested_bilateral_confirm_goes_to_active(self):
        assert (
            next_state(AgreementStatus.REOPEN_REQUESTED, "bilateral_confirm")
            == AgreementStatus.ACTIVE
        )

    def test_reopen_requested_cancel_goes_to_sealed(self):
        assert (
            next_state(AgreementStatus.REOPEN_REQUESTED, "cancel_reopen")
            == AgreementStatus.SEALED
        )

    def test_sealed_archive_goes_to_archived(self):
        assert next_state(AgreementStatus.SEALED, "archive") == AgreementStatus.ARCHIVED

    def test_sealed_expire_goes_to_expired(self):
        assert next_state(AgreementStatus.SEALED, "expire") == AgreementStatus.EXPIRED

    def test_pending_consent_all_consented_goes_to_active(self):
        assert (
            next_state(AgreementStatus.PENDING_CONSENT, "all_consented")
            == AgreementStatus.ACTIVE
        )

    def test_active_seal_goes_to_sealed(self):
        assert next_state(AgreementStatus.ACTIVE, "seal") == AgreementStatus.SEALED

    def test_sealed_close_goes_to_closed(self):
        assert next_state(AgreementStatus.SEALED, "close") == AgreementStatus.CLOSED

    def test_sealed_reopen_goes_to_active(self):
        assert next_state(AgreementStatus.SEALED, "reopen") == AgreementStatus.ACTIVE

    def test_pending_consent_seal_goes_to_sealed(self):
        # New direct path: PENDING_CONSENT → seal → SEALED (skips ACTIVE).
        assert (
            next_state(AgreementStatus.PENDING_CONSENT, "seal")
            == AgreementStatus.SEALED
        )

    @pytest.mark.parametrize(
        "current,action",
        [
            (AgreementStatus.DRAFT, "seal"),
            (AgreementStatus.DRAFT, "all_consented"),
            (AgreementStatus.DRAFT, "close"),
            (AgreementStatus.PENDING_CONSENT, "add_party"),
            (AgreementStatus.ACTIVE, "request_consent"),
            (AgreementStatus.ACTIVE, "add_party"),
            (AgreementStatus.SEALED, "add_party"),
            (AgreementStatus.SEALED, "request_consent"),
            (AgreementStatus.CLOSED, "add_party"),
            (AgreementStatus.CLOSED, "seal"),
            (AgreementStatus.CLOSED, "reopen"),
        ],
    )
    def test_invalid_transition_raises_domain_error(self, current, action):
        with pytest.raises(DomainError, match="Invalid transition"):
            next_state(current, action)


class TestValidActions:
    def test_draft_actions(self):
        actions = valid_actions(AgreementStatus.DRAFT)
        assert "add_party" in actions
        assert "request_consent" in actions

    def test_pending_consent_actions(self):
        actions = valid_actions(AgreementStatus.PENDING_CONSENT)
        assert "all_consented" in actions
        assert "seal" in actions

    def test_active_actions(self):
        assert valid_actions(AgreementStatus.ACTIVE) == ["seal"]

    def test_sealed_actions(self):
        actions = valid_actions(AgreementStatus.SEALED)
        assert "close" in actions
        assert "reopen" in actions
        assert "request_reopen" in actions
        assert "archive" in actions
        assert "expire" in actions

    def test_reopen_requested_actions(self):
        actions = valid_actions(AgreementStatus.REOPEN_REQUESTED)
        assert "bilateral_confirm" in actions
        assert "cancel_reopen" in actions

    def test_closed_can_be_archived(self):
        assert "archive" in valid_actions(AgreementStatus.CLOSED)
