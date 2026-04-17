from django.core.exceptions import ValidationError


def validate_identity_reference(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValidationError("Identity reference cannot be empty or whitespace-only.")
    if len(stripped) > 128:
        raise ValidationError("Identity reference must be 128 characters or fewer.")
    return stripped
