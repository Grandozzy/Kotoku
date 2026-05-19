from apps.identity.selectors import IdentitySelector
from apps.identity.services import IdentityService


def test_identity_selector_is_importable():
    assert IdentitySelector is not None


def test_identity_service_is_importable():
    assert IdentityService is not None


def test_identity_selector_instantiable():
    selector = IdentitySelector()
    assert selector is not None


def test_identity_service_instantiable():
    service = IdentityService()
    assert service is not None
