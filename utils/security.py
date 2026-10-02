from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

CARD_RE = re.compile(r"^[0-9][0-9 ]{11,22}$")


def parse_amount(value: str) -> Decimal:
    normalized = value.strip().replace(",", ".")
    amount = Decimal(normalized)
    if amount <= 0 or amount.as_tuple().exponent < -2:
        raise ValueError("Некоректна сума")
    return amount.quantize(Decimal("0.01"))


def parse_int(value: str, minimum: int | None = None, maximum: int | None = None) -> int:
    result = int(value.strip())
    if minimum is not None and result < minimum:
        raise ValueError("Значення менше дозволеного")
    if maximum is not None and result > maximum:
        raise ValueError("Значення більше дозволеного")
    return result


def validate_url(value: str) -> str:
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https", "tg"} or not parsed.netloc:
        raise ValueError("Потрібне коректне посилання http(s)://...")
    return url


def validate_card(value: str) -> str:
    clean = re.sub(r"\s+", " ", value.strip())
    digits = re.sub(r"\D", "", clean)
    if not 12 <= len(digits) <= 19:
        raise ValueError("Номер картки має містити 12–19 цифр")
    return digits
