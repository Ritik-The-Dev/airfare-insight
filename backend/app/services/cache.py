"""
Simple in-memory cache with TTL for SearchJob results.

Cache key: "{origin}:{destination}:{departure_date}:{return_date}:{passengers}:{cabin_class}"
Thread-safe enough for single-process asyncio use.
"""
from __future__ import annotations

import time
from typing import NamedTuple

from app.models.config import settings
from app.schemas.search import FlightSearchParams, SearchJob


class _CacheEntry(NamedTuple):
    job: SearchJob
    stored_at: float  # time.monotonic()


_cache: dict[str, _CacheEntry] = {}


class SearchCache:
    @staticmethod
    def _make_key(params: FlightSearchParams) -> str:
        return (
            f"{params.origin}:{params.destination}"
            f":{params.departure_date}"
            f":{params.return_date}"
            f":{params.passengers}"
            f":{params.cabin_class}"
        )

    @staticmethod
    def get(params: FlightSearchParams) -> SearchJob | None:
        """Return a cached SearchJob if it exists and has not expired, else None."""
        key = SearchCache._make_key(params)
        entry = _cache.get(key)
        if entry is None:
            return None
        age = time.monotonic() - entry.stored_at
        if age > settings.cache_ttl:
            del _cache[key]
            return None
        # Attach cache_age_seconds to a copy of the job
        cached_job = entry.job.model_copy(
            update={"cache_age_seconds": int(age)}
        )
        return cached_job

    @staticmethod
    def set(params: FlightSearchParams, job: SearchJob) -> None:
        """Store a completed SearchJob in the cache."""
        key = SearchCache._make_key(params)
        _cache[key] = _CacheEntry(job=job, stored_at=time.monotonic())

    @staticmethod
    def clear() -> None:
        """Remove all entries (useful for testing)."""
        _cache.clear()
