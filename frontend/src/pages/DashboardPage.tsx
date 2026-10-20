import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Appointment, type LeadCard, type Offer, type StageCount } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { PriorityBadge, ScoreRing } from "../components/Badges";
import { addDays, dateTime, money, relativeDays, stageLabel, startOfWeek, typeLabel } from "../lib/format";

export function DashboardPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<StageCount[]>([]);
  const [leads, setLeads] = useState<LeadCard[]>([]);
  const [listings, setListings] = useState<number | null>(null);
  const [appts, setAppts] = useState<Appointment[]>([]);
  const [offers, setOffers] = useState<Offer[]>([]);

  useEffect(() => {
    api.GET("/api/leads/summary").then(({ data }) => data && setSummary(data));
    api.GET("/api/leads").then(({ data }) => data && setLeads(data));
    api.GET("/api/properties", { params: { query: { page_size: 1 } } }).then(({ data }) => data && setListings(data.total));
    const monday = startOfWeek(new Date());
    api.GET("/api/appointments", { params: { query: { start: new Date().toISOString(), end: addDays(monday, 14).toISOString() } } })
      .then(({ data }) => data && setAppts(data.filter((a) => a.status === "scheduled")));
    api.GET("/api/offers").then(({ data }) => data && setOffers(data));
  }, []);

  const open = leads.filter((l) => l.stage !== "won" && l.stage !== "lost");
  const won = summary.find((s) => s.stage === "won")?.count ?? 0;
  const lost = summary.find((s) => s.stage === "lost")?.count ?? 0;
  const conversion = won + lost ? Math.round((won / (won + lost)) * 100) : null;
  const focus = [...open].sort((a, b) => (b.score ?? 0) - (a.score ?? 0)).slice(0, 6);

  return (
    <section>
      <h1>Welcome, {user?.full_name.split(" ")[0]}</h1>
      <p className="muted">Here's where your pipeline stands today.</p>

      <div className="kpis">
        <div className="kpi"><span>Active leads</span><strong>{open.length}</strong></div>
        <div className="kpi"><span>High priority</span><strong className="accent">{open.filter((l) => l.priority === "high").length}</strong></div>
        <div className="kpi"><span>Deals won</span><strong>{won}</strong></div>
        <div className="kpi"><span>Win rate (closed)</span><strong>{conversion == null ? "—" : `${conversion}%`}</strong></div>
        <div className="kpi"><span>Upcoming appointments</span><strong>{appts.length}</strong></div>
        <div className="kpi"><span>Open offers</span><strong>{offers.filter((o) => o.status === "submitted" || o.status === "countered").length}</strong></div>
        <div className="kpi"><span>Listings for sale</span><strong>{listings ?? "—"}</strong></div>
      </div>

      <h2>Lead pipeline</h2>
      <ol className="pipeline" aria-label="Leads per stage">
        {summary.map((s) => (
          <li key={s.stage}>
            <Link to={`/pipeline#${s.stage}`}>
              <span>{stageLabel(s.stage)}</span>
              <strong>{s.count}</strong>
            </Link>
          </li>
        ))}
      </ol>

      {appts.length > 0 && <>
        <h2>Coming up</h2>
        <div className="list">
          {appts.slice(0, 4).map((a) => (
            <Link key={a.id} to={a.lead_id ? `/leads/${a.lead_id}` : "/calendar"} className="list-row">
              <span className={`badge type-${a.appointment_type}`}>{typeLabel[a.appointment_type]}</span>
              <div className="grow"><strong>{a.client_name}</strong><span className="muted small">{a.property_address ?? "No property"}</span></div>
              <span className="muted small nowrap">{dateTime(a.starts_at)}</span>
            </Link>
          ))}
        </div>
      </>}

      <h2>Focus on these leads first</h2>
      <p className="muted small">Ranked by the rule-based lead score. Open a lead to ask the AI for the next step.</p>
      <div className="list">
        {focus.map((l) => (
          <Link key={l.id} to={`/leads/${l.id}`} className="list-row">
            <ScoreRing score={l.score} />
            <div className="grow">
              <strong>{l.client_name}</strong>
              <span className="muted small">
                {stageLabel(l.stage)} · {l.preferred_city ?? "Any city"} · up to {money(l.budget_max)}
              </span>
            </div>
            <PriorityBadge priority={l.priority} />
            <span className="muted small nowrap">{relativeDays(l.last_contact_at)}</span>
          </Link>
        ))}
        {focus.length === 0 && <p className="empty">No active leads yet. Add a client to get started.</p>}
      </div>
    </section>
  );
}
