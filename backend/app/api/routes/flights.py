from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.search import FlightSearchParams, SearchJob
from app.services.search_orchestrator import get_job, start_search

router = APIRouter()


@router.post("/flights/search", response_model=SearchJob, status_code=202)
async def post_flight_search(params: FlightSearchParams) -> SearchJob:
    """
    Start a new flight search.

    Immediately returns an initial SearchJob with status="searching".
    The client should poll GET /api/flights/search/{search_id} until
    status changes to "completed" or "failed".
    """
    job = await start_search(params)
    return job


@router.get("/flights/search/{search_id}", response_model=SearchJob)
async def get_flight_search(search_id: str) -> SearchJob:
    """
    Poll the current state of a search job.

    Returns the SearchJob including all flights retrieved so far and
    per-source status updates.
    """
    job = get_job(search_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Search job '{search_id}' not found")
    return job


@router.get("/flights/{search_id}", response_model=SearchJob)
async def get_flight_search_alias(search_id: str) -> SearchJob:
    """Alias for GET /api/flights/search/{search_id}."""
    return await get_flight_search(search_id)
