from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.flights import router as flights_router
from app.api.routes.index_data import router as index_data_router
from app.api.routes.observations import router as observations_router
from app.api.routes.sources import router as sources_router
from app.models.config import settings

# ---------------------------------------------------------------------------
# Configure root logging level from settings
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="FareLens API",
    version="1.0.0",
    description=(
        "Real-time airfare comparison backend for FareLens. "
        "Scrapes 4 Indian airlines and 4 OTAs in parallel."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS — allow all origins in development (prototype/SIH demo)
# For production, restrict to specific origins via CORS_ORIGINS env var.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(flights_router, prefix="/api")
app.include_router(sources_router, prefix="/api")
app.include_router(observations_router, prefix="/api")
app.include_router(index_data_router, prefix="/api")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "service": "farelens-api"}
