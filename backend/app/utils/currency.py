from __future__ import annotations

import re


def parse_inr(raw: str) -> float | None:
    """
    Parse an INR fare string (e.g. "₹5,180", "5180.00", "INR 5,180") into a float.
    Returns None if the string cannot be parsed.
    """
    if not raw:
        return None
    cleaned = re.sub(r"[₹,\s]", "", raw)
    cleaned = re.sub(r"(?i)inr", "", cleaned)
    try:
        value = float(cleaned)
        return value if value > 0 else None
    except ValueError:
        return None


def format_inr(amount: float) -> str:
    """Format a float as an INR string with comma grouping."""
    return f"₹{amount:,.0f}"
