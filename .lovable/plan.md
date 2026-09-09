# FareLens — live airfare comparison prototype

## Goal

Replace the starter placeholder with a production-quality FareLens experience for SIH26056: a user enters an Indian route and date, the browser calls a separate Python FastAPI service, that service queries airline and OTA adapters in parallel, and the UI displays only normalized live results or explicit source failure states. No CPI logic, booking flow, authentication, payments, historical analysis, or fabricated fares will be added.

## User experience

1. Build the `/` screen around a calm editorial airfare-search workflow:
   - FareLens identity, “Live airfare. One clear view.”, “Know the fare before you book.”, and navigation to Search, How it works, and Sources.
   - Route fields with airport/city/IATA autocomplete for the requested Indian airports, swap control, departure/return dates, passengers, cabin, and a “Search live fares” action.
   - Clear validation for incomplete or invalid searches.
2. Add a progressive search state:
   - Start a search job, poll its status, and merge source updates as they arrive.
   - Show source-by-source searching, live result counts, unavailable, blocked, timeout, no-results, and error states without substituting sample rows.
   - Keep the user informed with retrieved timestamps, cache age, total search time, and a truthful all-sources-failed message.
3. Add the results experience:
   - Route/date/passenger/cabin summary, lowest live fare highlight, live price comparison by source, and normalized flight cards.
   - Filters for airline, stops, price, departure/arrival windows, and source; sorting for cheapest, fastest, best value, and earliest departure.
   - Fare breakdown only when returned by the source; otherwise show total fare only. Show “View deal” only when a real booking URL exists.
   - Refresh-live-fares action that starts a new job rather than pretending cached data is fresh.
4. Add `/sources` with the eight source adapters, type, current status, last successful fetch, and response time from the API.
5. Add a restrained System Status panel opened by a small button, showing search ID, queried/successful/failed sources, total flights, duration, and per-source details without making normal search feel like a developer console.
6. Add an in-page “How it works” section or navigation target explaining the three honest stages: parallel retrieval, normalization, comparison; keep it product-facing rather than technical clutter.

## Python backend

Create a separate `backend/` FastAPI service with the requested modular structure:

```text
backend/
  app/
    main.py
    api/routes/{flights.py,sources.py}
    models/{flight.py,search.py,source.py}
    schemas/{flight.py,search.py}
    services/{search_orchestrator.py,normalization.py,cache.py}
    scrapers/base.py
    scrapers/airlines/{indigo.py,air_india.py,akasa.py,spicejet.py}
    scrapers/ota/{makemytrip.py,cleartrip.py,easemytrip.py,ixigo.py}
    utils/{dates.py,currency.py,logging.py}
  requirements.txt
  .env.example
  Dockerfile
  README.md
```

- Define Pydantic request/response models for `FlightSearchParams`, normalized `FlightResult`, source status, search jobs, and source summaries.
- Implement a common async scraper interface and eight honest adapters. Use Playwright Python for browser-required sources, httpx/BeautifulSoup/lxml where appropriate, and do not bypass CAPTCHAs, access controls, or site policies. An adapter that cannot currently retrieve live results returns its actual unavailable/blocked/timeout/error status and never a hardcoded fare.
- Implement an orchestrator using `asyncio.gather(..., return_exceptions=True)` with a per-source timeout, isolated failures, structured logs, and progressive in-memory job updates. Add a short-lived cache with a 60-second default and cache age in responses; keep Redis optional and use a safe in-process fallback for a single-process prototype.
- Expose `POST /api/flights/search`, `GET /api/flights/search/{search_id}`, `GET /api/flights/{search_id}`, `GET /api/sources`, and `GET /api/health`, with CORS configured from an environment value and automatic OpenAPI documentation.
- Keep `DEMO_MODE=false` by default. If the Python service is not configured for the browser preview, the frontend must show a connection/unavailable state and zero flights, never demo prices.
- Include Docker/Playwright installation guidance, responsible-scraping notes, environment variables, and run instructions. The React app will read `VITE_API_BASE_URL`; no Node backend or browser-side Playwright will be introduced.

## React/TanStack implementation

- Rewrite the existing placeholder `src/routes/index.tsx` as the FareLens search/results route and add `src/routes/sources.tsx` plus any focused client-safe modules needed for API types, airport data, polling, formatting, and filter/sort state.
- Preserve TanStack Start routing and the existing root shell. Add a single mounted toast provider only if needed for recoverable interaction feedback.
- Use the existing Tailwind/shadcn-compatible token system and add a distinctive restrained palette, typography hierarchy, borders, and very limited motion in `src/styles.css`; avoid gradients, glassmorphism, glowing cards, blobs, and raw hardcoded colors in page code.
- Use semantic HTML, responsive layouts, keyboard-accessible autocomplete and dialogs, labeled controls, readable empty/loading/error states, and stable dimensions for comparison elements. The mobile layout must keep the search and live price comparison usable without horizontal scrolling.
- Add route-level metadata for `/` and `/sources` with unique titles/descriptions, Open Graph type, and Twitter card values; remove the starter “Lovable App” metadata from the root defaults while keeping the shared stylesheet link and shell intact.

## Verification

- Verify the placeholder is gone and `/` renders the full search experience; verify `/sources` renders and all navigation targets resolve.
- Exercise form validation, swap, autocomplete selection, filters, sorting, refresh, progressive status polling, source failure states, all-failed state, and no-booking-URL behavior with a controlled API response shape; confirm no price is rendered unless present in the API payload.
- Run the project’s build/lint checks and inspect current build/runtime logs after edits. Run a responsive browser check at desktop and mobile widths, including the search and result states.
- Validate the Python service imports, Pydantic schemas, endpoint contracts, orchestrator concurrency/timeout isolation, and Docker configuration where the environment allows it. Live provider access will remain truthful: sources that block or are unavailable will be surfaced as such rather than masked.

## Important integration assumption

This repository is currently a fresh TanStack Start frontend with no Python runtime or backend directory. The plan therefore keeps FastAPI as a separately runnable `backend/` service and makes the frontend’s API base URL configurable. The preview can fully demonstrate the interface and honest disconnected/error states until a Python service is started and `VITE_API_BASE_URL` points to it; it will not silently use mock fares.