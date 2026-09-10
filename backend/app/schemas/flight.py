from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FlightResult(BaseModel):
    id: str
    source: str
    airline: str
    flight_number: str | None = None
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    stops: int
    cabin_class: str
    base_fare: float | None = None
    taxes: float | None = None
    fees: float | None = None
    total_fare: float
    currency: str = "INR"
    baggage: str | None = None
    booking_url: str | None = None
    scraped_at: datetime
    status: str = "live"
