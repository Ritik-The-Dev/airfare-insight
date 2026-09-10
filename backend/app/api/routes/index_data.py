"""
Airfare Price Index endpoint.

GET /api/airfare-index

Computes a CPI-style index from fare_observations:
  - Base period = earliest month in the data (index = 100)
  - Each subsequent month's index = (avg_fare / base_avg_fare) * 100
  - Also returns per-route breakdown

When DATABASE_URL is not set, returns mock computed data so the dashboard
still renders correctly in the prototype environment.
"""
from __future__ import annotations

import logging
from typing import Any

import asyncpg
from fastapi import APIRouter

from app.models.config import settings

router = APIRouter(tags=["index"])
logger = logging.getLogger("farelens.index")

# ---------------------------------------------------------------------------
# Hardcoded mock index data (used when DATABASE_URL is not configured)
# These approximate values represent realistic synthetic prototype data.
# ---------------------------------------------------------------------------
_MOCK_MONTHLY: list[dict[str, Any]] = [
    {
        "month": "2026-08",
        "index": 100.0,
        "avg_fare": 5234,
        "observation_count": 420,
        "data_type_mix": {"MOCK": 420, "LIVE": 0},
    },
    {
        "month": "2026-09",
        "index": 103.2,
        "avg_fare": 5406,
        "observation_count": 156,
        "data_type_mix": {"MOCK": 130, "LIVE": 26},
    },
]

_MOCK_ROUTES: list[dict[str, Any]] = [
    {
        "route": "DEL-BOM",
        "monthly_index": [
            {"month": "2026-08", "index": 100.0, "avg_fare": 4820, "observation_count": 72, "data_type_mix": {"MOCK": 72, "LIVE": 0}},
            {"month": "2026-09", "index": 104.1, "avg_fare": 5018, "observation_count": 28, "data_type_mix": {"MOCK": 22, "LIVE": 6}},
        ],
    },
    {
        "route": "DEL-BLR",
        "monthly_index": [
            {"month": "2026-08", "index": 100.0, "avg_fare": 5610, "observation_count": 68, "data_type_mix": {"MOCK": 68, "LIVE": 0}},
            {"month": "2026-09", "index": 101.8, "avg_fare": 5711, "observation_count": 24, "data_type_mix": {"MOCK": 20, "LIVE": 4}},
        ],
    },
    {
        "route": "BOM-BLR",
        "monthly_index": [
            {"month": "2026-08", "index": 100.0, "avg_fare": 4250, "observation_count": 65, "data_type_mix": {"MOCK": 65, "LIVE": 0}},
            {"month": "2026-09", "index": 105.6, "avg_fare": 4488, "observation_count": 22, "data_type_mix": {"MOCK": 18, "LIVE": 4}},
        ],
    },
    {
        "route": "DEL-HYD",
        "monthly_index": [
            {"month": "2026-08", "index": 100.0, "avg_fare": 5890, "observation_count": 70, "data_type_mix": {"MOCK": 70, "LIVE": 0}},
            {"month": "2026-09", "index": 102.4, "avg_fare": 6031, "observation_count": 26, "data_type_mix": {"MOCK": 22, "LIVE": 4}},
        ],
    },
    {
        "route": "DEL-MAA",
        "monthly_index": [
            {"month": "2026-08", "index": 100.0, "avg_fare": 6120, "observation_count": 75, "data_type_mix": {"MOCK": 75, "LIVE": 0}},
            {"month": "2026-09", "index": 103.8, "avg_fare": 6353, "observation_count": 30, "data_type_mix": {"MOCK": 24, "LIVE": 6}},
        ],
    },
    {
        "route": "BOM-DEL",
        "monthly_index": [
            {"month": "2026-08", "index": 100.0, "avg_fare": 4950, "observation_count": 70, "data_type_mix": {"MOCK": 70, "LIVE": 0}},
            {"month": "2026-09", "index": 102.9, "avg_fare": 5094, "observation_count": 26, "data_type_mix": {"MOCK": 22, "LIVE": 4}},
        ],
    },
]


def _mock_response() -> dict[str, Any]:
    return {
        "base_period": "2026-08",
        "base_index": 100,
        "methodology": (
            "Simple average fare index. Base period = first month of observations. "
            "Index = (avg_fare / base_avg_fare) × 100."
        ),
        "data_disclaimer": (
            "Index values marked MOCK are based on synthetic prototype data only. "
            "Not official government statistics."
        ),
        "monthly_index": _MOCK_MONTHLY,
        "route_indices": _MOCK_ROUTES,
    }


# ---------------------------------------------------------------------------
# Live DB computation helpers
# ---------------------------------------------------------------------------

_MONTHLY_SQL = """
SELECT
    TO_CHAR(DATE_TRUNC('month', observed_at), 'YYYY-MM') AS month,
    ROUND(AVG(price)::numeric, 2)                        AS avg_fare,
    COUNT(*)                                              AS observation_count,
    COUNT(*) FILTER (WHERE data_type = 'MOCK')           AS mock_count,
    COUNT(*) FILTER (WHERE data_type = 'LIVE')           AS live_count
FROM fare_observations
GROUP BY DATE_TRUNC('month', observed_at)
ORDER BY DATE_TRUNC('month', observed_at)
"""

_ROUTE_MONTHLY_SQL = """
SELECT
    route,
    TO_CHAR(DATE_TRUNC('month', observed_at), 'YYYY-MM') AS month,
    ROUND(AVG(price)::numeric, 2)                        AS avg_fare,
    COUNT(*)                                              AS observation_count,
    COUNT(*) FILTER (WHERE data_type = 'MOCK')           AS mock_count,
    COUNT(*) FILTER (WHERE data_type = 'LIVE')           AS live_count
FROM fare_observations
GROUP BY route, DATE_TRUNC('month', observed_at)
ORDER BY route, DATE_TRUNC('month', observed_at)
"""


def _compute_index(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Given sorted monthly rows, compute index relative to first month."""
    if not rows:
        return []
    base_fare = float(rows[0]["avg_fare"])
    if base_fare == 0:
        base_fare = 1.0
    result = []
    for row in rows:
        avg = float(row["avg_fare"])
        idx = round((avg / base_fare) * 100, 1)
        result.append({
            "month": row["month"],
            "index": idx,
            "avg_fare": int(round(avg)),
            "observation_count": int(row["observation_count"]),
            "data_type_mix": {
                "MOCK": int(row["mock_count"]),
                "LIVE": int(row["live_count"]),
            },
        })
    return result


async def _live_response() -> dict[str, Any]:
    """Compute the airfare index from the live database."""
    try:
        conn = await asyncpg.connect(settings.database_url)
        try:
            monthly_rows = [dict(r) for r in await conn.fetch(_MONTHLY_SQL)]
            route_rows = [dict(r) for r in await conn.fetch(_ROUTE_MONTHLY_SQL)]
        finally:
            await conn.close()
    except Exception as exc:
        logger.error("Failed to compute airfare index from DB: %s", exc)
        return _mock_response()

    if not monthly_rows:
        # DB is configured but empty — fall back to mock so dashboard shows data
        return _mock_response()

    monthly_index = _compute_index(monthly_rows)
    base_period = monthly_index[0]["month"] if monthly_index else "N/A"

    # Group route rows by route name
    route_map: dict[str, list[dict[str, Any]]] = {}
    for r in route_rows:
        route_map.setdefault(r["route"], []).append(r)

    route_indices = [
        {"route": route, "monthly_index": _compute_index(rows)}
        for route, rows in sorted(route_map.items())
    ]

    return {
        "base_period": base_period,
        "base_index": 100,
        "methodology": (
            "Simple average fare index. Base period = first month of observations. "
            "Index = (avg_fare / base_avg_fare) × 100."
        ),
        "data_disclaimer": (
            "Index values marked MOCK are based on synthetic prototype data only. "
            "Not official government statistics."
        ),
        "monthly_index": monthly_index,
        "route_indices": route_indices,
    }


# ---------------------------------------------------------------------------
# Route handler
# ---------------------------------------------------------------------------

@router.get("/airfare-index", tags=["index"])
async def get_airfare_index() -> dict[str, Any]:
    """
    Return the India Domestic Airfare Price Index.

    Base period = earliest month in fare_observations (index = 100).
    When DATABASE_URL is not configured, returns mock computed prototype data.
    """
    if not settings.database_url:
        logger.info("DATABASE_URL not set — returning mock airfare index data")
        return _mock_response()

    return await _live_response()
