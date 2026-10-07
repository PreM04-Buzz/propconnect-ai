import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, errorMessage, type CityCount, type Property } from "../api/client";
import { money } from "../lib/format";

type Sort = "price_asc" | "price_desc" | "newest" | "size_desc";
const PAGE_SIZE = 24;

export function PropertiesPage() {
  const [params, setParams] = useSearchParams();
  const [cities, setCities] = useState<CityCount[]>([]);
  const [items, setItems] = useState<Property[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const get = (k: string) => params.get(k) ?? "";
  const page = Number(get("page") || 1);

  function update(k: string, v: string) {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    if (k !== "page") next.delete("page");
    setParams(next, { replace: true });
  }

  useEffect(() => {
    api.GET("/api/properties/cities", { params: { query: { limit: 80 } } }).then(({ data }) => data && setCities(data));
  }, []);

  useEffect(() => {
    const t = setTimeout(async () => {
      const n = (k: string) => (get(k) ? Number(get(k)) : undefined);
      const { data, error } = await api.GET("/api/properties", {
        params: { query: {
          q: get("q") || undefined, city: get("city") || undefined, min_price: n("min_price"), max_price: n("max_price"),
          min_beds: n("min_beds"), min_baths: n("min_baths"), sort: (get("sort") || "price_asc") as Sort, page, page_size: PAGE_SIZE,
        } },
      });
      if (data) {
        setItems(data.items);
        setTotal(data.total);
      } else setError(errorMessage(error));
    }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  return (
    <section>
      <div className="page-head">
        <div>
          <h1>Properties</h1>
          <p className="muted">{total.toLocaleString()} listings for sale match your filters.</p>
        </div>
        <Link className="button" to="/properties/new">Add listing</Link>
      </div>
      <div className="filters">
        <input className="grow" placeholder="Search address, city or ZIP" value={get("q")} onChange={(e) => update("q", e.target.value)} />
        <select value={get("city")} onChange={(e) => update("city", e.target.value)} aria-label="City">
          <option value="">All cities</option>
          {cities.map((c) => <option key={c.city} value={c.city}>{c.city} ({c.count})</option>)}
        </select>
        <input type="number" min={0} step={25000} placeholder="Min price" value={get("min_price")} onChange={(e) => update("min_price", e.target.value)} />
        <input type="number" min={0} step={25000} placeholder="Max price" value={get("max_price")} onChange={(e) => update("max_price", e.target.value)} />
        <select value={get("min_beds")} onChange={(e) => update("min_beds", e.target.value)} aria-label="Bedrooms">
          <option value="">Any beds</option>{[1, 2, 3, 4, 5].map((b) => <option key={b} value={b}>{b}+ beds</option>)}
        </select>
        <select value={get("min_baths")} onChange={(e) => update("min_baths", e.target.value)} aria-label="Bathrooms">
          <option value="">Any baths</option>{[1, 2, 3].map((b) => <option key={b} value={b}>{b}+ baths</option>)}
        </select>
        <select value={get("sort") || "price_asc"} onChange={(e) => update("sort", e.target.value)} aria-label="Sort">
          <option value="price_asc">Price: low to high</option><option value="price_desc">Price: high to low</option>
          <option value="size_desc">Largest first</option><option value="newest">Newest added</option>
        </select>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="prop-grid">
        {items?.map((p) => (
          <Link key={p.id} to={`/properties/${p.id}`} className="prop-card">
            <div className="prop-price">{money(p.price)}</div>
            <div className="prop-specs">{p.bedrooms} bd · {p.bathrooms} ba · {p.house_size_sqft?.toLocaleString() ?? "—"} sq ft</div>
            <div className="prop-addr">{p.street_address}</div>
            <div className="muted small">{p.city}, IL {p.zip_code}</div>
          </Link>
        ))}
      </div>
      {items && items.length === 0 && <p className="empty">No listings match. Try widening the price range.</p>}
      {pages > 1 && (
        <div className="pager">
          <button className="secondary" disabled={page <= 1} onClick={() => update("page", String(page - 1))}>Previous</button>
          <span>Page {page} of {pages}</span>
          <button className="secondary" disabled={page >= pages} onClick={() => update("page", String(page + 1))}>Next</button>
        </div>
      )}
    </section>
  );
}
