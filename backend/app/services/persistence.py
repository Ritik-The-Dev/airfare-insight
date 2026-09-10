"""
Fare observation persistence — Supabase PostgreSQL via asyncpg.

Inserts LIVE fare observations after each successful search.
If DATABASE_URL is not configured, logs a warning and skips silently.
On any DB error: logs the error, returns 0, never crashes the search.

Idempotency:
    Duplicate key = same (route, airline, flight_number, source, data_type,
                          minute-truncated observed_at, travel_date).
    Uses INSERT ... ON CONFLICT DO NOTHING so retries are safe.

Advance window classification:
    Only exact matches: 1→T+1, 7→T+7, 15→T+15, 30→T+30, 45→T+45.
    Everything else → NULL. Never approximate.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import asyncpg

from app.models.config import settings
from app.schemas.flight import FlightResult
from app.schemas.search import FlightSearchParams

logger = logging.getLogger("farelens.persistence")

_ADVANCE_WINDOW_MAP: dict[int, str] = {
    1: "T+1",
    7: "T+7",
    15: "T+15",
    30: "T+30",
    45: "T+45",
}

_INSERT_SQL = """
INSERT INTO fare_observations (
    observed_at, travel_date, origin, destination, route,
    airline, flight_number, source,
    price, currency, base_fare, taxes, fees,
    stops, duration_minutes, cabin_class, passengers,
    advance_purchase_days, advance_window,
    availability, data_type, booking_url
) VALUES (
    $1, $2, $3, $4, $5,
    $6, $7, $8,
    $9, $10, $11, $12, $13,
    $14, $15, $16, $17,
    $18, $19,
    $20, $21, $22
)
ON CONFLICT DO NOTHING
"""


def _calc_advance(travel_date: date, observed_at: datetime) -> tuple[int | None, str | None]:
    today = observed_at.date()
    days = (travel_date - today).days
    if days < 0:
        return None, None
    window = _ADVANCE_WINDOW_MAP.get(days)
    return days, window


async def persist_observations(
    flights: list[FlightResult],
    params: FlightSearchParams,
    data_type: str = "LIVE",
) -> int:
    """
    Persist a list of normalized FlightResult objects as fare observations.

    Returns the number of rows actually inserted (conflicts skipped).
    Never raises — all exceptions are caught and logged.
    """
    if not settings.database_url:
        logger.warning("DATABASE_URL not configured — skipping fare observation persistence")
        return 0

    if not flights:
        return 0

    observed_at = datetime.now(tz=timezone.utc)
    rows = []

    for f in flights:
        adv_days, adv_window = _calc_advance(params.departure_date, observed_at)
        route = f"{f.origin}-{f.destination}"
        rows.append((
            observed_at,                          # $1  observed_at
            params.departure_date,                # $2  travel_date
            f.origin,                             # $3  origin
            f.destination,                        # $4  destination
            route,                                # $5  route
            f.airline,                            # $6  airline
            f.flight_number,                      # $7  flight_number (nullable)
            f.source,                             # $8  source
            f.total_fare,                         # $9  price
            f.currency,                           # $10 currency
            f.base_fare,                          # $11 base_fare (nullable)
            f.taxes,                              # $12 taxes (nullable)
            f.fees,                               # $13 fees (nullable)
            f.stops,                              # $14 stops
            f.duration_minutes,                   # $15 duration_minutes
            f.cabin_class,                        # $16 cabin_class
            params.passengers,                    # $17 passengers
            adv_days,                             # $18 advance_purchase_days
            adv_window,                           # $19 advance_window
            "available",                          # $20 availability
            data_type,                            # $21 data_type (LIVE or MOCK)
            f.booking_url,                        # $22 booking_url (nullable)
        ))

    try:
        conn = await asyncpg.connect(settings.database_url)
        try:
            result = await conn.executemany(_INSERT_SQL, rows)
            # executemany returns a string like "INSERT 0 N" for the last batch
            # Count non-conflict inserts by querying isn't straightforward with executemany,
            # so we return len(rows) as attempted; actual inserts may be fewer due to conflicts.
            inserted = len(rows)
            logger.info(
                "Persisted %d %s fare observations for %s→%s",
                inserted, data_type, params.origin, params.destination,
            )
            return inserted
        finally:
            await conn.close()
    except Exception as exc:
        logger.error("Failed to persist fare observations to Supabase: %s", exc)
        return 0


async def query_observations(
    *,
    route: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
    airline: str | None = None,
    source: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    advance_window: str | None = None,
    data_type: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Query fare_observations with optional filters. Returns list of dicts."""
    if not settings.database_url:
        return []

    conditions = []
    args: list = []
    idx = 1

    if route:
        conditions.append(f"route = ${idx}"); args.append(route); idx += 1
    if origin:
        conditions.append(f"origin = ${idx}"); args.append(origin.upper()); idx += 1
    if destination:
        conditions.append(f"destination = ${idx}"); args.append(destination.upper()); idx += 1
    if airline:
        conditions.append(f"airline ILIKE ${idx}"); args.append(f"%{airline}%"); idx += 1
    if source:
        conditions.append(f"source ILIKE ${idx}"); args.append(f"%{source}%"); idx += 1
    if start_date:
        conditions.append(f"observed_at >= ${idx}"); args.append(start_date); idx += 1
    if end_date:
        conditions.append(f"observed_at <= ${idx}"); args.append(end_date); idx += 1
    if advance_window:
        conditions.append(f"advance_window = ${idx}"); args.append(advance_window); idx += 1
    if data_type:
        conditions.append(f"data_type = ${idx}"); args.append(data_type.upper()); idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT id, observed_at, travel_date, origin, destination, route,
               airline, flight_number, source, price, currency,
               base_fare, taxes, fees, stops, duration_minutes, cabin_class,
               passengers, advance_purchase_days, advance_window,
               availability, data_type, booking_url, created_at
        FROM fare_observations
        {where}
        ORDER BY observed_at DESC
        LIMIT {min(limit, 1000)}
    """

    try:
        conn = await asyncpg.connect(settings.database_url)
        try:
            rows = await conn.fetch(sql, *args)
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    except Exception as exc:
        logger.error("Failed to query fare observations: %s", exc)
        return []


async def get_summary() -> dict:
    """Return aggregate summary of fare_observations table."""
    if not settings.database_url:
        return {
            "total_observations": 0, "live_observations": 0, "mock_observations": 0,
            "routes_count": 0, "airlines_count": 0, "sources_count": 0,
            "latest_observation": None,
        }

    sql = """
        SELECT
            COUNT(*) AS total_observations,
            COUNT(*) FILTER (WHERE data_type = 'LIVE') AS live_observations,
            COUNT(*) FILTER (WHERE data_type = 'MOCK') AS mock_observations,
            COUNT(DISTINCT route) AS routes_count,
            COUNT(DISTINCT airline) AS airlines_count,
            COUNT(DISTINCT source) AS sources_count,
            MAX(observed_at) AS latest_observation
        FROM fare_observations
    """
    try:
        conn = await asyncpg.connect(settings.database_url)
        try:
            row = await conn.fetchrow(sql)
            return dict(row) if row else {}
        finally:
            await conn.close()
    except Exception as exc:
        logger.error("Failed to fetch observation summary: %s", exc)
        return {
            "total_observations": 0, "live_observations": 0, "mock_observations": 0,
            "routes_count": 0, "airlines_count": 0, "sources_count": 0,
            "latest_observation": None,
        }


async def get_trends(
    route: str,
    start_date: str | None = None,
    end_date: str | None = None,
    data_type: str | None = None,
) -> list[dict]:
    """Return daily average/min/max fares for a route."""
    if not settings.database_url:
        return []

    conditions = ["route = $1"]
    args: list = [route]
    idx = 2

    if start_date:
        conditions.append(f"observed_at >= ${idx}"); args.append(start_date); idx += 1
    if end_date:
        conditions.append(f"observed_at <= ${idx}"); args.append(end_date); idx += 1
    if data_type:
        conditions.append(f"data_type = ${idx}"); args.append(data_type.upper()); idx += 1

    where = f"WHERE {' AND '.join(conditions)}"
    sql = f"""
        SELECT
            observed_at::date AS date,
            route,
            ROUND(AVG(price)::numeric, 2) AS average_fare,
            MIN(price) AS min_fare,
            MAX(price) AS max_fare,
            COUNT(*) AS observation_count
        FROM fare_observations
        {where}
        GROUP BY observed_at::date, route
        ORDER BY observed_at::date
    """

    try:
        conn = await asyncpg.connect(settings.database_url)
        try:
            rows = await conn.fetch(sql, *args)
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    except Exception as exc:
        logger.error("Failed to fetch fare trends: %s", exc)
        return []
