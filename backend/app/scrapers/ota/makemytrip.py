"""
MakeMyTrip scraper — Playwright + network interception.
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


class MakeMyTripScraper(BaseFlightScraper):
    source_name = "MakeMyTrip"
    source_type = "OTA"

    async def search(self, params: FlightSearchParams) -> list[FlightResult]:
        dep = params.departure_date.strftime("%m%d%Y")  # MMT uses MMDDYYYY in deep links
        url = (
            f"https://www.makemytrip.com/flight/search"
            f"?itinerary={params.origin}-{params.destination}-{dep}"
            f"&tripType=O&paxType=A-{params.passengers}_C-0_I-0"
            f"&intl=false&cabinClass=E&lang=eng"
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
                if any(k in r.url for k in ("listing", "search", "flight", "FLIGHTS")):
                    try:
                        if "json" in r.headers.get("content-type", ""):
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

        # MMT nests airline info in sI segments
        si = item.get("sI", [])
        airline = "Unknown"
        fn = None
        if si and isinstance(si, list) and isinstance(si[0], dict):
            al = si[0].get("al", {})
            airline = al.get("alN") or al.get("name") or "Unknown"
            fd = si[0].get("fD", {})
            fn = fd.get("fN") or fd.get("flightNumber")
        airline = airline or item.get("airlineName") or item.get("airline") or "Unknown"
        fn = fn or item.get("flightNumber") or item.get("flight_number")
        stops = max(0, len(si) - 1) if si else _int(item, "stops", "stopCount")

        results.append(FlightResult(
            id=str(uuid.uuid4()),
            source="MakeMyTrip", airline=str(airline),
            flight_number=str(fn) if fn else None,
            origin=params.origin, destination=params.destination,
            departure_time=dep_dt, arrival_time=arr_dt,
            duration_minutes=duration_minutes(dep_dt, arr_dt),
            stops=stops,
            cabin_class=params.cabin_class,
            total_fare=fare, currency="INR",
            scraped_at=scraped_at, status="live",
        ))
    return results


def _find_list(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return None
    for path in (
        ("data", "listData"), ("data", "flights"), ("listData",),
        ("flights",), ("results",), ("flightResults",), ("itineraries",), ("data",),
    ):
        node = data
        for k in path:
            node = node.get(k) if isinstance(node, dict) else None
        if isinstance(node, list):
            return node
    return None


def _fare(item):
    # MMT: totalPriceList[0].fd.ADULT.fC.TF
    tpl = item.get("totalPriceList")
    if isinstance(tpl, list) and tpl:
        try:
            tf = tpl[0]["fd"]["ADULT"]["fC"]["TF"]
            return float(tf)
        except (KeyError, TypeError, ValueError, IndexError):
            pass
    for k in ("totalFare", "totalAmount", "totalPrice", "fare", "price"):
        v = item.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def _times(item, params):
    si = item.get("sI", [])
    if si and isinstance(si, list):
        dep = si[0].get("dt") if isinstance(si[0], dict) else None
        arr = si[-1].get("at") if isinstance(si[-1], dict) else None
        if dep and arr:
            d = _parse_dt(str(dep), params.departure_date)
            a = _parse_dt(str(arr), params.departure_date)
            if d and a:
                if a <= d:
                    a += timedelta(days=1)
                return d, a
    dep = item.get("departureTime") or item.get("depTime") or item.get("departure")
    arr = item.get("arrivalTime") or item.get("arrTime") or item.get("arrival")
    if not dep or not arr:
        return None, None
    d, a = _parse_dt(str(dep), params.departure_date), _parse_dt(str(arr), params.departure_date)
    if d and a and a <= d:
        a += timedelta(days=1)
    return d, a


def _parse_dt(s, base):
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


def _int(item, *keys):
    for k in keys:
        v = item.get(k)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    return 0
