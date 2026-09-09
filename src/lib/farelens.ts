export type SourceStatus =
  | "searching"
  | "live"
  | "unavailable"
  | "timeout"
  | "blocked"
  | "no_results"
  | "error";

export type Airport = {
  city: string;
  code: string;
  name: string;
};

export type FlightResult = {
  id: string;
  source: string;
  airline: string;
  flight_number: string | null;
  origin: string;
  destination: string;
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  stops: number;
  cabin_class: string;
  base_fare: number | null;
  taxes: number | null;
  fees: number | null;
  total_fare: number;
  currency: string;
  baggage: string | null;
  booking_url: string | null;
  scraped_at: string;
  status: SourceStatus;
};

export type SourceSummary = {
  name: string;
  type: "Airline" | "OTA";
  status: SourceStatus;
  result_count: number;
  last_successful_fetch: string | null;
  response_time_ms: number | null;
  error: string | null;
};

export type SearchState = {
  search_id: string;
  status: "searching" | "completed" | "failed";
  sources: SourceSummary[];
  flights: FlightResult[];
  started_at: string;
  completed_at: string | null;
  total_search_time_ms: number | null;
  cache_age_seconds: number | null;
};

export const AIRPORTS: Airport[] = [
  { city: "Delhi", code: "DEL", name: "Indira Gandhi International Airport" },
  { city: "Mumbai", code: "BOM", name: "Chhatrapati Shivaji Maharaj International Airport" },
  { city: "Bengaluru", code: "BLR", name: "Kempegowda International Airport" },
  { city: "Hyderabad", code: "HYD", name: "Rajiv Gandhi International Airport" },
  { city: "Chennai", code: "MAA", name: "Chennai International Airport" },
  { city: "Kolkata", code: "CCU", name: "Netaji Subhas Chandra Bose International Airport" },
  { city: "Pune", code: "PNQ", name: "Pune International Airport" },
  { city: "Ahmedabad", code: "AMD", name: "Sardar Vallabhbhai Patel International Airport" },
];

export const SOURCE_CATALOG: SourceSummary[] = [
  ...["IndiGo", "Air India", "Akasa Air", "SpiceJet"].map((name) => ({
    name,
    type: "Airline" as const,
    status: "unavailable" as const,
    result_count: 0,
    last_successful_fetch: null,
    response_time_ms: null,
    error: null,
  })),
  ...["MakeMyTrip", "Cleartrip", "EaseMyTrip", "ixigo"].map((name) => ({
    name,
    type: "OTA" as const,
    status: "unavailable" as const,
    result_count: 0,
    last_successful_fetch: null,
    response_time_ms: null,
    error: null,
  })),
];

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export function formatINR(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false }).format(date);
}

export function formatDate(value: string) {
  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "long", year: "numeric" }).format(date);
}

export function formatDuration(minutes: number) {
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return `${hours}h ${remainder.toString().padStart(2, "0")}m`;
}

export function relativeAge(value: string | null) {
  if (!value) return "Not yet fetched";
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  return `${Math.floor(seconds / 60)}m ago`;
}

export function displayStatus(status: SourceStatus) {
  return status === "no_results" ? "No results" : status.charAt(0).toUpperCase() + status.slice(1);
}