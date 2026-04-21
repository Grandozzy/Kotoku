"""Root pytest configuration.

Fixtures defined here are available to all tests across apps/ and tests/.
"""
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_sms_gateway(request):
    """Prevent any test from hitting the real SMS gateway.

    Mark a test or class with @pytest.mark.real_sms_gateway to bypass this
    fixture and exercise the real SmsGateway code path.
    """
    if request.node.get_closest_marker("real_sms_gateway"):
        yield
    else:
        with patch("infrastructure.sms.gateway.SmsGateway.send", return_value=True):
            yield


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear Django's cache before and after each test.

    Prevents rate-limiter state (e.g. OTP attempt counters) from leaking
    between tests.
    """
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()
