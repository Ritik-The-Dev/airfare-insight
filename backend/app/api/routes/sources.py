from __future__ import annotations

from fastapi import APIRouter

from app.schemas.search import SourceSummary
from app.services.search_orchestrator import _DISPLAY_SOURCES, get_job, _jobs

router = APIRouter()

_SOURCE_DEFAULTS = {s.name: s.type for s in _DISPLAY_SOURCES}


@router.get("/sources", response_model=list[SourceSummary])
async def get_sources() -> list[SourceSummary]:
    """
    Return all configured data sources with their last-known status.
    Falls back to "unavailable" for sources never queried.
    """
    latest: dict[str, SourceSummary] = {}

    for job in _jobs.values():
        if job.status != "completed":
            continue
        for source in job.sources:
            existing = latest.get(source.name)
            if existing is None:
                latest[source.name] = source
            else:
                if source.status == "live" and existing.status != "live":
                    latest[source.name] = source
                elif (
                    source.last_successful_fetch
                    and existing.last_successful_fetch
                    and source.last_successful_fetch > existing.last_successful_fetch
                ):
                    latest[source.name] = source

    result: list[SourceSummary] = []
    for name, source_type in _SOURCE_DEFAULTS.items():
        if name in latest:
            result.append(latest[name])
        else:
            result.append(SourceSummary(name=name, type=source_type, status="unavailable"))

    return result
