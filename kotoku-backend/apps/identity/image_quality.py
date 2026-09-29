from dataclasses import dataclass
from io import BytesIO

from django.conf import settings
from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError


@dataclass(frozen=True)
class CardImageQuality:
    failure_codes: list[str]


def assess_card_image(data: bytes, *, side: str) -> CardImageQuality:
    """Apply conservative capture-quality checks before paid OCR/face APIs."""
    prefix = f"card_{side}"
    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            width, height = image.size
            grayscale = image.convert("L")
    except (OSError, UnidentifiedImageError):
        return CardImageQuality([f"{prefix}_invalid"])

    failures: list[str] = []
    if min(width, height) < settings.IDENTITY_CARD_MIN_SHORT_EDGE:
        failures.append(f"{prefix}_resolution_too_low")

    grayscale.thumbnail((512, 512))
    histogram = grayscale.histogram()
    pixel_count = max(1, sum(histogram))
    dark_ratio = sum(histogram[:11]) / pixel_count
    bright_ratio = sum(histogram[245:]) / pixel_count
    edge_variance = ImageStat.Stat(grayscale.filter(ImageFilter.FIND_EDGES)).var[0]

    if edge_variance < settings.IDENTITY_CARD_MIN_EDGE_VARIANCE:
        failures.append(f"{prefix}_blurry")
    if dark_ratio > settings.IDENTITY_CARD_MAX_DARK_RATIO:
        failures.append(f"{prefix}_too_dark")
    if bright_ratio > settings.IDENTITY_CARD_MAX_BRIGHT_RATIO:
        failures.append(f"{prefix}_overexposed")

    return CardImageQuality(failures)
