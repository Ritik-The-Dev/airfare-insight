from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.flight import FlightResult


class FlightSearchParams(BaseModel):
    origin: str          # IATA code
    destination: str     # IATA code
    departure_date: date
    return_date: date | None = None
    passengers: int = 1
    cabin_class: str = "Economy"


class SourceSummary(BaseModel):
    name: str
    type: str                            # "Airline" or "OTA"
    status: str                          # searching/live/unavailable/timeout/blocked/no_results/error
    result_count: int = 0
    last_successful_fetch: datetime | None = None
    response_time_ms: int | None = None
    error: str | None = None


class SearchJob(BaseModel):
    search_id: str
    status: str                          # searching/completed/failed
    sources: list[SourceSummary]
    flights: list[FlightResult]
    started_at: datetime
    completed_at: datetime | None = None
    total_search_time_ms: int | None = None
    cache_age_seconds: int | None = None
