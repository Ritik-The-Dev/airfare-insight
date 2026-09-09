# Airfare Insight

Build a production-quality web application prototype for Smart India Hackathon problem statement:

SIH26056 — GREEN · Strong Pick

“Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator Portals for Augmentation of the Consumer Price Index (CPI).”

==================================================

CORE SCOPE

==================================================

For this prototype, focus ONLY on:

REAL-TIME AIRFARE SEARCH + SCRAPING + NORMALIZATION + COMPARISON.

Do NOT implement:

- CPI calculation

- 30-day backtesting

- DGCA historical comparison

- statistical testing

- advanced airfare index construction

- user authentication

- payments

- flight booking

The core demonstration is:

USER ENTERS ROUTE + DATE

        ↓

BACKEND SCRAPES MULTIPLE SOURCES IN PARALLEL

        ↓

REAL LIVE FARES ARE EXTRACTED

        ↓

DATA IS NORMALIZED

        ↓

USER SEES A FAST, CLEAN COMPARISON

==================================================

TECH STACK — IMPORTANT

==================================================

FRONTEND:

- React

- TypeScript

- Tailwind CSS

- shadcn/ui where appropriate

BACKEND:

- PYTHON ONLY

Use:

- FastAPI for REST API

- Playwright Python for browser automation

- BeautifulSoup4 / lxml for HTML parsing where appropriate

- asyncio for concurrent scraping

- Pydantic for request/response models

- httpx for normal HTTP requests where browser automation is unnecessary

- Redis for short-lived caching if available

- PostgreSQL/Supabase for persistence if required

DO NOT use:

- Node.js backend

- Express

- NestJS

- Java backend

The React frontend communicates with the Python FastAPI backend through REST APIs.

==================================================

ARCHITECTURE

==================================================

Use this architecture:

React Frontend

       ↓

FastAPI API

       ↓

Search Orchestrator

       ↓

┌──────────────┬──────────────┬──────────────┐

│              │              │              │

IndiGo       Air India      Akasa        SpiceJet

Scraper      Scraper        Scraper        Scraper

│              │              │              │

└──────────────┴──────────────┴──────────────┘

             +

┌──────────────┬──────────────┬──────────────┐

│              │              │              │

MakeMyTrip   Cleartrip     EaseMyTrip      ixigo

Scraper      Scraper        Scraper        Scraper

│              │              │              │

└──────────────┴──────────────┴──────────────┘

       ↓

Normalized FlightResult

       ↓

FastAPI

       ↓

React UI

IMPORTANT:

Scraping MUST happen server-side.

Never run Playwright in the browser.

==================================================

REAL DATA — ABSOLUTE REQUIREMENT

==================================================

The application MUST use real airfare data.

DO NOT use dummy prices in the real search flow.

Never create fake values such as:

₹4,999

₹5,299

₹6,149

just to populate the UI.

If a scraper fails:

status = "unavailable"

If a website blocks automation:

status = "blocked"

If there are no flights:

status = "no_results"

If the scraper times out:

status = "timeout"

NEVER replace failed data with fake data.

The UI must clearly communicate which sources actually returned live results.

==================================================

PYTHON BACKEND STRUCTURE

==================================================

Create a clean Python backend structure similar to:

backend/

    app/

        main.py

        api/

            routes/

                flights.py

                sources.py

        models/

            flight.py

            search.py

            source.py

        schemas/

            flight.py

            search.py

        services/

            search_orchestrator.py

            normalization.py

            cache.py

        scrapers/

            base.py

            airlines/

                indigo.py

                air_india.py

                akasa.py

                spicejet.py

            ota/

                makemytrip.py

                cleartrip.py

                easemytrip.py

                ixigo.py

        utils/

            dates.py

            currency.py

            logging.py

    requirements.txt

    .env.example

==================================================

SCRAPER INTERFACE

==================================================

Every scraper must implement the same interface.

Example:

class BaseFlightScraper:

    async def search(

        self,

        params: FlightSearchParams

    ) -> list[FlightResult]:

        ...

Each source gets its own implementation.

Example:

class IndigoScraper(BaseFlightScraper):

    async def search(self, params):

        ...

class AirIndiaScraper(BaseFlightScraper):

    async def search(self, params):

        ...

etc.

The rest of the application should NOT care how an individual source works.

==================================================

SCRAPER SOURCES

==================================================

Create adapters for:

AIRLINES:

1. IndiGo

2. Air India

3. Akasa Air

4. SpiceJet

OTA:

5. MakeMyTrip

6. Cleartrip

7. EaseMyTrip

8. ixigo

IMPORTANT:

Do not falsely claim a scraper is functional if the target website currently prevents automated access.

Build the adapter architecture properly.

If a source cannot be accessed during deployment/demo, return:

{

    "source": "MakeMyTrip",

    "status": "unavailable",

    "error": "Unable to retrieve live results"

}

while continuing with other sources.

==================================================

PARALLEL SCRAPING

==================================================

This is extremely important.

NEVER do:

await indigo.search()

await airindia.search()

await akasa.search()

await spicejet.search()

because that makes the search unnecessarily slow.

Use Python asyncio.

Example architecture:

results = await asyncio.gather(

    indigo.search(params),

    airindia.search(params),

    akasa.search(params),

    spicejet.search(params),

    makemytrip.search(params),

    cleartrip.search(params),

    easemytrip.search(params),

    ixigo.search(params),

    return_exceptions=True

)

Use per-source timeouts.

For example:

asyncio.wait_for(

    scraper.search(params),

    timeout=8

)

One failed scraper must NEVER stop the others.

==================================================

PROGRESSIVE RESULTS

==================================================

Do not force the user to wait for every scraper before showing anything.

Implement a mechanism where source status can update progressively.

Possible approach:

POST /api/flights/search

creates a search job.

Return:

{

    "search_id": "abc123",

    "status": "searching"

}

Then:

GET /api/flights/search/{search_id}

returns current state.

Example:

{

    "status": "searching",

    "sources": [

        {

            "name": "IndiGo",

            "status": "completed",

            "result_count": 6

        },

        {

            "name": "Air India",

            "status": "searching"

        },

        {

            "name": "MakeMyTrip",

            "status": "unavailable"

        }

    ],

    "flights": [...]

}

The frontend should update as results arrive.

==================================================

FAST PERFORMANCE

==================================================

Target a useful first result within approximately:

5–10 seconds

Optimize aggressively.

Use:

- asyncio

- concurrent scraping

- connection reuse

- short browser timeouts

- efficient selectors

- network interception when appropriate

- caching

- minimal page waits

Avoid:

page.wait_for_timeout(10000)

unless absolutely necessary.

Prefer:

wait_for_selector()

or waiting for a relevant network response.

Do not load unnecessary assets when possible.

==================================================

NORMALIZED DATA MODEL

==================================================

All scrapers must return the same structure.

Use Pydantic:

class FlightResult(BaseModel):

    id: str

    source: str

    airline: str

    flight_number: str | None

    origin: str

    destination: str

    departure_time: datetime

    arrival_time: datetime

    duration_minutes: int

    stops: int

    cabin_class: str

    base_fare: float | None

    taxes: float | None

    fees: float | None

    total_fare: float

    currency: str

    baggage: str | None

    booking_url: str | None

    scraped_at: datetime

    status: str

The frontend should ONLY consume this normalized structure.

==================================================

PRICE HANDLING

==================================================

Where possible:

total_fare =

base_fare + taxes + fees

But NEVER manufacture missing values.

If only total fare is available:

base_fare = null

taxes = null

fees = null

Display only:

Total fare

₹X,XXX

If the source explicitly provides a fare breakdown:

Base fare

Taxes

Fees

Total

Always distinguish:

"Fare retrieved from source"

from:

"Fare estimated"

For this prototype, prefer showing only actual retrieved totals.

==================================================

SOURCE STATUS

==================================================

Every source must have a status:

SEARCHING

LIVE

UNAVAILABLE

TIMEOUT

BLOCKED

NO_RESULTS

ERROR

Example UI:

LIVE SOURCES

● IndiGo

Live · 4 results

● Air India

Live · 7 results

● MakeMyTrip

Live · 12 results

● Cleartrip

Unavailable

This makes the project much more credible during the SIH demonstration.

==================================================

FRONTEND — PRODUCT EXPERIENCE

==================================================

Application name:

FareLens

Tagline:

“Live airfare. One clear view.”

The website should NOT look like a generic AI-generated SaaS dashboard.

Avoid:

- huge gradients

- purple/blue AI gradients

- excessive glassmorphism

- glowing cards

- floating blobs

- unnecessary illustrations

- excessive rounded containers

- excessive animations

- generic “AI-powered” language

Design direction:

PREMIUM

CALM

EDITORIAL

DATA-DRIVEN

TRUSTWORTHY

FAST

Think:

premium travel product + financial-data clarity.

==================================================

HOMEPAGE

==================================================

Header:

FareLens

Navigation:

Search

How it works

Sources

Right side:

● Live data

Main headline:

“Know the fare before you book.”

Supporting copy:

“Compare live airfare across airlines and travel platforms in one place.”

Then a prominent search interface.

==================================================

SEARCH FORM

==================================================

Create:

FROM

TO

SWAP

DEPARTURE

RETURN

PASSENGERS

CABIN

SEARCH LIVE FARES

Airport autocomplete should support:

city

airport name

IATA code

Examples:

Delhi

DEL — Indira Gandhi International Airport

Mumbai

BOM — Chhatrapati Shivaji Maharaj International Airport

Bengaluru

BLR — Kempegowda International Airport

Hyderabad

HYD — Rajiv Gandhi International Airport

Chennai

MAA — Chennai International Airport

Kolkata

CCU — Netaji Subhas Chandra Bose International Airport

==================================================

SEARCH LOADING EXPERIENCE

==================================================

When user searches:

DO NOT show a generic spinner.

Show:

FETCHING LIVE FARES

Then:

✓ IndiGo

   6 flights found

✓ Air India

   4 flights found

⟳ MakeMyTrip

   Searching...

⟳ Cleartrip

   Searching...

— SpiceJet

   Unavailable

Results should appear progressively.

==================================================

RESULTS PAGE

==================================================

Show:

DEL → BOM

12 September 2026

1 Passenger

Economy

Then:

LIVE FARES

“Prices retrieved moments ago”

Show:

Cheapest

Fastest

Best Value

==================================================

PRICE COMPARISON

==================================================

At the top:

LOWEST LIVE FARE

₹5,180

IndiGo

Non-stop

2h 10m

MakeMyTrip

● Live · 8 sec ago

Then show all available flights.

==================================================

FLIGHT CARD

==================================================

Each card:

AIRLINE

Flight number

DEPARTURE

10:30

DEL

↓

2h 10m

Non-stop

↓

ARRIVAL

12:40

BOM

PRICE

₹5,180

Source:

MakeMyTrip

● Live · 8 sec ago

Button:

VIEW DEAL

If no booking URL exists:

do not show a fake booking link.

==================================================

COMPARISON VIEW

==================================================

Provide a compact source comparison:

LIVE PRICE COMPARISON

IndiGo        ₹5,240

Air India     ₹5,680

Akasa Air     ₹5,910

MakeMyTrip    ₹5,180

Cleartrip     Unavailable

Use actual backend values.

Do not show fake values.

==================================================

FILTERS

==================================================

Filters:

Airline

Stops

Price

Departure time

Arrival time

Source

Sorting:

Cheapest

Fastest

Best value

Earliest departure

==================================================

DATA FRESHNESS

==================================================

Every result must show when it was retrieved.

Examples:

● Live · 5 sec ago

● Live · 32 sec ago

Retrieved 2 minutes ago

Never pretend cached data is live.

Add:

REFRESH LIVE FARES

button.

==================================================

SOURCE PAGE

==================================================

Create:

/sources

Show:

Source

Type

Current Status

Last successful fetch

Response time

Example:

IndiGo

Airline

Live

Air India

Airline

Live

MakeMyTrip

OTA

Live

etc.

==================================================

SIH DEMO PANEL

==================================================

Create a developer/demo status panel accessible from a small “System Status” button.

Show:

Search ID

Sources queried

Successful sources

Failed sources

Total flights

Total search time

Example:

LIVE SEARCH

Completed in 6.7 seconds

8 sources queried

6 successful

2 unavailable

34 flights retrieved

This should be visually impressive but not visible as technical clutter to normal users.

==================================================

ERROR HANDLING

==================================================

If one scraper fails:

“Air India couldn't return live results right now.”

Continue showing other sources.

If all fail:

“Live fares couldn't be retrieved right now.

Please try again.”

NEVER show mock data.

==================================================

CACHE

==================================================

Use short-lived caching.

Suggested TTL:

30–60 seconds.

Cache key:

origin

destination

departure date

return date

passengers

cabin class

Show cache age clearly.

Example:

“Retrieved 31 seconds ago”

Provide:

Refresh live fares

==================================================

API ENDPOINTS

==================================================

Create:

POST /api/flights/search

GET /api/flights/search/{search_id}

GET /api/sources

GET /api/health

GET /api/flights/{search_id}

Use FastAPI with automatic OpenAPI documentation.

==================================================

ENVIRONMENT

==================================================

Create:

.env.example

Include appropriate variables such as:

DATABASE_URL=

REDIS_URL=

PLAYWRIGHT_HEADLESS=true

SCRAPER_TIMEOUT=8000

CACHE_TTL=60

DEMO_MODE=false

IMPORTANT:

DEMO_MODE must default to FALSE.

The application must never silently switch to fake data.

==================================================

DOCKER

==================================================

Create Docker configuration for the Python backend.

Ensure Playwright browser dependencies can be installed correctly.

Include:

requirements.txt

and appropriate setup instructions.

==================================================

LOGGING

==================================================

Backend should log:

search_id

source

start time

end time

duration

result count

error status

Example:

[search abc123]

IndiGo completed in 2.4s — 6 results

[search abc123]

Air India completed in 4.1s — 8 results

[search abc123]

MakeMyTrip timeout after 8s

Do not expose sensitive internal logs to users.

==================================================

ETHICAL / RESPONSIBLE SCRAPING

==================================================

The scraper architecture should:

- respect robots.txt where applicable

- respect website terms and access policies

- use reasonable request rates

- avoid unnecessary requests

- use caching

- avoid aggressive scraping

- avoid bypassing CAPTCHA or access controls

- never attempt to defeat anti-bot systems

If a source blocks access, mark it unavailable.

==================================================

FINAL UI QUALITY

==================================================

The final result must feel like a serious product suitable for an SIH presentation.

It should NOT feel like:

“Lovable generated a dashboard.”

It should feel like:

“A real Indian airfare intelligence product.”

Visual qualities:

- restrained

- premium

- clean

- highly readable

- excellent spacing

- subtle borders

- strong typography

- minimal shadows

- very limited animation

- excellent mobile experience

The most important visual element is the LIVE PRICE COMPARISON.

==================================================

FINAL PRIORITIES

==================================================

Priority 1:

REAL SCRAPED AIRFARE

Priority 2:

MULTIPLE SOURCES

Priority 3:

PYTHON FASTAPI BACKEND

Priority 4:

PLAYWRIGHT SCRAPING

Priority 5:

PARALLEL ASYNC EXECUTION

Priority 6:

FAST RESULTS

Priority 7:

NORMALIZED DATA

Priority 8:

SOURCE TRANSPARENCY

Priority 9:

EXCELLENT UX

Priority 10:

SIH DEMONSTRATION / SYSTEM STATUS

Do not sacrifice real data for visual polish.

The application should be honest:

If real data exists → show it.

If a source fails → show unavailable.

If no source works → show an error.

NEVER fabricate a price.

                 FastAPI

                    │

             Search Orchestrator

                    │

          ┌─────────┼─────────┐

          ↓         ↓         ↓

       IndiGo    Air India   OTA

       scraper    scraper   scraper

          │         │         │

          └─────────┼─────────┘

                    ↓

             Normalization

                    ↓

             Price Comparison

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/7c604a15-efdd-4a46-8b62-2bb2d92e2079).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
