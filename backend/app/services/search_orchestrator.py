"""
Search orchestrator — powered by Ignav Flights API.

Calls https://ignav.com/api/fares/one-way to fetch real live fares,
maps the response to the FareLens FlightResult schema, and exposes
the same job-based polling interface the frontend expects.

Scraper adapters are preserved in app/scrapers/ for future use but are
not called here.

In-memory job store:
    _jobs: dict[str, SearchJob]   — keyed by search_id

Flow:
    start_search(params)   → creates job, fires background task, returns immediately
    get_job(search_id)     → returns current (possibly still-updating) job
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone

import httpx

from app.models.config import settings
from app.schemas.flight import FlightResult
from app.schemas.search import FlightSearchParams, SearchJob, SourceSummary
from app.services.cache import SearchCache
from app.services.normalization import normalize_flight_list
from app.utils.logging import get_logger

logger = get_logger("farelens.orchestrator")

# In-memory job store
_jobs: dict[str, SearchJob] = {}

# Ignav API
_IGNAV_BASE = "https://ignav.com/api"
_IGNAV_HEADERS = {
    "Content-Type": "application/json",
    "X-Api-Key": settings.ignav_api_key,
}

# We present results as coming from a single "Ignav" source so the
# frontend's source comparison table still works. We also show the
# eight original airline/OTA labels as separate "pending" sources
# in the loading panel to match the product design.
_DISPLAY_SOURCES = [
    SourceSummary(name="IndiGo",      type="Airline", status="searching"),
    SourceSummary(name="Air India",   type="Airline", status="searching"),
    SourceSummary(name="Akasa Air",   type="Airline", status="searching"),
    SourceSummary(name="SpiceJet",    type="Airline", status="searching"),
    SourceSummary(name="MakeMyTrip",  type="OTA",     status="searching"),
    SourceSummary(name="Cleartrip",   type="OTA",     status="searching"),
    SourceSummary(name="EaseMyTrip",  type="OTA",     status="searching"),
    SourceSummary(name="ixigo",       type="OTA",     status="searching"),
]


async def start_search(params: FlightSearchParams) -> SearchJob:
    """Create job and fire background fetch. Returns immediately."""
    cached = SearchCache.get(params)
    if cached is not None:
        logger.info("Cache hit for %s→%s on %s", params.origin, params.destination, params.departure_date)
        return cached

    search_id = str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc)

    # Clone display sources so mutations stay per-job
    sources = [s.model_copy() for s in _DISPLAY_SOURCES]

    job = SearchJob(
        search_id=search_id,
        status="searching",
        sources=sources,
        flights=[],
        started_at=now,
    )
    _jobs[search_id] = job

    asyncio.create_task(_fetch_ignav(search_id, params))
    return job


async def _fetch_ignav(search_id: str, params: FlightSearchParams) -> None:
    """Call Ignav API, map results, update job."""
    job = _jobs[search_id]
    wall_start = time.monotonic()

    payload: dict = {
        "origin": params.origin,
        "destination": params.destination,
        "departure_date": str(params.departure_date),
        "adults": params.passengers,
    }
    if params.cabin_class and params.cabin_class.lower() != "economy":
        payload["cabin_class"] = params.cabin_class.lower().replace(" ", "_")

    flights: list[FlightResult] = []
    error_msg: str | None = None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{_IGNAV_BASE}/fares/one-way",
                json=payload,
                headers=_IGNAV_HEADERS,
            )
        if resp.status_code != 200:
            error_msg = f"Ignav API returned HTTP {resp.status_code}"
            logger.warning("[search %s] %s", search_id, error_msg)
        else:
            data = resp.json()
            flights = _map_ignav_response(data, params)
            logger.info(
                "[search %s] Ignav returned %d itineraries in %.1fs",
                search_id, len(flights),
                time.monotonic() - wall_start,
            )
    except httpx.TimeoutException:
        error_msg = "Ignav API timed out"
        logger.warning("[search %s] %s", search_id, error_msg)
    except Exception as exc:
        error_msg = f"Ignav API error: {exc}"
        logger.error("[search %s] %s", search_id, error_msg)

    # Map each returned flight's airline to one of the 8 display sources
    # so the comparison table shows per-airline pricing.
    now = datetime.now(tz=timezone.utc)
    total_ms = int((time.monotonic() - wall_start) * 1000)

    # Build a per-airline cheapest fare map for the sources panel
    airline_flights: dict[str, list[FlightResult]] = {}
    for f in flights:
        airline_flights.setdefault(f.airline, []).append(f)

    # Map Ignav airline names → FareLens source names
    _ALIAS: dict[str, str] = {
        "indigo": "IndiGo",
        "6e": "IndiGo",
        "air india": "Air India",
        "ai": "Air India",
        "akasa": "Akasa Air",
        "qp": "Akasa Air",
        "spicejet": "SpiceJet",
        "sg": "SpiceJet",
    }

    def _resolve_source(airline: str) -> str:
        key = airline.lower().strip()
        return _ALIAS.get(key, airline)  # fall back to the airline name itself

    updated_sources: list[SourceSummary] = []
    for s in job.sources:
        # Find flights that map to this source
        matched = [
            f for f in flights
            if _resolve_source(f.airline) == s.name or f.source == s.name
        ]
        if error_msg and not flights:
            updated_sources.append(SourceSummary(
                name=s.name, type=s.type, status="unavailable",
                result_count=0, error=error_msg,
                response_time_ms=total_ms,
            ))
        elif matched:
            updated_sources.append(SourceSummary(
                name=s.name, type=s.type, status="live",
                result_count=len(matched),
                last_successful_fetch=now,
                response_time_ms=total_ms,
            ))
            # Tag these flights with the FareLens source name
            for f in matched:
                f.source = s.name
        else:
            # No results from this airline in the Ignav response
            updated_sources.append(SourceSummary(
                name=s.name, type=s.type, status="no_results",
                result_count=0, response_time_ms=total_ms,
            ))

    normalized = normalize_flight_list(flights)

    completed = SearchJob(
        search_id=search_id,
        status="completed",
        sources=updated_sources,
        flights=normalized,
        started_at=job.started_at,
        completed_at=now,
        total_search_time_ms=total_ms,
    )
    _jobs[search_id] = completed

    if normalized:
        SearchCache.set(params, completed)

    # Persist LIVE observations (non-blocking, errors logged but not raised)
    if normalized:
        try:
            from app.services.persistence import persist_observations
            n = await persist_observations(normalized, params, data_type="LIVE")
            logger.info("Persisted %d LIVE fare observations", n)
        except Exception as exc:
            logger.error("Persistence error (search continues): %s", exc)


def _map_ignav_response(data: dict, params: FlightSearchParams) -> list[FlightResult]:
    """Convert Ignav API response to list[FlightResult]."""
    results: list[FlightResult] = []
    scraped_at = datetime.now(tz=timezone.utc)

    itineraries = data.get("itineraries", [])
    for itin in itineraries:
        try:
            price_info = itin.get("price", {})
            amount = price_info.get("amount")
            currency = price_info.get("currency", "USD")
            if amount is None:
                continue

            total_fare = float(amount)

            # Convert USD to INR if needed (approximate rate)
            if currency.upper() == "USD":
                total_fare = round(total_fare * 84.0, 2)
                currency = "INR"
            elif currency.upper() != "INR":
                # Keep as-is but note currency
                pass

            outbound = itin.get("outbound", {})
            carrier = outbound.get("carrier", "Unknown")
            dur = outbound.get("duration_minutes", 0)
            segments = outbound.get("segments", [])
            cabin = itin.get("cabin_class", params.cabin_class)
            stops = max(0, len(segments) - 1)

            if not segments:
                continue

            first_seg = segments[0]
            last_seg = segments[-1]

            dep_str = first_seg.get("departure_time_utc") or first_seg.get("departure_time_local", "")
            arr_str = last_seg.get("arrival_time_utc") or last_seg.get("arrival_time_local", "")

            dep_dt = _parse_dt(dep_str)
            arr_dt = _parse_dt(arr_str)
            if not dep_dt or not arr_dt:
                continue

            flight_number = f"{first_seg.get('marketing_carrier_code', '')}{first_seg.get('flight_number', '')}".strip()
            ignav_id = itin.get("ignav_id", "")
            booking_url = f"https://ignav.com/book/{ignav_id}" if ignav_id else None

            results.append(FlightResult(
                id=str(uuid.uuid4()),
                source=carrier,  # will be remapped to FareLens source name later
                airline=carrier,
                flight_number=flight_number or None,
                origin=params.origin,
                destination=params.destination,
                departure_time=dep_dt,
                arrival_time=arr_dt,
                duration_minutes=dur or _calc_dur(dep_dt, arr_dt),
                stops=stops,
                cabin_class=cabin,
                total_fare=total_fare,
                currency=currency,
                scraped_at=scraped_at,
                status="live",
            ))
        except Exception as exc:
            logger.debug("Skipping itinerary due to parse error: %s", exc)
            continue

    return results


def _parse_dt(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _calc_dur(dep: datetime, arr: datetime) -> int:
    return max(0, int((arr - dep).total_seconds() / 60))


def get_job(search_id: str) -> SearchJob | None:
    return _jobs.get(search_id)
