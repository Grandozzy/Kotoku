def build_storage_url(path: str) -> str:
    return f"https://storage.local/{path.lstrip('/')}"
