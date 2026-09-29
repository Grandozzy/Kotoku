from io import BytesIO

from django.test import override_settings
from PIL import Image

from apps.identity.image_quality import assess_card_image


def _image_bytes(*, size: tuple[int, int], color: int = 128) -> bytes:
    output = BytesIO()
    Image.new("L", size, color=color).save(output, format="JPEG")
    return output.getvalue()


class TestCardImageQuality:
    def test_rejects_invalid_image(self):
        result = assess_card_image(b"not-an-image", side="front")
        assert result.failure_codes == ["card_front_invalid"]

    @override_settings(
        IDENTITY_CARD_MIN_SHORT_EDGE=1000,
        IDENTITY_CARD_MIN_EDGE_VARIANCE=0,
        IDENTITY_CARD_MAX_DARK_RATIO=1,
        IDENTITY_CARD_MAX_BRIGHT_RATIO=1,
    )
    def test_rejects_low_resolution_with_side_specific_code(self):
        result = assess_card_image(_image_bytes(size=(1200, 800)), side="back")
        assert result.failure_codes == ["card_back_resolution_too_low"]

    @override_settings(
        IDENTITY_CARD_MIN_SHORT_EDGE=1000,
        IDENTITY_CARD_MIN_EDGE_VARIANCE=40,
        IDENTITY_CARD_MAX_DARK_RATIO=0.5,
        IDENTITY_CARD_MAX_BRIGHT_RATIO=0.5,
    )
    def test_flags_extreme_dark_flat_capture(self):
        result = assess_card_image(_image_bytes(size=(1600, 1100), color=0), side="front")
        assert "card_front_blurry" in result.failure_codes
        assert "card_front_too_dark" in result.failure_codes
