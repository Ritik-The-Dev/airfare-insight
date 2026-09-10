from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class FareObservation(BaseModel):
    id: UUID
    observed_at: datetime
    travel_date: date
    origin: str
    destination: str
    route: str
    airline: str
    flight_number: str | None = None
    source: str
    price: float
    currency: str
    base_fare: float | None = None
    taxes: float | None = None
    fees: float | None = None
    stops: int
    duration_minutes: int | None = None
    cabin_class: str | None = None
    passengers: int
    advance_purchase_days: int | None = None
    advance_window: str | None = None
    availability: str
    data_type: str
    booking_url: str | None = None
    created_at: datetime


class ObservationSummary(BaseModel):
    total_observations: int
    live_observations: int
    mock_observations: int
    routes_count: int
    airlines_count: int
    sources_count: int
    latest_observation: datetime | None = None


class DailyTrend(BaseModel):
    date: date
    route: str
    average_fare: float
    min_fare: float
    max_fare: float
    observation_count: int
