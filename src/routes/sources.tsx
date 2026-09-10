import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, CheckCircle2, CircleAlert, Clock3 } from "lucide-react";
import { API_BASE_URL, SOURCE_CATALOG, type SourceSummary, displayStatus, relativeAge } from "@/lib/farelens";

export const Route = createFileRoute("/sources")({
  head: () => ({ meta: [
    { title: "Sources — FareLens" },
    { name: "description", content: "See the airline and travel platform sources FareLens checks for live airfare." },
    { property: "og:title", content: "Sources — FareLens" },
    { property: "og:description", content: "See the airline and travel platform sources FareLens checks for live airfare." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: SourcesPage,
});

function SourcesPage() {
  const [sources, setSources] = useState<SourceSummary[]>(SOURCE_CATALOG);
  useEffect(() => { void fetch(`${API_BASE_URL}/api/sources`).then((response) => response.ok ? response.json() : null).then((data) => { if (Array.isArray(data)) setSources(data as SourceSummary[]); }).catch(() => undefined); }, []);
  return <main className="min-h-screen bg-background"><header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 lg:px-10"><Link to="/" className="flex items-center gap-3"><span className="flex size-9 items-center justify-center bg-primary text-sm font-semibold text-primary-foreground">FL</span><span className="text-xl font-semibold tracking-tight">FareLens</span></Link><Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft size={15} /> Back to search</Link></header><section className="mx-auto max-w-7xl px-5 pb-20 pt-16 lg:px-10 lg:pt-24"><p className="editorial-label text-primary">Source directory</p><h1 className="mt-5 max-w-2xl text-6xl leading-[0.95]">Every fare has a source.</h1><p className="mt-6 max-w-xl text-base leading-7 text-muted-foreground">FareLens keeps availability visible. A source is marked live only when it returns a real result for a search.</p><div className="mt-16 overflow-hidden border border-border"><div className="hidden grid-cols-[1.5fr_1fr_1fr_1fr] gap-4 border-b border-border bg-muted/50 px-5 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground sm:grid"><span>Source</span><span>Type</span><span>Status</span><span>Last successful fetch</span></div>{sources.map((source) => <div key={source.name} className="grid gap-3 border-b border-border px-5 py-5 last:border-b-0 sm:grid-cols-[1.5fr_1fr_1fr_1fr] sm:items-center sm:gap-4"><div><p className="font-medium">{source.name}</p><p className="mt-1 text-xs text-muted-foreground sm:hidden">{source.type}</p></div><span className="hidden text-sm text-muted-foreground sm:block">{source.type}</span><span className="flex items-center gap-2 text-sm"><StatusIcon status={source.status} />{displayStatus(source.status)}{source.response_time_ms ? <span className="text-xs text-muted-foreground">· {source.response_time_ms}ms</span> : null}</span><span className="text-sm text-muted-foreground">{relativeAge(source.last_successful_fetch)}</span></div>)}</div><div className="mt-8 flex gap-3 border-t border-border pt-6 text-sm text-muted-foreground"><CircleAlert size={16} className="mt-0.5 shrink-0" /><p>Airline and travel platform access can change. FareLens never bypasses access controls and never replaces unavailable sources with estimates.</p></div></section></main>;
}

function StatusIcon({ status }: { status: SourceSummary["status"] }) { if (status === "live") return <CheckCircle2 size={16} className="text-primary" />; if (status === "searching" || status === "timeout") return <Clock3 size={16} className="text-accent-foreground" />; return <CircleAlert size={16} className="text-muted-foreground" />; }