from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler as default_handler

from common.exception_handler import kotoku_exception_handler
from common.exceptions import DomainError


def test_domain_error_returns_400() -> None:
    response = kotoku_exception_handler(
        exc=DomainError("something broke"),
        context={},
    )
    assert response is not None
    assert response.status_code == 400
    assert response.data["status"] == "error"
    assert response.data["message"] == "something broke"


def test_non_domain_error_delegates_to_default_handler() -> None:
    exc = ValueError("not a domain error")
    context = {}
    assert (
        kotoku_exception_handler(exc, context)
        == default_handler(exc, context)
    )


def test_drf_validation_error_still_handled() -> None:
    exc = ValidationError("bad input")
    response = kotoku_exception_handler(exc, context={})
    assert response is not None
    assert response.status_code == 400
