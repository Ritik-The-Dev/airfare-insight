import { useEffect, useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, ArrowUpDown, Check, ChevronDown, CircleAlert, Clock3, ExternalLink, Filter, Gauge, Menu, RefreshCw, Search, SlidersHorizontal, X } from "lucide-react";
import {
  AIRPORTS,
  API_BASE_URL,
  type Airport,
  type FlightResult,
  type SearchState,
  type SourceStatus,
  type SourceSummary,
  formatDate,
  formatDuration,
  formatINR,
  formatTime,
  relativeAge,
  displayStatus,
} from "@/lib/farelens";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "FareLens — Know the fare before you book" },
      { name: "description", content: "Compare live airfare across Indian airlines and travel platforms in one clear view." },
      { property: "og:title", content: "FareLens — Know the fare before you book" },
      { property: "og:description", content: "Compare live airfare across Indian airlines and travel platforms in one clear view." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: FareLensHome,
});

type SortKey = "cheapest" | "fastest" | "earliest";

function FareLensHome() {
  const [from, setFrom] = useState<Airport | null>(null);
  const [to, setTo] = useState<Airport | null>(null);
  const [departure, setDeparture] = useState("");
  const [returnDate, setReturnDate] = useState("");
  const [passengers, setPassengers] = useState("1");
  const [cabin, setCabin] = useState("Economy");
  const [query, setQuery] = useState<SearchState | null>(null);
  const [error, setError] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [sort, setSort] = useState<SortKey>("cheapest");
  const [selectedAirline, setSelectedAirline] = useState("All airlines");
  const [selectedStops, setSelectedStops] = useState("Any stops");
  const [showFilters, setShowFilters] = useState(false);
  const [showSystem, setShowSystem] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);

  useEffect(() => {
    if (!query || query.status !== "searching" || !API_BASE_URL) return;
    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/flights/search/${query.search_id}`);
        if (response.ok) {
          const next = (await response.json()) as SearchState;
          setQuery(next);
          if (next.status !== "searching") setIsSearching(false);
        }
      } catch {
        setIsSearching(false);
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [query]);

  const airlines = useMemo(() => [...new Set((query?.flights ?? []).map((flight) => flight.airline))], [query]);
  const flights = useMemo(() => {
    const filtered = (query?.flights ?? []).filter((flight) => {
      const airlineMatch = selectedAirline === "All airlines" || flight.airline === selectedAirline;
      const stopsMatch = selectedStops === "Any stops" || (selectedStops === "Non-stop" ? flight.stops === 0 : flight.stops > 0);
      return airlineMatch && stopsMatch;
    });
    return [...filtered].sort((a, b) => {
      if (sort === "fastest") return a.duration_minutes - b.duration_minutes;
      if (sort === "earliest") return new Date(a.departure_time).getTime() - new Date(b.departure_time).getTime();
      return a.total_fare - b.total_fare;
    });
  }, [query, selectedAirline, selectedStops, sort]);
  const lowest = flights[0];
  const liveSources = (query?.sources ?? []).filter((source) => source.status === "live");

  async function searchLiveFares(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    if (!from || !to || !departure) {
      setError("Choose an origin, destination, and departure date to search live fares.");
      return;
    }
    if (from.code === to.code) {
      setError("Origin and destination must be different airports.");
      return;
    }
    if (!API_BASE_URL) {
      setError("The live search service is not connected in this preview. No sample fares have been added.");
      setQuery(null);
      return;
    }
    setIsSearching(true);
    setQuery(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/flights/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ origin: from.code, destination: to.code, departure_date: departure, return_date: returnDate || null, passengers: Number(passengers), cabin_class: cabin }),
      });
      if (!response.ok) throw new Error("Search service unavailable");
      const next = (await response.json()) as SearchState;
      setQuery(next);
    } catch {
      setIsSearching(false);
      setError("Live fares could not be retrieved right now. Please check the service and try again.");
    }
  }

  function swapAirports() {
    setFrom(to);
    setTo(from);
  }

  return (
    <main className="min-h-screen bg-background">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 lg:px-10">
        <Link to="/" className="flex items-center gap-3 text-foreground" aria-label="FareLens home">
          <span className="flex size-9 items-center justify-center bg-primary text-sm font-semibold text-primary-foreground">FL</span>
          <span className="text-xl font-semibold tracking-tight">FareLens</span>
        </Link>
        <nav className={`${mobileMenu ? "flex" : "hidden"} absolute left-5 right-5 top-20 z-10 flex-col gap-4 border border-border bg-card p-5 text-sm shadow-sm md:static md:flex md:flex-row md:items-center md:border-0 md:bg-transparent md:p-0 md:shadow-none`}>
          <a href="#search" className="text-foreground/75 transition-colors hover:text-foreground">Search</a>
          <a href="#how-it-works" className="text-foreground/75 transition-colors hover:text-foreground">How it works</a>
          <Link to="/sources" className="text-foreground/75 transition-colors hover:text-foreground">Sources</Link>
        </nav>
        <div className="flex items-center gap-3">
          <span className="hidden items-center gap-2 text-xs font-medium text-foreground/70 sm:flex"><span className="size-2 rounded-full bg-primary" /> Live data</span>
          <button className="inline-flex size-9 items-center justify-center border border-border md:hidden" onClick={() => setMobileMenu((value) => !value)} aria-label="Open navigation"><Menu size={17} /></button>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-5 pb-16 pt-12 lg:px-10 lg:pb-24 lg:pt-20">
        <div className="max-w-3xl">
          <p className="editorial-label mb-5 text-primary">India’s live airfare view</p>
          <h1 className="max-w-2xl text-5xl leading-[0.98] text-foreground sm:text-7xl">Know the fare before you book.</h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-muted-foreground">Compare live airfare across Indian airlines and travel platforms in one place. No estimates. No noise.</p>
        </div>

        <form id="search" onSubmit={searchLiveFares} className="mt-12 border border-border bg-card p-4 shadow-sm sm:p-6">
          <div className="grid gap-3 lg:grid-cols-[1fr_auto_1fr_1fr_1fr] lg:items-end">
            <AirportField label="From" value={from} onChange={setFrom} exclude={to?.code} />
            <button type="button" onClick={swapAirports} className="mb-1 inline-flex size-10 items-center justify-center self-end border border-border text-primary transition-colors hover:bg-muted" aria-label="Swap origin and destination"><ArrowUpDown size={17} /></button>
            <AirportField label="To" value={to} onChange={setTo} exclude={from?.code} />
            <label className="block"><span className="editorial-label mb-2 block text-muted-foreground">Departure</span><input type="date" value={departure} onChange={(event) => setDeparture(event.target.value)} className="h-12 w-full border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring" /></label>
            <label className="block"><span className="editorial-label mb-2 block text-muted-foreground">Return <span className="normal-case tracking-normal">optional</span></span><input type="date" value={returnDate} min={departure} onChange={(event) => setReturnDate(event.target.value)} className="h-12 w-full border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring" /></label>
          </div>
          <div className="mt-4 flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="grid grid-cols-2 gap-3 sm:flex sm:items-end">
              <label><span className="editorial-label mb-2 block text-muted-foreground">Passengers</span><select value={passengers} onChange={(event) => setPassengers(event.target.value)} className="h-11 min-w-32 border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"><option value="1">1 passenger</option><option value="2">2 passengers</option><option value="3">3 passengers</option><option value="4">4 passengers</option></select></label>
              <label><span className="editorial-label mb-2 block text-muted-foreground">Cabin</span><select value={cabin} onChange={(event) => setCabin(event.target.value)} className="h-11 min-w-32 border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"><option>Economy</option><option>Premium Economy</option><option>Business</option></select></label>
            </div>
            <button type="submit" disabled={isSearching} className="inline-flex h-12 items-center justify-center gap-3 bg-primary px-6 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-wait disabled:opacity-70"><Search size={17} /> {isSearching ? "Fetching live fares" : "Search live fares"}<ArrowRight size={16} /></button>
          </div>
          {error && <p className="mt-4 flex items-center gap-2 text-sm text-destructive"><CircleAlert size={15} /> {error}</p>}
        </form>
      </section>

      {isSearching && <LoadingPanel sources={query?.sources ?? []} />}
      {query && !isSearching && <ResultsPanel query={query} flights={flights} lowest={lowest} liveSources={liveSources} sort={sort} setSort={setSort} airlines={airlines} selectedAirline={selectedAirline} setSelectedAirline={setSelectedAirline} selectedStops={selectedStops} setSelectedStops={setSelectedStops} showFilters={showFilters} setShowFilters={setShowFilters} onRefresh={() => { setQuery(null); setTimeout(() => void searchLiveFares({ preventDefault() {} } as React.FormEvent), 0); }} showSystem={showSystem} setShowSystem={setShowSystem} from={from} to={to} departure={departure} passengers={passengers} cabin={cabin} />}

      <section id="how-it-works" className="page-rule mx-auto grid max-w-7xl gap-8 px-5 py-16 lg:grid-cols-[1fr_2fr] lg:px-10 lg:py-24">
        <div><p className="editorial-label text-primary">How it works</p><h2 className="mt-4 text-4xl leading-tight">A clearer read on a moving market.</h2></div>
        <div className="grid gap-8 sm:grid-cols-3">
          {[{ number: "01", title: "Retrieve", text: "Airline and travel platform sources are queried in parallel when you search." }, { number: "02", title: "Normalize", text: "Different fare formats are brought into one consistent flight result." }, { number: "03", title: "Compare", text: "See what is live, what is unavailable, and which fare is lowest right now." }].map((item) => <div key={item.number} className="border-t border-border pt-4"><span className="text-sm font-semibold text-accent-foreground">{item.number}</span><h3 className="mt-8 text-3xl">{item.title}</h3><p className="mt-3 text-sm leading-6 text-muted-foreground">{item.text}</p></div>)}
        </div>
      </section>
      <footer className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-8 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between lg:px-10"><span>FareLens · SIH26056 prototype</span><span>Live source transparency, always.</span></footer>
    </main>
  );
}

function AirportField({ label, value, onChange, exclude }: { label: string; value: Airport | null; onChange: (airport: Airport | null) => void; exclude?: string }) {
  const [input, setInput] = useState(value ? `${value.code} · ${value.city}` : "");
  const [open, setOpen] = useState(false);
  const matches = AIRPORTS.filter((airport) => airport.code !== exclude && `${airport.city} ${airport.code} ${airport.name}`.toLowerCase().includes(input.toLowerCase())).slice(0, 5);
  return <div className="relative"><label className="block"><span className="editorial-label mb-2 block text-muted-foreground">{label}</span><div className="relative"><input value={input} onFocus={() => setOpen(true)} onChange={(event) => { setInput(event.target.value); onChange(null); setOpen(true); }} placeholder="City or airport" className="h-12 w-full border border-input bg-background px-3 pr-8 text-sm outline-none focus:ring-2 focus:ring-ring" />{value && <button type="button" onClick={() => { onChange(null); setInput(""); }} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" aria-label={`Clear ${label}`}><X size={15} /></button>}</div></label>{open && matches.length > 0 && <div className="absolute left-0 right-0 top-[4.7rem] z-20 border border-border bg-card shadow-lg">{matches.map((airport) => <button type="button" key={airport.code} onClick={() => { onChange(airport); setInput(`${airport.code} · ${airport.city}`); setOpen(false); }} className="block w-full border-b border-border px-3 py-3 text-left last:border-0 hover:bg-muted"><span className="block text-sm font-semibold">{airport.code} <span className="font-normal">— {airport.city}</span></span><span className="mt-1 block truncate text-xs text-muted-foreground">{airport.name}</span></button>)}</div>}</div>;
}

function LoadingPanel({ sources }: { sources: SourceSummary[] }) {
  const displaySources = sources.length ? sources : SOURCE_CATALOG_FALLBACK;
  return <section className="border-y border-border bg-muted/45"><div className="mx-auto max-w-7xl px-5 py-12 lg:px-10"><div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end"><div><p className="editorial-label text-primary">Fetching live fares</p><h2 className="mt-3 text-4xl">Watching the market.</h2></div><span className="text-sm text-muted-foreground">Results will appear as each source responds.</span></div><div className="mt-8 grid gap-px border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">{displaySources.map((source) => <div key={source.name} className="flex items-center justify-between bg-card px-4 py-4"><div className="flex items-center gap-3"><span className={`size-2 rounded-full ${source.status === "live" ? "bg-primary" : source.status === "unavailable" ? "bg-destructive" : "animate-pulse bg-accent"}`} /><div><p className="text-sm font-medium">{source.name}</p><p className="text-xs text-muted-foreground">{source.status === "searching" ? "Searching..." : source.status === "live" ? `${source.result_count} flights found` : displayStatus(source.status)}</p></div></div>{source.status === "live" ? <Check size={16} className="text-primary" /> : source.status === "searching" ? <Clock3 size={16} className="text-muted-foreground" /> : <span className="text-xs text-muted-foreground">—</span>}</div>)}</div></div></section>;
}

const SOURCE_CATALOG_FALLBACK: SourceSummary[] = ["IndiGo", "Air India", "Akasa Air", "SpiceJet", "MakeMyTrip", "Cleartrip", "EaseMyTrip", "ixigo"].map((name) => ({ name, type: ["MakeMyTrip", "Cleartrip", "EaseMyTrip", "ixigo"].includes(name) ? "OTA" : "Airline", status: "searching", result_count: 0, last_successful_fetch: null, response_time_ms: null, error: null }));

function ResultsPanel(props: { query: SearchState; flights: FlightResult[]; lowest?: FlightResult; liveSources: SourceSummary[]; sort: SortKey; setSort: (sort: SortKey) => void; airlines: string[]; selectedAirline: string; setSelectedAirline: (value: string) => void; selectedStops: string; setSelectedStops: (value: string) => void; showFilters: boolean; setShowFilters: (value: boolean) => void; onRefresh: () => void; showSystem: boolean; setShowSystem: (value: boolean) => void; from: Airport | null; to: Airport | null; departure: string; passengers: string; cabin: string }) {
  const { query, flights, lowest, liveSources, sort, setSort, airlines, selectedAirline, setSelectedAirline, selectedStops, setSelectedStops, showFilters, setShowFilters, onRefresh, showSystem, setShowSystem, from, to, departure, passengers, cabin } = props;
  const allFailed = query.flights.length === 0 && query.sources.every((source) => source.status !== "live");
  return <section className="border-t border-border"><div className="mx-auto max-w-7xl px-5 py-12 lg:px-10 lg:py-16"><div className="flex flex-col gap-5 border-b border-border pb-8 md:flex-row md:items-end md:justify-between"><div><p className="editorial-label text-primary">{from?.code ?? "—"} <span className="px-2 text-muted-foreground">→</span> {to?.code ?? "—"}</p><h2 className="mt-3 text-4xl">Live fares</h2><p className="mt-2 text-sm text-muted-foreground">{departure ? formatDate(departure) : "Date not set"} · {passengers} passenger · {cabin} · Prices retrieved moments ago</p></div><div className="flex flex-wrap gap-2"><button type="button" onClick={onRefresh} className="inline-flex items-center gap-2 border border-border bg-card px-4 py-2.5 text-sm font-medium hover:bg-muted"><RefreshCw size={15} /> Refresh live fares</button><button type="button" onClick={() => setShowSystem(!showSystem)} className="inline-flex items-center gap-2 border border-border px-4 py-2.5 text-sm font-medium hover:bg-muted"><Gauge size={15} /> System status</button></div></div>{showSystem && <SystemStatus query={query} onClose={() => setShowSystem(false)} />}{allFailed ? <div className="border-b border-border py-14"><CircleAlert className="text-destructive" size={22} /><h3 className="mt-4 text-3xl">Live fares couldn’t be retrieved right now.</h3><p className="mt-2 max-w-lg text-sm leading-6 text-muted-foreground">No source returned a fare for this search. Try again shortly; no sample prices are shown.</p></div> : <><div className="grid gap-4 py-8 lg:grid-cols-[1.15fr_0.85fr]"><div className="border border-primary/25 bg-primary/5 p-6"><p className="editorial-label text-primary">Lowest live fare</p><div className="mt-4 flex flex-wrap items-end justify-between gap-4"><div><p className="text-5xl text-foreground">{formatINR(lowest?.total_fare)}</p><p className="mt-2 text-sm text-muted-foreground">{lowest?.airline ?? "Waiting for a live result"} {lowest?.stops === 0 ? "· Non-stop" : "· " + lowest?.stops + " stop"} {lowest ? `· ${formatDuration(lowest.duration_minutes)}` : ""}</p></div><span className="flex items-center gap-2 text-xs font-medium text-primary"><span className="size-2 rounded-full bg-primary" /> {lowest ? `Live · ${relativeAge(lowest.scraped_at)}` : "No live fare"}</span></div></div><ComparisonTable sources={query.sources} flights={query.flights} /></div><div className="flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between"><div><p className="editorial-label text-primary">{flights.length} available results</p><p className="mt-2 text-sm text-muted-foreground">{liveSources.length} live sources · {query.total_search_time_ms ? `completed in ${(query.total_search_time_ms / 1000).toFixed(1)}s` : "searching"}</p></div><div className="flex flex-wrap gap-2"><button type="button" onClick={() => setShowFilters(!showFilters)} className="inline-flex items-center gap-2 border border-border px-3 py-2 text-sm"><SlidersHorizontal size={15} /> Filters</button><label className="flex items-center gap-2 border border-border px-3 text-sm"><span className="text-muted-foreground">Sort</span><select value={sort} onChange={(event) => setSort(event.target.value as SortKey)} className="bg-transparent py-2 font-medium outline-none"><option value="cheapest">Cheapest</option><option value="fastest">Fastest</option><option value="earliest">Earliest departure</option></select><ChevronDown size={14} /></label></div></div>{showFilters && <div className="grid gap-3 border-b border-border bg-muted/35 p-4 sm:grid-cols-2 lg:grid-cols-4"><label className="text-sm"><span className="editorial-label mb-2 block text-muted-foreground">Airline</span><select value={selectedAirline} onChange={(event) => setSelectedAirline(event.target.value)} className="h-10 w-full border border-input bg-card px-3 text-sm"><option>All airlines</option>{airlines.map((airline) => <option key={airline}>{airline}</option>)}</select></label><label className="text-sm"><span className="editorial-label mb-2 block text-muted-foreground">Stops</span><select value={selectedStops} onChange={(event) => setSelectedStops(event.target.value)} className="h-10 w-full border border-input bg-card px-3 text-sm"><option>Any stops</option><option>Non-stop</option><option>With stops</option></select></label><div className="hidden items-end text-xs text-muted-foreground lg:flex">Price and time filters are available when live results include comparable values.</div></div>}<div className="mt-6 grid gap-3">{flights.length ? flights.map((flight) => <FlightCard key={flight.id} flight={flight} />) : <div className="border border-border p-8 text-center text-sm text-muted-foreground">No live flights match these filters.</div>}</div></>}</div></section>;
}

function ComparisonTable({ sources, flights }: { sources: SourceSummary[]; flights: FlightResult[] }) { return <div className="border border-border bg-card p-6"><div className="flex items-center justify-between"><p className="editorial-label text-foreground">Live price comparison</p><Filter size={15} className="text-muted-foreground" /></div><div className="mt-5 space-y-3">{sources.map((source) => { const cheapest = flights.filter((flight) => flight.source === source.name).sort((a, b) => a.total_fare - b.total_fare)[0]; return <div className="flex items-center justify-between gap-4 text-sm" key={source.name}><span className="flex items-center gap-2"><span className={`size-1.5 rounded-full ${source.status === "live" ? "bg-primary" : "bg-muted-foreground/45"}`} />{source.name}</span><span className={cheapest ? "font-semibold" : "text-muted-foreground"}>{cheapest ? formatINR(cheapest.total_fare) : displayStatus(source.status)}</span></div>; })}</div></div>; }

function FlightCard({ flight }: { flight: FlightResult }) { return <article className="grid gap-5 border border-border bg-card p-5 transition-colors hover:border-primary/50 sm:grid-cols-[1fr_1.6fr_auto] sm:items-center"><div><p className="text-sm font-semibold">{flight.airline}</p><p className="mt-1 text-xs text-muted-foreground">{flight.flight_number ?? "Flight number not provided"}</p></div><div className="flex items-center gap-3"><div className="text-right"><p className="text-xl font-medium">{formatTime(flight.departure_time)}</p><p className="text-xs font-semibold text-muted-foreground">{flight.origin}</p></div><div className="min-w-20 flex-1 text-center"><p className="text-xs text-muted-foreground">{formatDuration(flight.duration_minutes)}</p><div className="my-2 flex items-center gap-1"><span className="h-px flex-1 bg-border" /><span className="size-1.5 rounded-full bg-primary" /><span className="h-px flex-1 bg-border" /></div><p className="text-xs text-muted-foreground">{flight.stops === 0 ? "Non-stop" : `${flight.stops} stop`}</p></div><div><p className="text-xl font-medium">{formatTime(flight.arrival_time)}</p><p className="text-xs font-semibold text-muted-foreground">{flight.destination}</p></div></div><div className="flex items-center justify-between gap-4 sm:flex-col sm:items-end"><div className="text-right"><p className="text-2xl font-medium">{formatINR(flight.total_fare)}</p><p className="mt-1 flex items-center justify-end gap-1 text-xs text-muted-foreground"><span className="size-1.5 rounded-full bg-primary" />{flight.source} · {relativeAge(flight.scraped_at)}</p></div>{flight.booking_url && <a href={flight.booking_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground">View deal <ExternalLink size={13} /></a>}</div></article>; }

function SystemStatus({ query, onClose }: { query: SearchState; onClose: () => void }) { const successful = query.sources.filter((source) => source.status === "live").length; return <aside className="my-6 border border-primary/25 bg-primary/5 p-5"><div className="flex items-start justify-between gap-4"><div><p className="editorial-label text-primary">Live search</p><h3 className="mt-2 text-2xl">System status</h3></div><button type="button" onClick={onClose} aria-label="Close system status"><X size={17} /></button></div><div className="mt-5 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4"><div><p className="text-xs text-muted-foreground">Search ID</p><p className="mt-1 truncate font-mono text-xs">{query.search_id}</p></div><div><p className="text-xs text-muted-foreground">Sources queried</p><p className="mt-1 font-semibold">{query.sources.length}</p></div><div><p className="text-xs text-muted-foreground">Successful</p><p className="mt-1 font-semibold">{successful}</p></div><div><p className="text-xs text-muted-foreground">Flights retrieved</p><p className="mt-1 font-semibold">{query.flights.length}</p></div></div></aside>; }