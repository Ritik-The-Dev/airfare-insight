from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.flight import FlightResult
from app.schemas.search import FlightSearchParams


# Shared browser-like headers for Playwright contexts
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}


class ScraperUnavailableError(Exception):
    """
    Raised by a scraper when it cannot return real flight data.

    This covers: navigation timeouts, CAPTCHA walls, bot-detection blocks,
    empty/unparseable responses, and any other retrieval failure.

    The orchestrator catches this and marks the source with an appropriate
    status (timeout / blocked / unavailable / error) — it never substitutes
    fake data.
    """

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        self.reason = reason
        super().__init__(f"{source}: {reason}")


class BaseFlightScraper(ABC):
    """Abstract base for all airline and OTA scrapers."""

    source_name: str  # human-readable name, e.g. "IndiGo"
    source_type: str  # "Airline" or "OTA"

    @abstractmethod
    async def search(self, params: FlightSearchParams) -> list[FlightResult]:
        """
        Attempt to retrieve live flights for the given search parameters.

        Returns a list of FlightResult objects on success.
        Raises ScraperUnavailableError on any failure.
        """
        ...
