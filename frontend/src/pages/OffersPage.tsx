import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage, type Offer, type OfferStatus } from "../api/client";
import { OfferActions } from "../components/OfferActions";
import { money, offerStatusLabel, shortDate } from "../lib/format";

const FILTERS: (OfferStatus | "")[] = ["", "submitted", "countered", "accepted", "rejected", "withdrawn", "draft"];

export function OffersPage() {
  const [filter, setFilter] = useState<OfferStatus | "">("");
  const [offers, setOffers] = useState<Offer[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const { data, error } = await api.GET("/api/offers", { params: { query: { status: filter || undefined } } });
    if (data) setOffers(data);
    else setError(errorMessage(error));
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);

  const open = offers?.filter((o) => o.status === "submitted" || o.status === "countered").length ?? 0;
  return (
    <section>
      <div className="page-head">
        <div>
          <h1>Offers</h1>
          <p className="muted">{open} open {open === 1 ? "offer" : "offers"}. Accepting one closes the deal: the lead moves to Won and the home is marked sold.</p>
        </div>
        <select value={filter} onChange={(e) => setFilter(e.target.value as OfferStatus | "")} aria-label="Filter by status">
          {FILTERS.map((f) => <option key={f} value={f}>{f ? offerStatusLabel[f] : "All offers"}</option>)}
        </select>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th>Client</th><th>Property</th><th>List price</th><th>Offer</th><th>Counter</th><th>Status</th><th>Submitted</th><th /></tr>
          </thead>
          <tbody>
            {offers?.map((o) => (
              <tr key={o.id}>
                <td>{o.lead_id ? <Link to={`/leads/${o.lead_id}`}>{o.client_name}</Link> : o.client_name}</td>
                <td><Link to={`/properties/${o.property_id}`}>{o.property_address}</Link></td>
                <td>{money(o.list_price)}</td>
                <td><strong>{money(o.amount)}</strong>
                  {o.list_price ? <div className="muted small">{Math.round((o.amount / o.list_price) * 100)}% of list</div> : null}</td>
                <td>{money(o.counter_amount)}</td>
                <td><span className={`badge offer-${o.status}`}>{offerStatusLabel[o.status]}</span></td>
                <td>{shortDate(o.submitted_at)}</td>
                <td><OfferActions offer={o} onChanged={load} onError={setError} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        {offers && offers.length === 0 && <p className="empty">No offers here yet. Make one from a lead's page.</p>}
      </div>
    </section>
  );
}
