"""
Normalization helpers.

Each scraper returns FlightResult objects that already follow the shared schema.
This module provides post-processing utilities: deduplication, sorting, and
validation of fare fields.
"""
from __future__ import annotations

from app.schemas.flight import FlightResult


def deduplicate(flights: list[FlightResult]) -> list[FlightResult]:
    """
    Remove near-duplicate flights (same airline, flight number, departure time).
    When duplicates exist the one with the lower total_fare is kept.
    """
    seen: dict[str, FlightResult] = {}
    for flight in flights:
        # Key: airline + flight_number + departure minute
        key = (
            f"{flight.airline.lower()}"
            f"|{(flight.flight_number or '').lower()}"
            f"|{flight.departure_time.strftime('%Y-%m-%dT%H:%M')}"
        )
        if key not in seen or flight.total_fare < seen[key].total_fare:
            seen[key] = flight
    return list(seen.values())


def sort_by_fare(flights: list[FlightResult]) -> list[FlightResult]:
    return sorted(flights, key=lambda f: f.total_fare)


def normalize_flight_list(flights: list[FlightResult]) -> list[FlightResult]:
    """
    Apply all normalization steps to a raw list from the orchestrator.
    Steps: deduplicate → sort by fare.
    """
    return sort_by_fare(deduplicate(flights))
