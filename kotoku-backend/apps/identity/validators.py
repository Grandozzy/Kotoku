from django.core.exceptions import ValidationError


def validate_identity_reference(value: str) -> None:
    if not value.strip():
        raise ValidationError("Identity reference cannot be empty or whitespace-only.")
