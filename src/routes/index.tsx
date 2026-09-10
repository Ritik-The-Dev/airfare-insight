import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { CircleAlert } from "lucide-react";
import { API_BASE_URL, formatINR } from "@/lib/farelens";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "FareLens — India Airfare Price Index" },
      { name: "description", content: "A real-time price index computed from live and historical fare observations across domestic routes." },
      { property: "og:title", content: "FareLens — India Airfare Price Index" },
      { property: "og:description", content: "Tracking the cost of air travel across India." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: CPIDashboard,
});

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type MonthlyIndexEntry = {
  month: string;
  index: number;
  avg_fare: number;
  observation_count: number;
  data_type_mix: { MOCK: number; LIVE: number };
};

type RouteIndex = {
  route: string;
  monthly_index: MonthlyIndexEntry[];
};

type AirfareIndexResponse = {
  base_period: string;
  base_index: number;
  methodology: string;
  data_disclaimer: string;
  monthly_index: MonthlyIndexEntry[];
  route_indices: RouteIndex[];
};

type ObservationSummary = {
  total_observations: number;
  live_observations: number;
  mock_observations: number;
  routes_count: number;
  airlines_count: number;
  sources_count: number;
  latest_observation: string | null;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatMonthLabel(yyyyMM: string): string {
  const [year, month] = yyyyMM.split("-");
  const date = new Date(Number(year), Number(month) - 1, 1);
  return date.toLocaleString("en-IN", { month: "long", year: "numeric" });
}

function formatMonthShort(yyyyMM: string): string {
  const [year, month] = yyyyMM.split("-");
  const date = new Date(Number(year), Number(month) - 1, 1);
  return date.toLocaleString("en-IN", { month: "short", year: "numeric" });
}

function dataTypeBadge(mix: { MOCK: number; LIVE: number }): string {
  if (mix.LIVE === 0) return "MOCK";
  if (mix.MOCK === 0) return "LIVE";
  return "MIXED";
}

// ---------------------------------------------------------------------------
// Skeleton placeholder
// ---------------------------------------------------------------------------
function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-muted ${className}`} />;
}

// ---------------------------------------------------------------------------
// Route airlines map (display only)
// ---------------------------------------------------------------------------
const ROUTE_AIRLINES: Record<string, string> = {
  "DEL-BOM": "IndiGo · Air India · Akasa · SpiceJet",
  "DEL-BLR": "IndiGo · Air India · Akasa",
  "BOM-BLR": "IndiGo · Air India · SpiceJet",
  "DEL-HYD": "IndiGo · Air India · Akasa",
  "DEL-MAA": "IndiGo · Air India · SpiceJet",
  "BOM-DEL": "IndiGo · Air India · Akasa · SpiceJet",
};

// ---------------------------------------------------------------------------
// Sparkline — simple div-based bar chart, no recharts dependency
// ---------------------------------------------------------------------------
function Sparkline({ data }: { data: MonthlyIndexEntry[] }) {
  if (data.length === 0) return null;
  const values = data.map((d) => d.index);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  return (
    <div className="flex items-end gap-0.5" style={{ height: 32 }} aria-hidden>
      {values.map((v, i) => {
        const heightPct = Math.max(10, Math.round(((v - min) / range) * 100));
        return (
          <div
            key={i}
            className="flex-1 bg-primary/60 rounded-sm"
            style={{ height: `${heightPct}%` }}
            title={`${data[i]?.month ?? ""}: ${v}`}
          />
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
function CPIDashboard() {
  const [indexData, setIndexData] = useState<AirfareIndexResponse | null>(null);
  const [summary, setSummary] = useState<ObservationSummary | null>(null);
  const [indexLoading, setIndexLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/airfare-index`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setIndexData(data as AirfareIndexResponse);
      })
      .catch(() => undefined)
      .finally(() => setIndexLoading(false));
  }, []);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/fare-observations/summary`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setSummary(data as ObservationSummary);
      })
      .catch(() => undefined)
      .finally(() => setSummaryLoading(false));
  }, []);

  const monthly = indexData?.monthly_index ?? [];
  const latest = monthly[monthly.length - 1] ?? null;
  const prev = monthly[monthly.length - 2] ?? null;
  const indexChange = latest && prev ? latest.index - prev.index : null;
  const basePeriodLabel = indexData?.base_period
    ? formatMonthLabel(indexData.base_period)
    : null;

  return (
    <main className="min-h-screen bg-background">

      {/* ------------------------------------------------------------------ */}
      {/* HEADER                                                               */}
      {/* ------------------------------------------------------------------ */}
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 lg:px-10">
        <Link to="/" className="flex items-center gap-3 text-foreground" aria-label="FareLens home">
          <span className="flex size-9 items-center justify-center bg-primary text-sm font-semibold text-primary-foreground">
            FL
          </span>
          <span className="text-xl font-semibold tracking-tight">FareLens</span>
        </Link>

        <nav className="hidden items-center gap-6 text-sm md:flex">
          <Link to="/" className="font-medium text-foreground">Dashboard</Link>
          <Link to="/search" className="text-foreground/70 transition-colors hover:text-foreground">Search Flights</Link>
          <Link to="/sources" className="text-foreground/70 transition-colors hover:text-foreground">Sources</Link>
        </nav>

        <span className="editorial-label rounded border border-border bg-muted px-2.5 py-1 text-muted-foreground">
          SIH26056 Prototype
        </span>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* HERO                                                                 */}
      {/* ------------------------------------------------------------------ */}
      <section className="mx-auto max-w-7xl px-5 pb-16 pt-12 lg:px-10 lg:pb-20 lg:pt-20">
        <p className="editorial-label text-primary">India Airfare Price Index</p>
        <h1 className="mt-5 max-w-2xl text-5xl leading-[0.97] sm:text-7xl">
          Tracking the cost of air travel across India.
        </h1>
        <p className="mt-6 max-w-xl text-base leading-7 text-muted-foreground">
          A real-time price index computed from live and historical fare observations across domestic routes.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Link
            to="/search"
            className="inline-flex h-11 items-center gap-2 bg-primary px-5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Search Live Fares →
          </Link>
          <a
            href="#methodology"
            className="inline-flex h-11 items-center gap-2 border border-border px-5 text-sm font-medium text-foreground/80 transition-colors hover:bg-muted"
          >
            View methodology ↓
          </a>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* WHATSAPP BANNER (top of dashboard)                                  */}
      {/* ------------------------------------------------------------------ */}
      <div className="mx-auto max-w-7xl px-5 pb-8 lg:px-10">
        <a
          href={WA_LINK}
          target="_blank"
          rel="noreferrer"
          className="flex flex-col items-start justify-between gap-4 border border-primary/30 bg-primary/5 px-6 py-5 transition-colors hover:bg-primary/10 sm:flex-row sm:items-center"
        >
          <div className="flex items-start gap-4 sm:items-center">
            <span className="text-2xl">💬</span>
            <div>
              <p className="text-sm font-semibold text-foreground">
                New — Search flights directly on WhatsApp
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Message <span className="font-medium text-foreground">+91 99274 71836</span> — "Find cheapest flight Mumbai to Bangalore on 12 Sep" and get live results instantly.
              </p>
            </div>
          </div>
          <span className="editorial-label shrink-0 rounded border border-primary/30 bg-primary/10 px-3 py-1.5 text-primary">
            Try on WhatsApp →
          </span>
        </a>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* INDEX HEADLINE                                                       */}
      {/* ------------------------------------------------------------------ */}
      <section className="page-rule mx-auto max-w-7xl px-5 py-12 lg:px-10 lg:py-16">
        <p className="editorial-label text-primary">Current index value</p>

        {indexLoading ? (
          <div className="mt-6 border border-border bg-card p-8">
            <Skeleton className="h-20 w-48" />
            <Skeleton className="mt-4 h-5 w-72" />
            <Skeleton className="mt-3 h-4 w-52" />
          </div>
        ) : latest ? (
          <div className="mt-6 border border-border bg-card p-8">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <div className="flex items-end gap-4">
                  <span className="text-7xl font-light tabular-nums leading-none">
                    {latest.index.toFixed(1)}
                  </span>
                  {indexChange !== null && (
                    <span
                      className={`mb-1 text-xl font-medium tabular-nums ${
                        indexChange > 0 ? "text-destructive" : "text-primary"
                      }`}
                    >
                      {indexChange > 0 ? "▲" : "▼"} {Math.abs(indexChange).toFixed(1)} pts
                    </span>
                  )}
                </div>
                <p className="mt-3 text-sm text-muted-foreground">
                  {formatMonthLabel(latest.month)} · vs{" "}
                  {basePeriodLabel ? `${basePeriodLabel} baseline = 100` : "base period = 100"}
                </p>
                {indexChange !== null && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {indexChange > 0 ? "+" : ""}{indexChange.toFixed(1)}% month-on-month
                    {indexChange > 0 ? " — fares rising" : " — fares falling"}
                  </p>
                )}
              </div>
              <div className="flex flex-col gap-3 text-sm text-muted-foreground">
                <div className="flex items-center justify-between gap-8 border-t border-border pt-3 sm:flex-col sm:items-end sm:border-0 sm:pt-0">
                  <span className="text-xs text-muted-foreground/70">Observations this month</span>
                  <span className="font-semibold text-foreground">{latest.observation_count.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex items-center justify-between gap-8 sm:flex-col sm:items-end">
                  <span className="text-xs text-muted-foreground/70">Average fare</span>
                  <span className="font-semibold text-foreground">{formatINR(latest.avg_fare)}</span>
                </div>
                <div className="flex items-center justify-between gap-8 sm:flex-col sm:items-end">
                  <span className="text-xs text-muted-foreground/70">Data type</span>
                  <DataTypeBadge mix={latest.data_type_mix} />
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-6 border border-border bg-card p-8 text-sm text-muted-foreground">
            Index data is unavailable. Check that the backend is running.
          </div>
        )}
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* MONTHLY INDEX TABLE                                                  */}
      {/* ------------------------------------------------------------------ */}
      <section className="page-rule mx-auto max-w-7xl px-5 py-12 lg:px-10 lg:py-16">
        <div className="flex flex-col gap-1">
          <p className="editorial-label text-primary">Monthly series</p>
          <h2 className="mt-2 text-4xl">India Domestic Airfare Price Index</h2>
          {basePeriodLabel && (
            <p className="mt-2 text-sm text-muted-foreground">
              Base Period: {basePeriodLabel} = 100 &nbsp;·&nbsp; Simple average fare index
            </p>
          )}
        </div>

        <div className="mt-8 overflow-x-auto border border-border">
          {/* Table header */}
          <div className="hidden grid-cols-[1.6fr_0.8fr_1fr_0.8fr_1fr_0.7fr] gap-4 border-b border-border bg-muted/50 px-5 py-3 text-xs font-semibold uppercase tracking-[0.13em] text-muted-foreground sm:grid">
            <span>Month</span>
            <span className="text-right">Index</span>
            <span className="text-right">Avg Fare</span>
            <span className="text-right">Change</span>
            <span className="text-right">Obs. Count</span>
            <span className="text-right">Data</span>
          </div>

          {indexLoading ? (
            <div className="space-y-0">
              {[1, 2, 3].map((i) => (
                <div key={i} className="border-b border-border px-5 py-4">
                  <Skeleton className="h-5 w-full" />
                </div>
              ))}
            </div>
          ) : monthly.length === 0 ? (
            <div className="px-5 py-10 text-center text-sm text-muted-foreground">
              No index data available.
            </div>
          ) : (
            monthly.map((row, i) => {
              const prevRow = monthly[i - 1] ?? null;
              const change = prevRow ? row.index - prevRow.index : null;
              const badge = dataTypeBadge(row.data_type_mix);
              const isBase = i === 0;

              return (
                <div
                  key={row.month}
                  className={`grid gap-3 border-b border-border px-5 py-4 last:border-b-0 sm:grid-cols-[1.6fr_0.8fr_1fr_0.8fr_1fr_0.7fr] sm:items-center sm:gap-4 ${
                    isBase ? "bg-muted/30" : ""
                  }`}
                >
                  {/* Month */}
                  <div className="flex items-center gap-2">
                    {isBase && (
                      <span className="editorial-label rounded bg-primary/10 px-1.5 py-0.5 text-primary">
                        BASE
                      </span>
                    )}
                    <span className="text-sm font-medium">{formatMonthLabel(row.month)}</span>
                  </div>

                  {/* Index */}
                  <span className="text-right text-sm font-semibold tabular-nums">
                    {row.index.toFixed(1)}
                  </span>

                  {/* Avg Fare */}
                  <span className="text-right text-sm tabular-nums">
                    {formatINR(row.avg_fare)}
                  </span>

                  {/* Change */}
                  <span
                    className={`text-right text-sm tabular-nums font-medium ${
                      change === null
                        ? "text-muted-foreground"
                        : change > 0
                        ? "text-destructive"
                        : "text-primary"
                    }`}
                  >
                    {change === null
                      ? "—"
                      : `${change > 0 ? "▲" : "▼"} ${Math.abs(change).toFixed(1)}%`}
                  </span>

                  {/* Obs count */}
                  <span className="text-right text-sm tabular-nums text-muted-foreground">
                    {row.observation_count.toLocaleString("en-IN")}
                  </span>

                  {/* Data badge */}
                  <div className="flex justify-end">
                    <DataTypeBadge mix={row.data_type_mix} label={badge} />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {indexData?.data_disclaimer && (
          <p className="mt-4 flex items-start gap-2 text-xs text-muted-foreground">
            <CircleAlert size={13} className="mt-0.5 shrink-0" />
            {indexData.data_disclaimer}
          </p>
        )}
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* ROUTE-LEVEL BREAKDOWN                                                */}
      {/* ------------------------------------------------------------------ */}
      <section className="page-rule mx-auto max-w-7xl px-5 py-12 lg:px-10 lg:py-16">
        <p className="editorial-label text-primary">Route breakdown</p>
        <h2 className="mt-2 text-4xl">Route-Level Fare Index</h2>
        <p className="mt-3 text-sm text-muted-foreground">
          Index computed independently for each route. Base = 100 at each route's earliest observation.
        </p>

        {indexLoading ? (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="border border-border bg-card p-5">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="mt-3 h-10 w-20" />
                <Skeleton className="mt-3 h-8 w-full" />
              </div>
            ))}
          </div>
        ) : indexData?.route_indices && indexData.route_indices.length > 0 ? (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {indexData.route_indices.map((ri) => {
              const [orig, dest] = ri.route.split("-");
              const latestRI = ri.monthly_index[ri.monthly_index.length - 1];
              const prevRI = ri.monthly_index[ri.monthly_index.length - 2] ?? null;
              const riChange = latestRI && prevRI ? latestRI.index - prevRI.index : null;
              const airlines = ROUTE_AIRLINES[ri.route] ?? "IndiGo · Air India";

              return (
                <div key={ri.route} className="border border-border bg-card p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="editorial-label text-muted-foreground">Route</p>
                      <p className="mt-1 text-xl font-medium">
                        {orig} <span className="text-muted-foreground">→</span> {dest}
                      </p>
                    </div>
                    {latestRI && (
                      <span
                        className={`text-sm font-semibold tabular-nums ${
                          riChange === null
                            ? "text-muted-foreground"
                            : riChange > 0
                            ? "text-destructive"
                            : "text-primary"
                        }`}
                      >
                        {riChange !== null
                          ? `${riChange > 0 ? "▲" : "▼"} ${Math.abs(riChange).toFixed(1)}`
                          : "Base"}
                      </span>
                    )}
                  </div>

                  {latestRI && (
                    <div className="mt-4">
                      <span className="text-4xl font-light tabular-nums">
                        {latestRI.index.toFixed(1)}
                      </span>
                      <span className="ml-2 text-xs text-muted-foreground">
                        {formatMonthShort(latestRI.month)}
                      </span>
                    </div>
                  )}

                  <div className="mt-4">
                    <Sparkline data={ri.monthly_index} />
                  </div>

                  <p className="mt-3 text-xs text-muted-foreground">{airlines}</p>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="mt-8 text-sm text-muted-foreground">
            Route breakdown unavailable.
          </p>
        )}
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* KEY STATISTICS ROW                                                   */}
      {/* ------------------------------------------------------------------ */}
      <section className="page-rule mx-auto max-w-7xl px-5 py-12 lg:px-10 lg:py-16">
        <p className="editorial-label text-primary">Data coverage</p>
        <h2 className="mt-2 text-4xl">Key Statistics</h2>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Total Observations"
            value={
              summaryLoading
                ? null
                : (summary?.total_observations ?? 0).toLocaleString("en-IN")
            }
            note="All data types"
          />
          <StatCard
            label="Live Observations"
            value={
              summaryLoading
                ? null
                : (summary?.live_observations ?? 0).toLocaleString("en-IN")
            }
            note="From Ignav API"
          />
          <StatCard
            label="Routes Monitored"
            value={
              summaryLoading
                ? null
                : (summary?.routes_count ?? 0).toString()
            }
            note="Domestic routes"
          />
          <StatCard
            label="Airlines Tracked"
            value={
              summaryLoading
                ? null
                : (summary?.airlines_count ?? 0).toString()
            }
            note="IndiGo, Air India, Akasa, SpiceJet"
          />
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* WHATSAPP FEATURE                                                     */}
      {/* ------------------------------------------------------------------ */}
      <section className="page-rule mx-auto max-w-7xl px-5 py-12 lg:px-10 lg:py-16">
        <WhatsAppSection />
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* METHODOLOGY                                                          */}
      {/* ------------------------------------------------------------------ */}
      <section
        id="methodology"
        className="page-rule mx-auto max-w-7xl px-5 py-12 lg:px-10 lg:py-16"
      >
        <p className="editorial-label text-primary">Methodology</p>
        <h2 className="mt-2 text-4xl">How the index is computed</h2>

        <div className="mt-8 grid gap-8 lg:grid-cols-[2fr_1fr]">
          <div className="space-y-6 text-sm leading-7 text-muted-foreground">
            <div>
              <h3 className="mb-2 text-base text-foreground">What the index measures</h3>
              <p>
                The India Domestic Airfare Price Index tracks changes in the average fare paid for
                economy-class domestic air travel. It is expressed as a number relative to a fixed
                base period, which equals 100. A reading of 105 means fares are 5% higher than
                the base period.
              </p>
            </div>
            <div>
              <h3 className="mb-2 text-base text-foreground">Base period definition</h3>
              <p>
                The base period is the earliest calendar month for which fare observations are
                available in the system. All subsequent months are indexed against the average fare
                of that month. Formula:{" "}
                <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground">
                  Index = (avg_fare / base_avg_fare) × 100
                </code>
              </p>
            </div>
            <div>
              <h3 className="mb-2 text-base text-foreground">Data sources</h3>
              <p>
                <strong className="text-foreground">LIVE</strong> — fares retrieved in real time
                from the Ignav Aviato API, covering IndiGo, Air India, Akasa Air, and SpiceJet on
                major domestic routes.
              </p>
              <p className="mt-2">
                <strong className="text-foreground">MOCK</strong> — synthetic fares generated as
                prototype data to demonstrate index computation while live data accumulates.
              </p>
            </div>
            <div className="rounded border border-border bg-muted/40 p-4">
              <p className="flex items-start gap-2 text-xs">
                <CircleAlert size={13} className="mt-0.5 shrink-0 text-muted-foreground" />
                <span>
                  <strong className="text-foreground">Disclaimer:</strong> MOCK data is synthetic
                  prototype data. FareLens is a SIH26056 student prototype. Index values are not
                  official government statistics and should not be used for commercial or policy
                  decisions.
                </span>
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="border border-border bg-card p-5">
              <p className="editorial-label text-muted-foreground">Index formula</p>
              <pre className="mt-3 overflow-x-auto text-xs text-foreground">
{`Index(m) = 
  avg_fare(m) / avg_fare(base) × 100`}
              </pre>
            </div>
            <div className="border border-border bg-card p-5">
              <p className="editorial-label text-muted-foreground">Covered routes</p>
              <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
                {["DEL–BOM", "DEL–BLR", "BOM–BLR", "DEL–HYD", "DEL–MAA", "BOM–DEL"].map((r) => (
                  <li key={r} className="flex items-center gap-2">
                    <span className="size-1.5 rounded-full bg-primary" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* FOOTER                                                               */}
      {/* ------------------------------------------------------------------ */}
      <footer className="page-rule mx-auto max-w-7xl px-5 py-8 text-xs text-muted-foreground lg:px-10">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <span>FareLens · SIH26056 · India Domestic Airfare Price Index Prototype</span>
          <div className="flex items-center gap-4">
            <Link to="/search" className="hover:text-foreground">Search Fares</Link>
            <Link to="/sources" className="hover:text-foreground">Sources</Link>
            <a href="#methodology" className="hover:text-foreground">Methodology</a>
          </div>
        </div>
        <p className="mt-2 max-w-xl leading-5">
          Data disclaimer: Index values are computed from prototype observations and may include
          synthetic MOCK data. Not official government statistics.
        </p>
      </footer>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  note,
}: {
  label: string;
  value: string | null;
  note: string;
}) {
  return (
    <div className="border border-border bg-card p-5">
      <p className="editorial-label text-muted-foreground">{label}</p>
      <div className="mt-3">
        {value === null ? (
          <Skeleton className="h-10 w-24" />
        ) : (
          <span className="text-4xl font-light tabular-nums">{value}</span>
        )}
      </div>
      <p className="mt-2 text-xs text-muted-foreground">{note}</p>
    </div>
  );
}

function DataTypeBadge({
  mix,
  label,
}: {
  mix: { MOCK: number; LIVE: number };
  label?: string;
}) {
  const badge = label ?? dataTypeBadge(mix);
  const cls =
    badge === "LIVE"
      ? "bg-primary/10 text-primary border-primary/25"
      : badge === "MIXED"
      ? "bg-accent/20 text-accent-foreground border-accent/30"
      : "bg-muted text-muted-foreground border-border";

  return (
    <span
      className={`editorial-label inline-flex items-center gap-1 rounded border px-1.5 py-0.5 ${cls}`}
    >
      {badge === "LIVE" && <span className="size-1.5 rounded-full bg-primary" />}
      {badge}
    </span>
  );
}

// ---------------------------------------------------------------------------
// WhatsApp Feature Section
// ---------------------------------------------------------------------------

const WA_NUMBER = "919927471836"; // E.164 without +
const WA_EXAMPLE = "Find the cheapest flight from Mumbai to Bangalore on 12th Sep 2026";
const WA_LINK = `https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(WA_EXAMPLE)}`;

const EXAMPLE_QUERIES = [
  "Cheapest flight Delhi to Mumbai tomorrow",
  "Find me a flight from Bangalore to Goa this Saturday",
  "Show me the fastest flight from Mumbai to Delhi",
];

function WhatsAppSection() {
  return (
    <div className="grid gap-0 overflow-hidden border border-border bg-card lg:grid-cols-[1fr_1fr]">
      {/* Left: Feature description */}
      <div className="flex flex-col justify-between p-8 lg:p-10">
        {/* Badge */}
        <div>
          <span className="editorial-label inline-flex items-center gap-1.5 rounded border border-primary/25 bg-primary/8 px-2.5 py-1 text-primary">
            <span className="size-1.5 rounded-full bg-primary" />
            New · Natural Language Search
          </span>

          <h2 className="mt-5 text-4xl leading-tight">
            Search flights on WhatsApp.
          </h2>

          <p className="mt-4 max-w-sm text-base leading-7 text-muted-foreground">
            No website required. Just message FareLens your flight requirement in plain English and get live fare results — directly on WhatsApp.
          </p>

          {/* Phone number */}
          <div className="mt-6 inline-flex items-center gap-3 rounded border border-border bg-background px-4 py-3">
            <span className="text-lg">💬</span>
            <div>
              <p className="editorial-label text-muted-foreground">WhatsApp</p>
              <p className="mt-0.5 font-semibold tracking-wide text-foreground">+91 99274 71836</p>
            </div>
          </div>

          {/* Example queries */}
          <div className="mt-8">
            <p className="editorial-label text-muted-foreground">Try saying</p>
            <ul className="mt-3 space-y-2">
              {EXAMPLE_QUERIES.map((q) => (
                <li key={q} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="mt-0.5 shrink-0 text-primary">→</span>
                  <span className="italic">"{q}"</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* CTA button */}
        <div className="mt-8">
          <a
            href={WA_LINK}
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-12 items-center gap-3 bg-primary px-6 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <span className="text-base">💬</span>
            Search on WhatsApp
          </a>
          <p className="mt-3 text-xs text-muted-foreground">
            Opens WhatsApp with an example query pre-filled.
          </p>
        </div>
      </div>

      {/* Right: Mock WhatsApp conversation */}
      <div className="flex items-center justify-center border-t border-border bg-muted/30 p-8 lg:border-l lg:border-t-0 lg:p-10">
        <div className="w-full max-w-xs space-y-3">
          {/* Header */}
          <div className="flex items-center gap-3 rounded-t border border-border bg-card px-4 py-3">
            <div className="flex size-8 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
              FL
            </div>
            <div>
              <p className="text-sm font-semibold">FareLens</p>
              <p className="text-xs text-muted-foreground">Flight Search Agent · Online</p>
            </div>
          </div>

          {/* User bubble */}
          <div className="flex justify-end">
            <div className="max-w-[85%] rounded-l-2xl rounded-br-2xl rounded-tr-sm border border-border bg-primary/10 px-4 py-3 text-sm text-foreground">
              Find cheapest flight Mumbai → BLR on 12 Sep ✈️
              <p className="mt-1 text-right text-xs text-muted-foreground">10:32</p>
            </div>
          </div>

          {/* Bot searching */}
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-r-2xl rounded-bl-sm rounded-tl-2xl border border-border bg-card px-4 py-3 text-sm text-foreground">
              🔎 Searching live fares...
              <p className="mt-1 text-xs text-muted-foreground">10:32</p>
            </div>
          </div>

          {/* Bot result */}
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-r-2xl rounded-bl-sm rounded-tl-2xl border border-border bg-card px-4 py-3 text-sm text-foreground">
              <p className="font-semibold">✈️ Best options found</p>
              <div className="mt-2 space-y-1.5 border-t border-border pt-2">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">IndiGo</span>
                  <span className="font-semibold">₹4,899</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Air India</span>
                  <span className="font-semibold">₹5,120</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Akasa Air</span>
                  <span className="font-semibold">₹5,310</span>
                </div>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">Live fares · 10:32</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
