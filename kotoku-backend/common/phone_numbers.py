import re

_E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_phone_for_compare(phone: str | None) -> str:
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        return f"233{digits[1:]}"
    return digits


def normalize_phone_to_e164(phone: str | None) -> str:
    raw = str(phone or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        return f"+233{digits[1:]}"
    if raw.startswith("+") and digits:
        return f"+{digits}"
    return raw


def is_valid_phone_input(phone: str | None) -> bool:
    return bool(_E164_PATTERN.fullmatch(normalize_phone_to_e164(phone)))


def same_phone(left: str | None, right: str | None) -> bool:
    normalized_left = normalize_phone_for_compare(left)
    normalized_right = normalize_phone_for_compare(right)
    return bool(normalized_left and normalized_left == normalized_right)


def phone_lookup_values(phone: str | None) -> list[str]:
    raw = str(phone or "").strip()
    e164 = normalize_phone_to_e164(raw)
    digits = normalize_phone_for_compare(raw)
    values = {raw, e164}
    if digits:
        values.add(digits)
    if digits.startswith("233") and len(digits) == 12:
        values.add(f"0{digits[3:]}")
    values.discard("")
    return list(values)
