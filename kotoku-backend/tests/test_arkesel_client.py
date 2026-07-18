import json
import urllib.error
from unittest.mock import Mock, patch

from django.test import override_settings

from infrastructure.sms.arkesel_client import ArkeselOtpClient


@override_settings(ARKESEL_API_KEY="test-key", ARKESEL_SENDER_ID="Kotoku")
def test_send_otp_success():
    with patch("infrastructure.sms.arkesel_client.urllib.request.urlopen") as mock_urlopen:
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps(
            {"code": "1000", "message": "Successful, OTP is being processed for delivery"}
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = ArkeselOtpClient().send_otp(
            number="+233501234567",
            message="Your code is %otp_code%",
        )

    assert result is True
    call_args = mock_urlopen.call_args[0][0]
    body = json.loads(call_args.data)
    assert body["number"] == "+233501234567"
    assert body["sender_id"] == "Kotoku"
    assert body["message"] == "Your code is %otp_code%"
    assert body["type"] == "numeric"
    assert body["expiry"] == 5
    assert body["length"] == 6
    assert body["medium"] == "sms"


@override_settings(ARKESEL_API_KEY="test-key")
def test_send_otp_rejected():
    with patch("infrastructure.sms.arkesel_client.urllib.request.urlopen") as mock_urlopen:
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps(
            {"code": "1002", "message": "Invalid sender ID"}
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = ArkeselOtpClient().send_otp(
            number="+233501234567",
            message="Your code is %otp_code%",
        )

    assert result is False


@override_settings(ARKESEL_API_KEY="test-key")
def test_send_otp_http_error():
    with patch("infrastructure.sms.arkesel_client.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://example.com", 401, "Unauthorized", {}, None
        )

        result = ArkeselOtpClient().send_otp(
            number="+233501234567",
            message="Your code is %otp_code%",
        )

    assert result is False


@override_settings(ARKESEL_API_KEY="test-key")
def test_verify_otp_success():
    with patch("infrastructure.sms.arkesel_client.urllib.request.urlopen") as mock_urlopen:
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps(
            {"code": "1100", "message": "Successful"}
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = ArkeselOtpClient().verify_otp(
            number="+233501234567",
            code="123456",
        )

    assert result is True


@override_settings(ARKESEL_API_KEY="test-key")
def test_verify_otp_rejected():
    with patch("infrastructure.sms.arkesel_client.urllib.request.urlopen") as mock_urlopen:
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps(
            {"code": "1102", "message": "Invalid code"}
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = ArkeselOtpClient().verify_otp(
            number="+233501234567",
            code="000000",
        )

    assert result is False


@override_settings(ARKESEL_API_KEY="test-key")
def test_verify_otp_http_error():
    with patch("infrastructure.sms.arkesel_client.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://example.com", 422, "Unprocessable", {}, None
        )

        result = ArkeselOtpClient().verify_otp(
            number="+233501234567",
            code="000000",
        )

    assert result is False


@override_settings(ARKESEL_API_KEY="")
def test_send_otp_missing_api_key():
    try:
        ArkeselOtpClient().send_otp(number="+233501234567", message="test")
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert "ARKESEL_API_KEY" in str(e)


@override_settings(ARKESEL_API_KEY="")
def test_verify_otp_missing_api_key():
    try:
        ArkeselOtpClient().verify_otp(number="+233501234567", code="123456")
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert "ARKESEL_API_KEY" in str(e)
