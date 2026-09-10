"""
FareLens mock data seeder.

Generates ~30 days of synthetic MOCK fare observations for representative
Indian domestic routes. Safe to run multiple times — uses ON CONFLICT DO NOTHING.

IMPORTANT:
  Every record has data_type = 'MOCK'.
  This is synthetic data for prototype/demo purposes only.
  It is NOT official historical airfare data.
  It is NOT used to claim official CPI statistics.

Usage:
    cd backend
    python seed_mock_data.py
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL is not set. Add it to backend/.env")
    sys.exit(1)

import asyncpg  # noqa: E402 — after dotenv load

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROUTES: dict[str, dict] = {
    "DEL-BOM": {
        "origin": "DEL", "destination": "BOM",
        "airlines": {
            "IndiGo": 5200, "Air India": 5800, "SpiceJet": 4900, "Akasa Air": 5100,
        },
        "duration_minutes": {"IndiGo": 130, "Air India": 135, "SpiceJet": 125, "Akasa Air": 132},
    },
    "DEL-BLR": {
        "origin": "DEL", "destination": "BLR",
        "airlines": {
            "IndiGo": 4800, "Air India": 5400, "Air India Express": 4600,
        },
        "duration_minutes": {"IndiGo": 165, "Air India": 170, "Air India Express": 168},
    },
    "BOM-BLR": {
        "origin": "BOM", "destination": "BLR",
        "airlines": {
            "IndiGo": 3800, "SpiceJet": 3600, "Akasa Air": 3700,
        },
        "duration_minutes": {"IndiGo": 85, "SpiceJet": 88, "Akasa Air": 86},
    },
    "DEL-HYD": {
        "origin": "DEL", "destination": "HYD",
        "airlines": {
            "IndiGo": 4200, "Air India": 4700, "SpiceJet": 4000,
        },
        "duration_minutes": {"IndiGo": 145, "Air India": 150, "SpiceJet": 148},
    },
    "DEL-MAA": {
        "origin": "DEL", "destination": "MAA",
        "airlines": {
            "IndiGo": 4600, "Air India": 5200, "Air India Express": 4400,
        },
        "duration_minutes": {"IndiGo": 170, "Air India": 175, "Air India Express": 172},
    },
    "BOM-DEL": {
        "origin": "BOM", "destination": "DEL",
        "airlines": {
            "IndiGo": 5100, "Air India": 5700, "SpiceJet": 4800, "Akasa Air": 5000,
        },
        "duration_minutes": {"IndiGo": 130, "Air India": 135, "SpiceJet": 128, "Akasa Air": 132},
    },
}

ADVANCE_WINDOW_MAP = {1: "T+1", 7: "T+7", 15: "T+15", 30: "T+30", 45: "T+45"}

INSERT_SQL = """
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
RETURNING id
"""


def _price_for(base: int, advance_days: int, rng: random.Random) -> float:
    """
    Calculate a realistic mock fare.
    T+1 tends to be 20-30% more expensive than T+30, with ±8% noise.
    """
    # Advance-purchase multiplier — later bookings are cheaper, with variation
    if advance_days <= 1:
        multiplier = rng.uniform(1.18, 1.32)
    elif advance_days <= 7:
        multiplier = rng.uniform(1.10, 1.22)
    elif advance_days <= 15:
        multiplier = rng.uniform(1.02, 1.14)
    elif advance_days <= 30:
        multiplier = rng.uniform(0.92, 1.05)
    else:
        multiplier = rng.uniform(0.85, 0.98)

    # Add day-of-week variation (weekends slightly pricier)
    noise = rng.uniform(0.93, 1.08)
    price = base * multiplier * noise
    return round(price / 10) * 10  # round to nearest 10


def _det_seed(route: str, airline: str, obs_date: date, travel_date: date) -> int:
    """Deterministic seed so same inputs always produce same price."""
    key = f"{route}|{airline}|{obs_date}|{travel_date}"
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**32)


def _flight_number(airline: str, route: str, travel_date: date) -> str:
    prefixes = {
        "IndiGo": "6E", "Air India": "AI", "Air India Express": "IX",
        "SpiceJet": "SG", "Akasa Air": "QP",
    }
    prefix = prefixes.get(airline, "FL")
    # Deterministic number from route + date
    num = int(hashlib.md5(f"{route}{travel_date}".encode()).hexdigest(), 16) % 900 + 100
    return f"{prefix}{num}"


async def seed(conn: asyncpg.Connection) -> tuple[int, int]:
    today = date.today()
    start_date = today - timedelta(days=30)

    rows_to_insert = []

    for obs_date_offset in range(30):
        obs_date = start_date + timedelta(days=obs_date_offset)
        # Each observed day has flights for several advance-purchase windows
        for adv_days in (1, 7, 15, 30, 45):
            travel_date = obs_date + timedelta(days=adv_days)
            if travel_date >= today:
                continue  # skip future travel dates

            for route, route_cfg in ROUTES.items():
                for airline, base_price in route_cfg["airlines"].items():
                    rng = random.Random(_det_seed(route, airline, obs_date, travel_date))
                    price = _price_for(base_price, adv_days, rng)

                    # Use midday UTC as observed_at for mock data
                    observed_at = datetime(
                        obs_date.year, obs_date.month, obs_date.day,
                        10, 30, 0, tzinfo=timezone.utc,
                    )
                    adv_window = ADVANCE_WINDOW_MAP.get(adv_days)
                    flight_number = _flight_number(airline, route, travel_date)
                    duration = route_cfg["duration_minutes"].get(airline, 120)

                    # Approximate base/taxes split (60/40)
                    base_fare = round(price * 0.60 / 10) * 10
                    taxes = round(price * 0.30 / 10) * 10
                    fees = price - base_fare - taxes

                    rows_to_insert.append((
                        observed_at,
                        travel_date,
                        route_cfg["origin"],
                        route_cfg["destination"],
                        route,
                        airline,
                        flight_number,
                        airline,          # source = airline name for mock data
                        float(price),
                        "INR",
                        float(base_fare),
                        float(taxes),
                        float(fees),
                        0,                # stops (non-stop)
                        duration,
                        "economy",
                        1,                # passengers
                        adv_days,
                        adv_window,
                        "available",
                        "MOCK",
                        None,             # booking_url
                    ))

    # Insert in batches
    inserted = 0
    skipped = 0
    batch_size = 100

    for i in range(0, len(rows_to_insert), batch_size):
        batch = rows_to_insert[i: i + batch_size]
        results = await conn.executemany(INSERT_SQL, batch)
        # executemany with RETURNING isn't trivially countable via executemany
        # Use execute per row for accurate counting
        inserted += len(batch)  # approximate; conflicts silently skipped

    return inserted, skipped


async def main() -> None:
    print("Connecting to database...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        sys.exit(1)

    try:
        print("Seeding mock fare observations...")
        inserted, _ = await seed(conn)
        print(f"\nDone. Attempted {inserted} mock observations (duplicates silently skipped).")
        print("\nIMPORTANT: All seeded records have data_type=MOCK.")
        print("This is synthetic data for prototype/demo purposes only.")
        print("It is NOT official historical airfare data.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
