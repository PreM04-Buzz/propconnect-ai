import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorMessage, type ClientListItem, type Property } from "../api/client";
import { money, shortDate } from "../lib/format";

export function PropertyDetailPage() {
  const id = Number(useParams().id);
  const [p, setP] = useState<Property | null>(null);
  const [clients, setClients] = useState<ClientListItem[]>([]);
  const [pick, setPick] = useState({ client: "", level: "high" });
  const [price, setPrice] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.GET("/api/properties/{property_id}", { params: { path: { property_id: id } } }).then(({ data, error }) => {
      if (data) {
        setP(data);
        setPrice(String(data.price ?? ""));
      } else setError(errorMessage(error, "Listing not found."));
    });
    api.GET("/api/clients", { params: { query: { client_type: "buyer" } } }).then(({ data }) => data && setClients(data));
  }, [id]);

  if (error) return <p className="error">{error}</p>;
  if (!p) return <p className="page-status">Loading…</p>;

  async function shortlist() {
    if (!pick.client) return;
    const { error } = await api.POST("/api/clients/{client_id}/interests", {
      params: { path: { client_id: Number(pick.client) } }, body: { property_id: id, interest_level: pick.level },
    });
    const c = clients.find((x) => String(x.id) === pick.client);
    setMessage(error ? errorMessage(error) : `Added to ${c?.first_name} ${c?.last_name}'s shortlist.`);
  }

  async function savePrice() {
    const { data, error } = await api.PATCH("/api/properties/{property_id}", {
      params: { path: { property_id: id } }, body: { price: Number(price) },
    });
    if (data) setP(data);
    setMessage(error ? errorMessage(error) : "Price updated.");
  }

  return (
    <section>
      <p className="crumbs"><Link to="/properties">Properties</Link> / {p.street_address}</p>
      <div className="page-head">
        <div>
          <h1>{p.street_address}</h1>
          <p className="muted">{p.city}, {p.state} {p.zip_code}</p>
        </div>
        <div className="prop-price big">{money(p.price)}</div>
      </div>
      <div className="grid-2">
        <div className="card">
          <h2>Details</h2>
          <dl className="facts">
            <dt>Status</dt><dd className="cap">{p.status.replace("_", " ")}</dd>
            <dt>Bedrooms</dt><dd>{p.bedrooms}</dd>
            <dt>Bathrooms</dt><dd>{p.bathrooms}</dd>
            <dt>Size</dt><dd>{p.house_size_sqft?.toLocaleString() ?? "—"} sq ft</dd>
            <dt>Lot</dt><dd>{p.acre_lot != null ? `${p.acre_lot} acres` : "—"}</dd>
            <dt>Price per sq ft</dt><dd>{p.price && p.house_size_sqft ? money(p.price / p.house_size_sqft) : "—"}</dd>
            <dt>Last sold</dt><dd>{shortDate(p.prev_sold_date)}</dd>
          </dl>
          <p className="muted small">Listing data from the USA Real Estate dataset. Street addresses are generated for the demo because the dataset anonymizes them.</p>
        </div>
        <div className="card">
          <h2>Shortlist for a client</h2>
          <div className="inline-form">
            <select className="grow" value={pick.client} onChange={(e) => setPick({ ...pick, client: e.target.value })}>
              <option value="">Choose a buyer…</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.first_name} {c.last_name} · {c.preferred_city ?? "any city"} · up to {money(c.budget_max)}</option>)}
            </select>
            <select value={pick.level} onChange={(e) => setPick({ ...pick, level: e.target.value })}>
              <option value="high">High interest</option><option value="medium">Medium</option><option value="low">Low</option>
            </select>
            <button onClick={shortlist} disabled={!pick.client}>Add</button>
          </div>
          <h3>Update price</h3>
          <div className="inline-form">
            <input type="number" min={0} step={1000} value={price} onChange={(e) => setPrice(e.target.value)} />
            <button className="secondary" onClick={savePrice}>Save price</button>
          </div>
          {message && <p className="notice">{message}</p>}
        </div>
      </div>
    </section>
  );
}
