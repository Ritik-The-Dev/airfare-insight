from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


def format_date_for_url(d: date) -> str:
    """Return YYYY-MM-DD string suitable for query params."""
    return d.strftime("%Y-%m-%d")


def format_date_ddmmyyyy(d: date) -> str:
    """Return DD/MM/YYYY string used by some Indian OTAs."""
    return d.strftime("%d/%m/%Y")


def format_date_ddmonyyyy(d: date) -> str:
    """Return DDMonYYYY (e.g. 12Sep2026) used by some airline sites."""
    return d.strftime("%d%b%Y")


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def duration_minutes(departure: datetime, arrival: datetime) -> int:
    """Return non-negative duration in minutes between two datetimes."""
    delta: timedelta = arrival - departure
    return max(0, int(delta.total_seconds() // 60))
