"""
Tests for GET /api/fare-observations endpoints.
Uses FastAPI TestClient with mocked persistence layer — no real DB required.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def _sample_row() -> dict:
    return {
        "id": uuid.uuid4(),
        "observed_at": datetime.now(tz=timezone.utc),
        "travel_date": date.today(),
        "origin": "DEL",
        "destination": "BOM",
        "route": "DEL-BOM",
        "airline": "IndiGo",
        "flight_number": "6E123",
        "source": "IndiGo",
        "price": 5500.0,
        "currency": "INR",
        "base_fare": 4600.0,
        "taxes": 900.0,
        "fees": None,
        "stops": 0,
        "duration_minutes": 135,
        "cabin_class": "Economy",
        "passengers": 1,
        "advance_purchase_days": 3,
        "advance_window": None,
        "availability": "available",
        "data_type": "MOCK",
        "booking_url": None,
        "created_at": datetime.now(tz=timezone.utc),
    }


def _sample_summary() -> dict:
    return {
        "total_observations": 1250,
        "live_observations": 50,
        "mock_observations": 1200,
        "routes_count": 6,
        "airlines_count": 5,
        "sources_count": 3,
        "latest_observation": datetime.now(tz=timezone.utc),
    }


# ---------------------------------------------------------------------------
# Test 14: GET /api/fare-observations returns list
# ---------------------------------------------------------------------------

def test_get_fare_observations_returns_list():
    """14. GET /api/fare-observations returns a list when DB is configured."""
    from app.main import app
    client = TestClient(app, raise_server_exceptions=True)

    with patch("app.api.routes.observations.settings") as mock_settings, \
         patch("app.services.persistence.settings") as mock_pers_settings, \
         patch("app.api.routes.observations.query_observations",
               new=AsyncMock(return_value=[_sample_row()])):
        mock_settings.database_url = "postgresql://fake/db"
        mock_pers_settings.database_url = "postgresql://fake/db"
        response = client.get("/api/fare-observations")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["route"] == "DEL-BOM"


# ---------------------------------------------------------------------------
# Test 15: GET /api/fare-observations/summary returns correct shape
# ---------------------------------------------------------------------------

def test_get_fare_observations_summary_shape():
    """15. GET /api/fare-observations/summary returns correct shape."""
    from app.main import app
    client = TestClient(app, raise_server_exceptions=True)

    with patch("app.api.routes.observations.settings") as mock_settings, \
         patch("app.api.routes.observations.get_summary",
               new=AsyncMock(return_value=_sample_summary())):
        mock_settings.database_url = "postgresql://fake/db"
        response = client.get("/api/fare-observations/summary")

    assert response.status_code == 200
    body = response.json()
    expected_keys = {
        "total_observations", "live_observations", "mock_observations",
        "routes_count", "airlines_count", "sources_count", "latest_observation",
    }
    assert expected_keys.issubset(body.keys())
    assert body["total_observations"] == 1250
    assert body["live_observations"] == 50
    assert body["mock_observations"] == 1200


# ---------------------------------------------------------------------------
# Test 16a: 503 when DB not configured
# ---------------------------------------------------------------------------

def test_get_fare_observations_no_db_returns_503():
    """16a. When DATABASE_URL is empty, endpoint returns 503."""
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)

    with patch("app.api.routes.observations.settings") as mock_settings:
        mock_settings.database_url = ""
        response = client.get("/api/fare-observations?route=DEL-BOM")

    assert response.status_code == 503


# ---------------------------------------------------------------------------
# Test 16b: Filters (route, data_type) are accepted
# ---------------------------------------------------------------------------

def test_get_fare_observations_filters_accepted():
    """16b. Filters (route, data_type) are accepted and passed through."""
    from app.main import app
    client = TestClient(app, raise_server_exceptions=True)

    captured_kwargs: dict = {}

    async def capture_query(**kwargs):
        captured_kwargs.update(kwargs)
        return [_sample_row()]

    with patch("app.api.routes.observations.settings") as mock_settings, \
         patch("app.api.routes.observations.query_observations",
               new=capture_query):
        mock_settings.database_url = "postgresql://fake/db"
        response = client.get("/api/fare-observations?route=DEL-BOM&data_type=MOCK&limit=50")

    assert response.status_code == 200
    assert captured_kwargs.get("route") == "DEL-BOM"
    assert captured_kwargs.get("data_type") == "MOCK"
    assert captured_kwargs.get("limit") == 50


# ---------------------------------------------------------------------------
# Test 16c: Trends requires route param
# ---------------------------------------------------------------------------

def test_get_fare_observations_trends_requires_route():
    """16c. GET /api/fare-observations/trends without route returns 422."""
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)

    with patch("app.api.routes.observations.settings") as mock_settings:
        mock_settings.database_url = "postgresql://fake/db"
        response = client.get("/api/fare-observations/trends")

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 16d: Trends returns daily aggregates
# ---------------------------------------------------------------------------

def test_get_fare_observations_trends_returns_data():
    """16d. GET /api/fare-observations/trends returns daily aggregate list."""
    from app.main import app
    client = TestClient(app, raise_server_exceptions=True)

    trend_row = {
        "date": date(2026, 9, 1),
        "route": "DEL-BOM",
        "average_fare": 5234.0,
        "min_fare": 4900.0,
        "max_fare": 5800.0,
        "observation_count": 12,
    }

    with patch("app.api.routes.observations.settings") as mock_settings, \
         patch("app.api.routes.observations.get_trends",
               new=AsyncMock(return_value=[trend_row])):
        mock_settings.database_url = "postgresql://fake/db"
        response = client.get("/api/fare-observations/trends?route=DEL-BOM")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["route"] == "DEL-BOM"
    assert body[0]["average_fare"] == 5234.0
    assert body[0]["observation_count"] == 12
