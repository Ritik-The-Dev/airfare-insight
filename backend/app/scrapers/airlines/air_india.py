"""
Air India scraper — Playwright + network interception.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
import re

from playwright.async_api import async_playwright, Response

from app.models.config import settings
from app.scrapers.base import BaseFlightScraper, ScraperUnavailableError
from app.schemas.flight import FlightResult
from app.schemas.search import FlightSearchParams
from app.utils.dates import duration_minutes


class AirIndiaScraper(BaseFlightScraper):
    source_name = "Air India"
    source_type = "Airline"

    async def search(self, params: FlightSearchParams) -> list[FlightResult]:
        dep = params.departure_date.strftime("%Y-%m-%d")
        url = (
            f"https://www.airindia.com/in/en/book/flight-search.html"
            f"?tripType=O&from={params.origin}&to={params.destination}"
            f"&departDate={dep}&adult={params.passengers}&child=0&infant=0&cabinClass=E"
        )

        captured: list[dict] = []
        timeout_ms = settings.scraper_timeout * 1000

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=settings.playwright_headless)
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="en-IN",
            )
            page = await ctx.new_page()

            async def handle(r: Response) -> None:
                if any(k in r.url for k in ("search", "availability", "flight", "fare")):
                    try:
                        ct = r.headers.get("content-type", "")
                        if "json" in ct:
                            captured.append(await r.json())
                    except Exception:
                        pass

            page.on("response", lambda r: asyncio.ensure_future(handle(r)))

            try:
                await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            except Exception as e:
                await browser.close()
                raise ScraperUnavailableError(self.source_name, f"Navigation failed: {e}")

            await browser.close()

        for data in captured:
            flights = _parse(data, params)
            if flights:
                return flights

        raise ScraperUnavailableError(self.source_name, "No flight data found in page responses")


def _parse(data: Any, params: FlightSearchParams) -> list[FlightResult]:
    results = []
    scraped_at = datetime.now(tz=timezone.utc)
    raw = _find_list(data)
    if not raw:
        return []
    for item in raw:
        if not isinstance(item, dict):
            continue
        fare = _fare(item)
        if not fare:
            continue
        dep_dt, arr_dt = _times(item, params)
        if not dep_dt or not arr_dt:
            continue
        results.append(FlightResult(
            id=str(uuid.uuid4()),
            source="Air India", airline="Air India",
            flight_number=_str(item, "flightNumber", "flightNo"),
            origin=params.origin, destination=params.destination,
            departure_time=dep_dt, arrival_time=arr_dt,
            duration_minutes=duration_minutes(dep_dt, arr_dt),
            stops=_int(item, "stops", "stopCount"),
            cabin_class=params.cabin_class,
            total_fare=fare, currency="INR",
            scraped_at=scraped_at, status="live",
        ))
    return results


def _find_list(data: Any) -> list | None:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return None
    for path in (
        ("data", "flights"), ("data", "results"), ("flights",),
        ("results",), ("flightResults",), ("itineraries",), ("data",),
    ):
        node = data
        for k in path:
            node = node.get(k) if isinstance(node, dict) else None
        if isinstance(node, list):
            return node
    return None


def _fare(item: dict) -> float | None:
    for k in ("totalFare", "totalAmount", "totalPrice", "fare", "price"):
        v = item.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    for nested in ("fare", "price"):
        sub = item.get(nested)
        if isinstance(sub, dict):
            for k2 in ("totalFare", "total", "TF"):
                v = sub.get(k2)
                if v is not None:
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        pass
    return None


def _times(item: dict, params: FlightSearchParams):
    dep = item.get("departureTime") or item.get("depTime") or item.get("departure")
    arr = item.get("arrivalTime") or item.get("arrTime") or item.get("arrival")
    if not dep or not arr:
        return None, None
    d, a = _parse_dt(str(dep), params.departure_date), _parse_dt(str(arr), params.departure_date)
    if d and a and a <= d:
        a += timedelta(days=1)
    return d, a


def _parse_dt(s: str, base) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        pass
    m = re.search(r"(\d{1,2}):(\d{2})", s)
    if m:
        try:
            return datetime(base.year, base.month, base.day, int(m.group(1)), int(m.group(2)), tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def _str(item, *keys):
    for k in keys:
        v = item.get(k)
        if v:
            return str(v)
    return None


def _int(item, *keys):
    for k in keys:
        v = item.get(k)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    return 0
