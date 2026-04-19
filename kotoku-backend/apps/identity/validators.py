from django.core.exceptions import ValidationError


def validate_identity_reference(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValidationError("Identity reference cannot be empty or whitespace-only.")
    return stripped
