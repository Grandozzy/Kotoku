"""Tests for phone number validation with country codes."""
from django.test import TestCase

from apps.auth.services import PhoneService
from common.exceptions import DomainError


class TestPhoneService(TestCase):
    """Test PhoneService for E164 validation."""

    def test_validate_format_valid_e164(self):
        """Accept valid E164 format with country code."""
        result = PhoneService.validate_format("+233501234567")
        assert result is None

    def test_validate_format_valid_country_code_range(self):
        """Country code must start with 1-9 (not 0)."""
        with self.assertRaises(DomainError) as cm:
            PhoneService.validate_format("+0233501234567")
        assert "country code" in str(cm.exception)

    def test_validate_format_valid_phone_length(self):
        """Phone number 7-15 digits."""
        PhoneService.validate_format("+2331234567")  # 7 digits
        PhoneService.validate_format("+23312345678901")  # 11 digits

    def test_validate_format_invalid_phone_too_short(self):
        """Phone number too short."""
        with self.assertRaises(DomainError) as cm:
            PhoneService.validate_format("+2331")
        assert "Invalid phone number" in str(cm.exception)

    def test_validate_format_invalid_phone_too_long(self):
        """Phone number too long."""
        with self.assertRaises(DomainError) as cm:
            PhoneService.validate_format("+2331234567890123456")  # 16 digits - too long
        assert "Invalid phone number" in str(cm.exception)

    def test_validate_format_missing_country_code(self):
        """Must include country code."""
        with self.assertRaises(DomainError) as cm:
            PhoneService.validate_format("233501234567")
        assert "country code" in str(cm.exception)

    def test_validate_format_invalid_characters(self):
        """Phone number must be digits only."""
        with self.assertRaises(DomainError) as cm:
            PhoneService.validate_format("+23350-1234567")
        assert "Invalid phone number" in str(cm.exception)

    def test_validate_format_space_in_phone(self):
        """Phone number cannot have spaces."""
        with self.assertRaises(DomainError) as cm:
            PhoneService.validate_format("+233 501234567")
        assert "Invalid phone number" in str(cm.exception)