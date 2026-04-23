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


def test_non_domain_error_returns_none() -> None:
    response = kotoku_exception_handler(
        exc=ValueError("not a domain error"),
        context={},
    )
    assert response is None
