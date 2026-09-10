"""
Tests for fare observation persistence logic.
Uses unittest.mock — no real database connection required.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.flight import FlightResult
from app.schemas.search import FlightSearchParams
from app.services.persistence import _calc_advance, persist_observations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_flight(**kwargs) -> FlightResult:
    defaults = dict(
        id="test-id",
        source="IndiGo",
        airline="IndiGo",
        flight_number="6E123",
        origin="DEL",
        destination="BOM",
        departure_time=datetime(2026, 9, 11, 6, 0, tzinfo=timezone.utc),
        arrival_time=datetime(2026, 9, 11, 8, 10, tzinfo=timezone.utc),
        duration_minutes=130,
        stops=0,
        cabin_class="economy",
        total_fare=5292.0,
        currency="INR",
        scraped_at=datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc),
        status="live",
    )
    defaults.update(kwargs)
    return FlightResult(**defaults)


def make_params(**kwargs) -> FlightSearchParams:
    defaults = dict(
        origin="DEL", destination="BOM",
        departure_date=date(2026, 9, 11),
        passengers=1, cabin_class="Economy",
    )
    defaults.update(kwargs)
    return FlightSearchParams(**defaults)


# ---------------------------------------------------------------------------
# advance_purchase_days / advance_window tests
# ---------------------------------------------------------------------------

def test_advance_days_t1():
    obs = datetime(2026, 9, 10, tzinfo=timezone.utc)
    travel = date(2026, 9, 11)
    days, window = _calc_advance(travel, obs)
    assert days == 1
    assert window == "T+1"


def test_advance_days_t7():
    obs = datetime(2026, 9, 10, tzinfo=timezone.utc)
    travel = date(2026, 9, 17)
    days, window = _calc_advance(travel, obs)
    assert days == 7
    assert window == "T+7"


def test_advance_days_t15():
    obs = datetime(2026, 9, 1, tzinfo=timezone.utc)
    travel = date(2026, 9, 16)
    days, window = _calc_advance(travel, obs)
    assert days == 15
    assert window == "T+15"


def test_advance_days_t30():
    obs = datetime(2026, 8, 11, tzinfo=timezone.utc)
    travel = date(2026, 9, 10)
    days, window = _calc_advance(travel, obs)
    assert days == 30
    assert window == "T+30"


def test_advance_days_t45():
    obs = datetime(2026, 7, 27, tzinfo=timezone.utc)
    travel = date(2026, 9, 10)
    days, window = _calc_advance(travel, obs)
    assert days == 45
    assert window == "T+45"


def test_advance_days_non_window():
    """Days that don't match a window → window is None."""
    obs = datetime(2026, 9, 7, tzinfo=timezone.utc)
    travel = date(2026, 9, 10)
    days, window = _calc_advance(travel, obs)
    assert days == 3
    assert window is None


def test_advance_days_past_travel():
    """Travel date in the past → returns None, None."""
    obs = datetime(2026, 9, 15, tzinfo=timezone.utc)
    travel = date(2026, 9, 10)
    days, window = _calc_advance(travel, obs)
    assert days is None
    assert window is None


# ---------------------------------------------------------------------------
# persist_observations tests (mocked DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_persist_single_flight():
    """Successful normalized fare gets stored."""
    flight = make_flight()
    params = make_params()

    mock_conn = AsyncMock()
    mock_conn.executemany = AsyncMock(return_value=None)
    mock_conn.close = AsyncMock()

    with patch("app.services.persistence.settings") as mock_settings, \
         patch("asyncpg.connect", return_value=mock_conn):
        mock_settings.database_url = "postgresql://fake"
        n = await persist_observations([flight], params, data_type="LIVE")

    assert n == 1
    mock_conn.executemany.assert_called_once()


@pytest.mark.asyncio
async def test_persist_multiple_flights():
    """Multiple flights create multiple observations."""
    flights = [make_flight(id=f"id-{i}", flight_number=f"6E{100+i}") for i in range(5)]
    params = make_params()

    mock_conn = AsyncMock()
    mock_conn.executemany = AsyncMock(return_value=None)
    mock_conn.close = AsyncMock()

    with patch("app.services.persistence.settings") as mock_settings, \
         patch("asyncpg.connect", return_value=mock_conn):
        mock_settings.database_url = "postgresql://fake"
        n = await persist_observations(flights, params, data_type="LIVE")

    assert n == 5


@pytest.mark.asyncio
async def test_persist_empty_flights():
    """Empty flight list → zero observations, no DB call."""
    params = make_params()

    with patch("asyncpg.connect") as mock_connect:
        n = await persist_observations([], params, data_type="LIVE")

    assert n == 0
    mock_connect.assert_not_called()


@pytest.mark.asyncio
async def test_persist_live_data_type():
    """LIVE observations have data_type=LIVE passed to DB."""
    flight = make_flight()
    params = make_params()
    captured_rows = []

    mock_conn = AsyncMock()

    async def capture_executemany(sql, rows):
        captured_rows.extend(rows)

    mock_conn.executemany = capture_executemany
    mock_conn.close = AsyncMock()

    with patch("app.services.persistence.settings") as mock_settings, \
         patch("asyncpg.connect", return_value=mock_conn):
        mock_settings.database_url = "postgresql://fake"
        await persist_observations([flight], params, data_type="LIVE")

    # data_type is $21 (index 20 in 0-based)
    assert captured_rows[0][20] == "LIVE"


@pytest.mark.asyncio
async def test_persist_mock_data_type():
    """MOCK observations have data_type=MOCK."""
    flight = make_flight()
    params = make_params()
    captured_rows = []

    mock_conn = AsyncMock()

    async def capture_executemany(sql, rows):
        captured_rows.extend(rows)

    mock_conn.executemany = capture_executemany
    mock_conn.close = AsyncMock()

    with patch("app.services.persistence.settings") as mock_settings, \
         patch("asyncpg.connect", return_value=mock_conn):
        mock_settings.database_url = "postgresql://fake"
        await persist_observations([flight], params, data_type="MOCK")

    assert captured_rows[0][20] == "MOCK"


@pytest.mark.asyncio
async def test_persist_no_database_url():
    """If DATABASE_URL is empty, skip silently and return 0."""
    flight = make_flight()
    params = make_params()

    with patch("app.services.persistence.settings") as mock_settings, \
         patch("asyncpg.connect") as mock_connect:
        mock_settings.database_url = ""
        n = await persist_observations([flight], params, data_type="LIVE")

    assert n == 0
    mock_connect.assert_not_called()


@pytest.mark.asyncio
async def test_persist_db_failure_returns_zero():
    """DB failure is caught, returns 0, does not raise."""
    flight = make_flight()
    params = make_params()

    with patch("app.services.persistence.settings") as mock_settings, \
         patch("asyncpg.connect", side_effect=Exception("connection refused")):
        mock_settings.database_url = "postgresql://fake"
        n = await persist_observations([flight], params, data_type="LIVE")

    assert n == 0


@pytest.mark.asyncio
async def test_persist_advance_days_in_row():
    """advance_purchase_days is calculated correctly in the DB row."""
    # Travel on 2026-09-17, observed on 2026-09-10 → 7 days
    flight = make_flight()
    params = make_params(departure_date=date(2026, 9, 17))
    captured_rows = []

    mock_conn = AsyncMock()

    async def capture_executemany(sql, rows):
        captured_rows.extend(rows)

    mock_conn.executemany = capture_executemany
    mock_conn.close = AsyncMock()

    obs_time = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)

    with patch("app.services.persistence.settings") as mock_settings, \
         patch("asyncpg.connect", return_value=mock_conn), \
         patch("app.services.persistence.datetime") as mock_dt:
        mock_dt.now.return_value = obs_time
        mock_settings.database_url = "postgresql://fake"
        await persist_observations([flight], params, data_type="LIVE")

    # advance_purchase_days is $18 (index 17), advance_window is $19 (index 18)
    assert captured_rows[0][17] == 7
    assert captured_rows[0][18] == "T+7"
