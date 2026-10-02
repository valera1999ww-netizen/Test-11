from __future__ import annotations

from decimal import Decimal
from html import escape


def money(value: Decimal | float | int) -> str:
    return f"{Decimal(value):.2f}".rstrip("0").rstrip(".")


def safe(value: object) -> str:
    return escape(str(value))


def masked_destination(value: str) -> str:
    clean = value.strip()
    if len(clean) <= 4:
        return "****"
    tail = clean[-4:]
    return f"**** **** **** {tail}"
