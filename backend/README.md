# FareLens — Python FastAPI Backend

Real-time airfare scraping and comparison engine for the FareLens SIH prototype.

---

## Prerequisites

- Python 3.12+
- pip
- (Optional) Docker

---

## Local setup

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
```

Copy the example env file and adjust as needed:

```bash
cp .env.example .env
```

### Run the dev server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/api/docs`

---

## Connect the frontend

Create a `.env.local` at the **repo root** (next to `package.json`):

```
VITE_API_BASE_URL=http://localhost:8000
```

Then start the frontend:

```bash
npm run dev    # or: bun dev
```

---

## Docker

```bash
# Build
docker build -t farelens-backend .

# Run
docker run -p 8000:8000 --env-file .env farelens-backend
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/flights/search` | Start a search job |
| `GET` | `/api/flights/search/{search_id}` | Poll search job state |
| `GET` | `/api/flights/{search_id}` | Alias for the above |
| `GET` | `/api/sources` | List all sources with last-known status |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/docs` | Swagger UI |

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `PLAYWRIGHT_HEADLESS` | `true` | Run browser headlessly |
| `SCRAPER_TIMEOUT` | `8` | Per-scraper timeout in seconds |
| `CACHE_TTL` | `60` | Search result cache TTL in seconds |
| `DEMO_MODE` | `false` | Must stay false — no fake data injected |
| `LOG_LEVEL` | `INFO` | Python logging level |

---

## A note on scrapers

All eight airline/OTA scrapers make genuine best-effort attempts to retrieve
live fares.  These websites actively deploy bot-detection systems (Akamai,
Cloudflare, CAPTCHA walls).  A scraper that cannot retrieve real data raises
`ScraperUnavailableError` and the orchestrator marks that source with an
honest status (`unavailable`, `blocked`, `timeout`, or `error`).

**No fake fares are ever injected.**  Source-level transparency is the core
value proposition of FareLens.

---

## Project structure

```
backend/
  app/
    main.py                    FastAPI application factory
    models/
      config.py                pydantic-settings Settings class
    schemas/
      flight.py                FlightResult Pydantic model
      search.py                FlightSearchParams, SourceSummary, SearchJob
    scrapers/
      base.py                  BaseFlightScraper + ScraperUnavailableError
      airlines/
        indigo.py              IndiGo (Playwright)
        air_india.py           Air India (Playwright)
        akasa.py               Akasa Air (Playwright + JSON interception)
        spicejet.py            SpiceJet (Playwright)
      ota/
        makemytrip.py          MakeMyTrip (Playwright)
        cleartrip.py           Cleartrip (Playwright + JSON interception)
        easemytrip.py          EaseMyTrip (httpx → Playwright fallback)
        ixigo.py               ixigo (Playwright + JSON interception)
    services/
      search_orchestrator.py   asyncio.gather parallel execution
      normalization.py         Deduplication and sorting
      cache.py                 In-memory TTL cache
    api/
      routes/
        flights.py             POST /search, GET /search/{id}
        sources.py             GET /sources
    utils/
      dates.py                 Date formatting helpers
      currency.py              INR parsing/formatting
      logging.py               Structured logger
```

---

## Supabase / Database Setup

### 1. Create Supabase project
Go to https://supabase.com and create a free project.

### 2. Run migration
In Supabase SQL Editor, paste and run:
`migrations/001_fare_observations.sql`

### 3. Environment variables
Add to `backend/.env`:
```
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
SUPABASE_URL=https://PROJECT.supabase.co
SUPABASE_KEY=your-service-role-key
```

### 4. Seed mock data
```bash
cd backend
python seed_mock_data.py
```
Expected output: `Seeded ~720 mock observations`

### 5. Live observation persistence
Every successful flight search automatically persists LIVE observations to Supabase.
Failed providers are never persisted.

### 6. Query observations
```
GET /api/fare-observations?route=DEL-BOM&data_type=MOCK
GET /api/fare-observations/summary
GET /api/fare-observations/trends?route=DEL-BOM
```

### Data integrity
- LIVE: real fares from providers
- MOCK: synthetic data for prototype/demo only
- Mock data is NOT official historical airfare data
- Mock data is NOT used for official CPI statistics

---

## Supabase / Database Setup

### 1. Create a Supabase project
Go to https://supabase.com and create a free project.

### 2. Run the migration
In the **Supabase SQL Editor**, paste and run the contents of:
```
migrations/001_fare_observations.sql
```

### 3. Get your database password
In Supabase → Project Settings → Database → Connection string (URI mode).
Replace `[YOUR-PASSWORD]` with your actual DB password.

### 4. Set environment variables in `backend/.env`
```
DATABASE_URL=postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_KEY=your-service-role-key
```

### 5. Seed mock data (run once, safe to re-run)
```bash
cd backend
python seed_mock_data.py
```
Expected output: `Attempted ~720 mock observations (duplicates silently skipped)`

### 6. Query observations
```
GET /api/fare-observations?route=DEL-BOM
GET /api/fare-observations?route=DEL-BOM&data_type=MOCK
GET /api/fare-observations/summary
GET /api/fare-observations/trends?route=DEL-BOM
```

---

## Database Schema

Table: `fare_observations`

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique observation ID |
| observed_at | TIMESTAMPTZ | When FareLens retrieved the fare |
| travel_date | DATE | Flight departure date |
| origin | VARCHAR(3) | IATA origin code |
| destination | VARCHAR(3) | IATA destination code |
| route | VARCHAR(7) | e.g. DEL-BOM |
| airline | VARCHAR | Airline name |
| flight_number | VARCHAR | e.g. 6E123 (nullable) |
| source | VARCHAR | Provider/source name |
| price | NUMERIC | Final fare amount |
| currency | VARCHAR | Normally INR |
| base_fare / taxes / fees | NUMERIC | Fare breakdown (nullable) |
| stops | INTEGER | Number of stops |
| duration_minutes | INTEGER | Journey duration (nullable) |
| cabin_class | VARCHAR | economy / business etc. |
| passengers | INTEGER | Search passenger count |
| advance_purchase_days | INTEGER | travel_date − observed_date |
| advance_window | VARCHAR | T+1 / T+7 / T+15 / T+30 / T+45 / NULL |
| availability | VARCHAR | available / unavailable |
| data_type | VARCHAR | **LIVE** or **MOCK** |
| booking_url | TEXT | Provider deep-link (nullable) |
| created_at | TIMESTAMPTZ | DB insertion time |

---

## LIVE vs MOCK Data

| data_type | Meaning |
|-----------|---------|
| LIVE | Real fare retrieved from a live provider during a search |
| MOCK | Synthetic data generated by `seed_mock_data.py` for prototype/demo purposes |

> **Important:** Mock historical observations are synthetic data used only for prototype/demo purposes.
> They are NOT official historical airfare observations and are NOT used to claim official CPI statistics.

---

## How live observations are persisted

Every successful flight search automatically persists LIVE observations to Supabase.
Failed providers are never persisted — no fake fares, no ₹0 placeholders.

The flow is:
```
Search → Ignav API → Normalize → Persist LIVE observations → Return response to frontend
```

If `DATABASE_URL` is not set, persistence is silently skipped and the search works normally.

---

## Run tests
```bash
cd backend
C:\Python313\python.exe -m pytest tests/ -v
```
