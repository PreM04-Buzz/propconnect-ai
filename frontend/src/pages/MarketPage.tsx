import { useEffect, useState } from "react";
import { api, errorMessage, type MarketRegion, type MarketSeries, type MyArea } from "../api/client";
import { MarketChart, SERIES_COLORS } from "../components/MarketChart";
import { useAuth } from "../auth/AuthContext";

const monthYear = (iso?: string | null) =>
  iso ? new Date(`${iso}T12:00:00`).toLocaleDateString("en-US", { month: "long", year: "numeric" }) : "—";
const signed = (n?: number | null) => (n === null || n === undefined ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(1)}%`);
const trendWord = { rising: "Rising", falling: "Falling", steady: "Steady" } as Record<string, string>;

/** Homes for sale over time, by metro area (Zillow), and what it means for your clients' areas. */
export function MarketPage() {
  const { user } = useAuth();
  const [areas, setAreas] = useState<MyArea[] | null>(null);
  const [options, setOptions] = useState<MarketRegion[]>([]);
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<number[]>([]);
  const [series, setSeries] = useState<MarketSeries[]>([]);
  const [mode, setMode] = useState<"count" | "index">("count");
  const [error, setError] = useState<string | null>(null);

  // Start with the clients' areas and the Illinois list; chart Chicago by default.
  useEffect(() => {
    api.GET("/api/market/my-areas").then(({ data }) => setAreas(data ?? []));
    api.GET("/api/market/regions").then(({ data, error: e }) => {
      if (e) return setError(errorMessage(e));
      setOptions(data ?? []);
      const chicago = data?.find((r) => r.region_name === "Chicago, IL") ?? data?.[0];
      if (chicago) setPicked([chicago.region_id]);
    });
  }, []);

  // Search as you type (short pause so we don't ask on every key).
  useEffect(() => {
    const t = setTimeout(() => {
      api.GET("/api/market/regions", { params: { query: { q: query } } }).then(({ data }) => data && setOptions(data));
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    if (!picked.length) return setSeries([]);
    api.GET("/api/market/trends", { params: { query: { region_id: picked } } }).then(({ data, error: e }) => {
      if (e) setError(errorMessage(e));
      else setSeries(data ?? []);
    });
  }, [picked]);

  // Comparing a big metro with a small one only makes sense side by side as "% of 2019".
  useEffect(() => {
    if (picked.length < 2) setMode("count");
  }, [picked.length]);

  const add = (id: number) => {
    if (picked.includes(id)) return;
    setPicked((p) => (p.length >= 3 ? [...p.slice(0, 2), id] : [...p, id]));
    if (picked.length >= 1) setMode("index");
  };
  const remove = (id: number) => setPicked((p) => p.filter((x) => x !== id));
  // One card per metro: suburbs of the same metro share the same market numbers.
  const groups = new Map<number, { area: MyArea; cities: MyArea[]; clients: number }>();
  for (const a of areas ?? []) {
    if (!a.region_id) continue;
    const g = groups.get(a.region_id) ?? { area: a, cities: [], clients: 0 };
    g.cities.push(a);
    g.clients += a.clients;
    groups.set(a.region_id, g);
  }
  const matched = [...groups.values()].sort((x, y) => y.clients - x.clients);
  const unmatched = areas?.filter((a) => !a.region_id) ?? [];
  const arrow = (n?: number | null) => (n === null || n === undefined ? "" : n > 0 ? "↑ " : n < 0 ? "↓ " : "");

  return (
    <section className="wide-page market">
      <div className="page-head">
        <div>
          <h1>Market trends</h1>
          <p className="muted">How many homes are for sale each month, by metro area. More homes for sale means more choice for buyers;
            fewer means sellers have the upper hand. Source: Zillow, March 2018 to August 2026.</p>
        </div>
      </div>
      {error && <p className="error" role="alert">{error}</p>}

      <h2 className="market-h2">Where {user?.role === "admin" ? "your office’s" : "your"} clients want to live</h2>
      {areas === null ? <p className="muted">Loading…</p> : areas.length === 0 ? (
        <p className="empty">No clients with a preferred city yet. Add one on a client’s page and their area appears here.</p>
      ) : (
        <div className="area-grid">
          {matched.map(({ area: a, cities, clients }) => (
            <button type="button" key={a.region_id} className="area-card" onClick={() => a.region_id && add(a.region_id)}
                    aria-label={`Show ${a.region_name} on the chart`}>
              <span className="area-city">{a.region_name?.replace(/, [A-Z]{2}$/, "")} metro</span>
              <span className="muted small">
                {clients} client{clients === 1 ? "" : "s"}: {cities.map((c) => (c.clients > 1 ? `${c.city} (${c.clients})` : c.city)).join(", ")}
              </span>
              <span className="area-num">{a.latest?.toLocaleString() ?? "—"} <small>homes for sale</small></span>
              <span className="area-tags">
                <span className="chip">{arrow(a.change_1y_pct)}{signed(a.change_1y_pct)} on a year ago</span>
                {a.trend_3m && <span className="chip">{trendWord[a.trend_3m]} lately</span>}
              </span>
            </button>
          ))}
        </div>
      )}
      {unmatched.length > 0 && (
        <p className="muted small">No market data yet for {unmatched.map((a) => a.city).join(", ")}. Zillow reports by metro area,
          and these aren’t matched to one.</p>
      )}

      <div className="card market-card">
        <div className="market-controls">
          <div className="market-picked" aria-label="Areas on the chart">
            {series.map((s, i) => (
              <span key={s.region_id} className="picked-chip">
                <i style={{ background: SERIES_COLORS[i] }} />{s.region_name}
                <button type="button" aria-label={`Remove ${s.region_name}`} onClick={() => remove(s.region_id)}>×</button>
              </span>
            ))}
          </div>
          <div className="seg" role="group" aria-label="Show as">
            <button type="button" aria-pressed={mode === "count"} onClick={() => setMode("count")}>Homes for sale</button>
            <button type="button" aria-pressed={mode === "index"} onClick={() => setMode("index")}>Compared with 2019</button>
          </div>
        </div>
        {series.length ? <MarketChart series={series} mode={mode} /> : <p className="empty">Pick an area to see its trend.</p>}
        <div className="market-search">
          <label>Add an area to compare (up to 3)
            <input type="search" placeholder="Search a city or metro, e.g. Milwaukee" value={query}
                   onChange={(e) => setQuery(e.target.value)} />
          </label>
          <div className="region-list">
            {options.slice(0, 12).map((r) => (
              <button type="button" key={r.region_id} className="region-opt" disabled={picked.includes(r.region_id)}
                      onClick={() => add(r.region_id)}>
                {r.region_name}<span className="muted small"> {r.latest_inventory?.toLocaleString() ?? "—"} · {signed(r.change_1y_pct)}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="stat-grid">
        {series.map((s, i) => (
          <div key={s.region_id} className="card stat-card" style={{ borderTopColor: SERIES_COLORS[i] }}>
            <h3>{s.region_name}</h3>
            <p className="stat-summary">{s.stats.summary}</p>
            <dl>
              <div><dt>Homes for sale, {monthYear(s.stats.latest_month)}</dt><dd>{s.stats.latest?.toLocaleString() ?? "—"}</dd></div>
              <div><dt>Change on a year earlier</dt><dd>{signed(s.stats.change_1y_pct)}</dd></div>
              <div><dt>Compared with 2019</dt><dd>{signed(s.stats.change_vs_2019_pct)}</dd></div>
              <div><dt>Last 3 months</dt><dd>{s.stats.trend_3m ? trendWord[s.stats.trend_3m] : "—"}</dd></div>
              <div><dt>Most for sale</dt><dd>{s.stats.peak?.toLocaleString()} <small>({monthYear(s.stats.peak_month)})</small></dd></div>
              <div><dt>Fewest for sale</dt><dd>{s.stats.low?.toLocaleString()} <small>({monthYear(s.stats.low_month)})</small></dd></div>
            </dl>
          </div>
        ))}
      </div>
    </section>
  );
}
