"""
Fare observations API endpoints.

GET /api/fare-observations          — list with filters
GET /api/fare-observations/summary  — aggregate counts
GET /api/fare-observations/trends   — daily aggregates for a route

Returns 503 when DATABASE_URL is not configured.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.config import settings
from app.schemas.observation import DailyTrend, FareObservation, ObservationSummary
from app.services.persistence import get_summary, get_trends, query_observations

router = APIRouter(tags=["observations"])


def _require_db() -> None:
    """Raise 503 if the database is not configured."""
    if not settings.database_url:
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Set DATABASE_URL in backend/.env",
        )


@router.get("/fare-observations", response_model=list[FareObservation])
async def list_observations(
    route: str | None = Query(None, description="e.g. DEL-BOM"),
    origin: str | None = Query(None),
    destination: str | None = Query(None),
    airline: str | None = Query(None),
    source: str | None = Query(None),
    start_date: str | None = Query(None, description="ISO date or datetime"),
    end_date: str | None = Query(None, description="ISO date or datetime"),
    advance_window: str | None = Query(None, description="T+1 | T+7 | T+15 | T+30 | T+45"),
    data_type: str | None = Query(None, description="LIVE or MOCK"),
    limit: int = Query(100, ge=1, le=1000),
) -> list[FareObservation]:
    _require_db()
    rows = await query_observations(
        route=route,
        origin=origin,
        destination=destination,
        airline=airline,
        source=source,
        start_date=start_date,
        end_date=end_date,
        advance_window=advance_window,
        data_type=data_type,
        limit=limit,
    )
    return [FareObservation(**r) for r in rows]


@router.get("/fare-observations/summary", response_model=ObservationSummary)
async def observations_summary() -> ObservationSummary:
    _require_db()
    data = await get_summary()
    return ObservationSummary(**data)


@router.get("/fare-observations/trends", response_model=list[DailyTrend])
async def observations_trends(
    route: str = Query(..., description="e.g. DEL-BOM"),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    data_type: str | None = Query(None, description="LIVE or MOCK"),
) -> list[DailyTrend]:
    _require_db()
    rows = await get_trends(
        route=route,
        start_date=start_date,
        end_date=end_date,
        data_type=data_type,
    )
    return [DailyTrend(**r) for r in rows]
