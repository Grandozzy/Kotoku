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

    @pytest.mark.parametrize(
        "current,action",
        [
            (AgreementStatus.DRAFT, "seal"),
            (AgreementStatus.DRAFT, "all_consented"),
            (AgreementStatus.DRAFT, "close"),
            (AgreementStatus.PENDING_CONSENT, "seal"),
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
        assert valid_actions(AgreementStatus.PENDING_CONSENT) == ["all_consented"]

    def test_active_actions(self):
        assert valid_actions(AgreementStatus.ACTIVE) == ["seal"]

    def test_sealed_actions(self):
        actions = valid_actions(AgreementStatus.SEALED)
        assert "close" in actions
        assert "reopen" in actions

    def test_closed_has_no_actions(self):
        assert valid_actions(AgreementStatus.CLOSED) == []
