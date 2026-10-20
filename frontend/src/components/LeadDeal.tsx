import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage, type Appointment, type ClientDetail, type Offer } from "../api/client";
import { dateTime, money, offerStatusLabel, typeLabel } from "../lib/format";
import { OfferActions } from "./OfferActions";

/** Viewings, meetings and offers for one lead, with ways to add more. */
export function LeadDeal({ leadId, clientId, onChanged }: { leadId: number; clientId: number; onChanged: () => void }) {
  const [appts, setAppts] = useState<Appointment[]>([]);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [client, setClient] = useState<ClientDetail | null>(null);
  const [form, setForm] = useState({ property: "", amount: "" });
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [a, o, c] = await Promise.all([
      api.GET("/api/appointments", { params: { query: { client_id: clientId } } }),
      api.GET("/api/offers", { params: { query: { lead_id: leadId } } }),
      api.GET("/api/clients/{client_id}", { params: { path: { client_id: clientId } } }),
    ]);
    if (a.data) setAppts(a.data);
    if (o.data) setOffers(o.data);
    if (c.data) setClient(c.data);
  }, [leadId, clientId]);

  useEffect(() => {
    void load();
  }, [load]);

  const refresh = () => {
    void load();
    onChanged();
  };

  async function makeOffer(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const { error } = await api.POST("/api/offers", { body: {
      client_id: clientId, property_id: Number(form.property), amount: Number(form.amount.replace(/[$,\s]/g, "")), submit: true,
    } });
    if (error) return setError(errorMessage(error));
    setForm({ property: "", amount: "" });
    refresh();
  }

  const upcoming = appts.filter((a) => a.status === "scheduled");
  const past = appts.filter((a) => a.status !== "scheduled").reverse();
  const shortlist = client?.interests.filter((i) => i.property.status === "for_sale") ?? [];

  return (
    <div className="grid-2">
      <div className="card">
        <div className="card-head">
          <h2>Viewings and meetings</h2>
          <Link className="button secondary" to={`/calendar?client=${clientId}`}>Schedule</Link>
        </div>
        <ul className="plain-list">
          {upcoming.map((a) => (
            <li key={a.id}><strong>{dateTime(a.starts_at)}</strong> · {typeLabel[a.appointment_type]}
              {a.property_address && <span className="muted"> at {a.property_address}</span>}</li>
          ))}
          {upcoming.length === 0 && <li className="muted">Nothing scheduled.</li>}
        </ul>
        {past.length > 0 && <>
          <h3>Earlier</h3>
          <ul className="plain-list">
            {past.slice(0, 5).map((a) => (
              <li key={a.id} className="small"><span className="cap">{a.status.replace("_", "-")}</span> · {dateTime(a.starts_at)}
                {a.property_address && <> · {a.property_address}</>}{a.outcome && <span className="muted"> · “{a.outcome}”</span>}</li>
            ))}
          </ul>
        </>}
      </div>
      <div className="card">
        <h2>Offers</h2>
        <ul className="plain-list">
          {offers.map((o) => (
            <li key={o.id}>
              <span className={`badge offer-${o.status}`}>{offerStatusLabel[o.status]}</span>{" "}
              <strong>{money(o.amount)}</strong> on {o.property_address}
              {o.counter_amount ? <span className="muted"> · seller countered {money(o.counter_amount)}</span> : null}
              <div><OfferActions offer={o} onChanged={refresh} onError={setError} /></div>
            </li>
          ))}
          {offers.length === 0 && <li className="muted">No offers yet.</li>}
        </ul>
        <form className="inline-form" onSubmit={makeOffer}>
          <select required className="grow" value={form.property} onChange={(e) => setForm({ ...form, property: e.target.value })}>
            <option value="">{shortlist.length ? "Make an offer on…" : "Shortlist a home first"}</option>
            {shortlist.map((i) => <option key={i.property_id} value={i.property_id}>{i.property.street_address} · list {money(i.property.price)}</option>)}
          </select>
          <input required inputMode="numeric" placeholder="Amount ($)" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          <button type="submit" disabled={!form.property}>Submit offer</button>
        </form>
        {error && <p className="error" role="alert">{error}</p>}
      </div>
    </div>
  );
}
