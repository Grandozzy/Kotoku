def ensure_present(value: str, field_name: str) -> None:
    if not value:
        raise ValueError(f"{field_name} is required")
