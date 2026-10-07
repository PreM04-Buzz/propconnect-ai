import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, errorMessage, type ClientDetail, type InteractionType, type PropertyMatch } from "../api/client";
import { PriorityBadge, ScoreRing, StageBadge } from "../components/Badges";
import { ClientForm } from "../components/ClientForm";
import { financingLabel, money, shortDate } from "../lib/format";

const TYPES: InteractionType[] = ["call", "email", "text", "meeting", "note"];

export function ClientDetailPage() {
  const id = Number(useParams().id);
  const navigate = useNavigate();
  const [c, setC] = useState<ClientDetail | null>(null);
  const [matches, setMatches] = useState<PropertyMatch[]>([]);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState({ type: "call" as InteractionType, summary: "" });

  const load = useCallback(async () => {
    const { data, error } = await api.GET("/api/clients/{client_id}", { params: { path: { client_id: id } } });
    if (!data) return setError(errorMessage(error, "Client not found."));
    setC(data);
    const m = await api.GET("/api/clients/{client_id}/matches", { params: { path: { client_id: id }, query: { limit: 6 } } });
    if (m.data) setMatches(m.data);
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) return <p className="error">{error}</p>;
  if (!c) return <p className="page-status">Loading…</p>;
  const lead = c.leads[0];
  const interestIds = new Set(c.interests.map((i) => i.property_id));

  async function addNote(e: FormEvent) {
    e.preventDefault();
    if (!note.summary.trim()) return;
    await api.POST("/api/clients/{client_id}/interactions", {
      params: { path: { client_id: id } }, body: { interaction_type: note.type, summary: note.summary.trim() },
    });
    setNote({ ...note, summary: "" });
    void load();
  }

  async function addInterest(propertyId: number) {
    await api.POST("/api/clients/{client_id}/interests", {
      params: { path: { client_id: id } }, body: { property_id: propertyId, interest_level: "high" },
    });
    void load();
  }

  async function removeInterest(interestId: number) {
    await api.DELETE("/api/clients/{client_id}/interests/{interest_id}", {
      params: { path: { client_id: id, interest_id: interestId } },
    });
    void load();
  }

  async function remove() {
    if (!c || !window.confirm(`Delete ${c.first_name} ${c.last_name} and their lead history?`)) return;
    await api.DELETE("/api/clients/{client_id}", { params: { path: { client_id: id } } });
    navigate("/clients");
  }

  return (
    <section>
      <p className="crumbs"><Link to="/clients">Clients</Link> / {c.first_name} {c.last_name}</p>
      <div className="page-head">
        <div>
          <h1>{c.first_name} {c.last_name}</h1>
          <p className="muted cap">{c.client_type} · {c.email ?? "no email"} · {c.phone ?? "no phone"}</p>
        </div>
        <div className="actions">
          {lead && <Link className="button" to={`/leads/${lead.id}`}>Open lead and AI next step</Link>}
          <button className="secondary" onClick={() => setEditing(!editing)}>{editing ? "Close editor" : "Edit profile"}</button>
        </div>
      </div>

      {editing ? (
        <ClientForm
          client={c}
          submitLabel="Save changes"
          onCancel={() => setEditing(false)}
          onSubmit={async (body) => {
            const { lead_source: _ls, create_lead: _cl, agent_id: _a, ...update } = body;
            const { data, error } = await api.PATCH("/api/clients/{client_id}", { params: { path: { client_id: id } }, body: update });
            if (!data) return errorMessage(error);
            setEditing(false);
            void load();
            return null;
          }}
        />
      ) : (
        <div className="grid-2">
          <div className="card">
            <h2>Profile</h2>
            <dl className="facts">
              <dt>Budget</dt><dd>{money(c.budget_min)} – {money(c.budget_max)} {c.budget_confirmed ? "(confirmed)" : "(not confirmed)"}</dd>
              <dt>Location</dt><dd>{[c.preferred_city, c.preferred_zip].filter(Boolean).join(", ") || "Any"}</dd>
              <dt>Home</dt><dd>{c.min_bedrooms ?? "Any"}+ beds · {c.min_bathrooms ?? "Any"}+ baths{c.min_house_size_sqft ? ` · ${c.min_house_size_sqft}+ sq ft` : ""}</dd>
              <dt>Financing</dt><dd>{financingLabel[c.financing_status]}</dd>
              <dt>Timeline</dt><dd>{c.purchase_timeline_months != null ? `Within ${c.purchase_timeline_months} months` : "Not set"}</dd>
              <dt>Notes</dt><dd>{c.notes ?? "—"}</dd>
            </dl>
          </div>
          <div className="card">
            <h2>Lead</h2>
            {lead ? (
              <Link to={`/leads/${lead.id}`} className="lead-box">
                <ScoreRing score={lead.score} />
                <div>
                  <StageBadge stage={lead.stage} /> <PriorityBadge priority={lead.priority} />
                  <p className="muted small">Source: {lead.source ?? "not specified"} · updated {shortDate(lead.updated_at)}</p>
                </div>
              </Link>
            ) : <p className="muted">No lead for this client.</p>}
            <button className="danger-link" onClick={remove}>Delete client</button>
          </div>
        </div>
      )}

      <div className="grid-2">
        <div className="card">
          <h2>Interaction timeline</h2>
          <form className="inline-form" onSubmit={addNote}>
            <select value={note.type} onChange={(e) => setNote({ ...note, type: e.target.value as InteractionType })}>
              {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <input className="grow" placeholder="What happened? e.g. Called to confirm budget" value={note.summary}
                   onChange={(e) => setNote({ ...note, summary: e.target.value })} />
            <button type="submit">Log</button>
          </form>
          <ul className="timeline">
            {c.interactions.map((i) => (
              <li key={i.id}>
                <span className={`dot type-${i.interaction_type}`} />
                <div>
                  <strong className="cap">{i.interaction_type}</strong> <span className="muted small">{shortDate(i.occurred_at)}</span>
                  <p className="pre">{i.summary}</p>
                </div>
              </li>
            ))}
            {c.interactions.length === 0 && <li className="empty">No interactions logged yet.</li>}
          </ul>
        </div>

        <div className="card">
          <h2>Interested in</h2>
          <ul className="prop-list">
            {c.interests.map((i) => (
              <li key={i.id}>
                <Link to={`/properties/${i.property_id}`}>
                  <strong>{i.property.street_address}</strong>, {i.property.city}
                </Link>
                <span className="muted small"> {money(i.property.price)} · {i.property.bedrooms} bd · {i.interest_level} interest</span>
                <button className="link-button" onClick={() => removeInterest(i.id)}>Remove</button>
              </li>
            ))}
            {c.interests.length === 0 && <li className="empty">No properties shortlisted yet.</li>}
          </ul>
          <h3>Best matches</h3>
          <p className="muted small">Rule-based match score: budget, location, bedrooms, bathrooms, size, availability.</p>
          <ul className="prop-list">
            {matches.map((m) => (
              <li key={m.property.id}>
                <span className="match-score">{m.score}</span>
                <Link to={`/properties/${m.property.id}`}><strong>{m.property.street_address}</strong>, {m.property.city}</Link>
                <span className="muted small"> {money(m.property.price)} · {m.property.bedrooms} bd · {m.reasons.join(", ")}</span>
                {interestIds.has(m.property.id) ? <span className="muted small"> Shortlisted</span>
                  : <button className="link-button" onClick={() => addInterest(m.property.id)}>Shortlist</button>}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
